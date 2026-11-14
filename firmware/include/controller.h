#pragma once
#include <cmath>
#include <cstdint>

namespace garden {
enum class Mode : uint8_t { Off, Manual, Auto };
enum class Reason : uint8_t { Running, Duration, Wet, Sensor, Tank, Stop, Reboot, Guard };
enum class Source : uint8_t { Rule, Manual, AI };
struct Config {
  bool commissioned = false;
  bool manualUnlimitedStarts = false;
  bool separateManualQuota = false;
  float low = 30, high = 45, aiCeiling = 40;
  uint32_t pulseMs = 2000, maxPulseMs = 3000, cooldownMs = 600000;
  uint32_t manualCooldownMs = UINT32_MAX; // Sentinel uses cooldownMs; zero disables manual cooldown.
  uint32_t maxDayMs = 12000, maxDayStarts = 4, staleMs = 4000;
  bool valid() const {
    return std::isfinite(low) && std::isfinite(high) && std::isfinite(aiCeiling)
      && low >= 0 && low < high && high <= 100 && aiCeiling >= low && aiCeiling < high
      && pulseMs > 0 && pulseMs <= maxPulseMs && maxPulseMs <= 60000
      && cooldownMs >= 1000 && cooldownMs < 0x80000000UL
      && (manualCooldownMs == UINT32_MAX || manualCooldownMs == 0 || (manualCooldownMs >= 1000 && manualCooldownMs < 0x80000000UL))
      && maxDayMs >= maxPulseMs && maxDayStarts > 0 && staleMs >= 1000;
  }
};
struct Sensor {
  float soil = 0;
  bool valid = false, tankOK = false;
  uint32_t sampledMs = 0;
};
struct Event {
  uint32_t id = 0, commandSeq = 0, plannedMs = 0, actualMs = 0;
  int64_t startedAt = 0;
  Source source = Source::Rule;
  Reason reason = Reason::Running;
};
struct LegacyState {
  uint32_t magic = 0x53473101, lastCommand = 0, nextEvent = 1;
  int64_t windowStart = 0, lastWaterAt = 0;
  uint32_t reservedMs = 0, starts = 0;
  Mode mode = Mode::Off;
  uint8_t eventCount = 0;
  Event events[32]{};
};
// v2 preserves the complete v1 prefix, including unacknowledged events.
struct State : LegacyState {
  int64_t manualWindowStart = 0;
  uint32_t manualReservedMs = 0, manualStarts = 0;
  State() { magic=0x53473102; }
};
inline State migrateState(const LegacyState& old) {
  State next;
  static_cast<LegacyState&>(next)=old;
  if(old.magic!=0x53473101 || old.eventCount>32 || static_cast<unsigned>(old.mode)>2 || !old.nextEvent){next.magic=0;return next;}
  next.magic=0x53473102;
  // Source attribution of acknowledged history is unavailable. Reserve old
  // usage in BOTH budgets until that window expires; never silently refund it.
  next.manualWindowStart=old.windowStart;
  next.manualReservedMs=old.reservedMs;next.manualStarts=old.starts;
  next.mode=Mode::Off;
  return next;
}
struct Storage {
  virtual bool save(const State&) = 0;
  virtual ~Storage() = default;
};
struct Command {
  enum class Kind { Stop, SetMode, Water } kind = Kind::Stop;
  uint32_t seq = 0, durationMs = 0;
  int64_t issuedAt = 0, expiresAt = 0;
  Mode mode = Mode::Off;
  Source source = Source::Manual;
};
struct PumpOutput {
  virtual bool start(uint32_t durationMs) = 0;
  virtual void off() = 0;
  virtual uint32_t startedAt(uint32_t fallback) { return fallback; }
  virtual uint32_t actualDuration(uint32_t fallback) { return fallback; }
  virtual ~PumpOutput() = default;
};
// No network/Arduino dependencies. All output decisions are made here.
class Controller {
 public:
  Controller(Config cfg, State saved, Storage& storage, uint32_t now, PumpOutput* output = nullptr)
      : cfg_(cfg), state_(saved), storage_(storage), output_(output), stoppedMs_(now) {
    if (state_.magic != 0x53473102 || state_.eventCount > 32
        || static_cast<unsigned>(state_.mode) > 2 || state_.nextEvent == 0) {
      fault_ = true;
      return;
    }
    if (state_.eventCount && state_.events[state_.eventCount-1].reason == Reason::Running) {
      // Physical duration across a reset is unknown; keep the reservation.
      state_.events[state_.eventCount-1].reason = Reason::Reboot;
      persist();
    }
  }
  const State& state() const { return state_; }
  bool pumping() const { return pumping_; }
  bool fault() const { return fault_; }
  uint32_t cooldownRemaining(uint32_t now) const {
    const uint32_t elapsed=uint32_t(now-stoppedMs_);
    const uint32_t interval=state_.mode==Mode::Manual && cfg_.manualCooldownMs!=UINT32_MAX ? cfg_.manualCooldownMs : cfg_.cooldownMs;
    return elapsed>=interval ? 0 : interval-elapsed;
  }
  Mode mode() const { return state_.mode; }
  void tick(uint32_t ms, int64_t utc, const Sensor& s, bool deadlineFired = false) {
    if (pumping_) {
      if (deadlineFired || uint32_t(ms-startedMs_) >= durationMs_) stop(ms, Reason::Duration);
      else if (!fresh(ms,s)) stop(ms,Reason::Sensor);
      else if (!s.tankOK) stop(ms,Reason::Tank);
      else if (s.soil >= cfg_.high) stop(ms,Reason::Wet);
    }
    if (!fresh(ms,s)) { dryCount_=0; return; }
    if (s.sampledMs != lastSample_) {
      lastSample_ = s.sampledMs;
      if (s.soil <= cfg_.low) { if (dryCount_ < 3) ++dryCount_; }
      else dryCount_ = 0;
    }
    if (state_.mode == Mode::Auto && dryCount_ >= 3 && !pumping_)
      start(ms, utc, s, cfg_.pulseMs, Source::Rule, 0);
  }
  const char* command(const Command& c, uint32_t ms, int64_t utc, const Sensor& s) {
    // Even an expired STOP may shut the pump down, never starts it.
    const bool safeOff=c.kind==Command::Kind::Stop || (c.kind==Command::Kind::SetMode && c.mode==Mode::Off);
    if (safeOff) {
      stop(ms, Reason::Stop);
      // A stale/duplicate STOP must also prevent AUTO from restarting on the next tick.
      if(state_.mode!=Mode::Off){state_.mode=Mode::Off;dryCount_=0;if(!persist())return "storage_fault";}
    }
    if (c.seq == 0 || c.seq <= state_.lastCommand) return safeOff?"stopped":"duplicate";
    if (utc < 1700000000 || c.issuedAt > utc+5 || c.expiresAt <= utc
        || c.expiresAt <= c.issuedAt || c.expiresAt-c.issuedAt > 60) return safeOff?"stopped":"expired_or_clock";
    state_.lastCommand = c.seq;
    if (!persist()) return "storage_fault";
    if (c.kind == Command::Kind::Stop) {
      state_.mode = Mode::Off; return persist() ? "stopped" : "storage_fault";
    }
    if (c.kind == Command::Kind::SetMode) {
      stop(ms, Reason::Stop);
      if (static_cast<unsigned>(c.mode) > 2) return "invalid_mode";
      state_.mode = c.mode; dryCount_=0;
      return persist() ? "mode_set" : "storage_fault";
    }
    if ((c.source == Source::Manual && state_.mode != Mode::Manual)
        || (c.source == Source::AI && (state_.mode != Mode::Auto || s.soil > cfg_.aiCeiling))
        || c.source == Source::Rule) return "mode_or_ai_ceiling";
    return start(ms,utc,s,c.durationMs,c.source,c.seq);
  }
  bool acknowledgeEvent(uint32_t id) {
    if (!state_.eventCount || state_.events[0].id != id
        || state_.events[0].reason == Reason::Running) return false;
    for (unsigned i=1;i<state_.eventCount;++i) state_.events[i-1]=state_.events[i];
    --state_.eventCount;
    return persist();
  }
  void externalStop(uint32_t stoppedMs, Reason reason) { stop(stoppedMs, reason); if(reason==Reason::Guard) fault_=true; }
  void emergencyStop(uint32_t ms) { stop(ms,Reason::Stop); fault_=true; }
 private:
  bool persist() {
    if (!storage_.save(state_)) { if (output_) output_->off(); fault_=true; pumping_=false; return false; }
    return true;
  }
  bool fresh(uint32_t ms,const Sensor& s) const {
    return s.valid && std::isfinite(s.soil) && s.soil >= 0 && s.soil <= 100
      && uint32_t(ms-s.sampledMs) <= cfg_.staleMs;
  }
  const char* start(uint32_t ms,int64_t utc,const Sensor& s,uint32_t duration,Source source,uint32_t seq) {
    if (fault_ || !cfg_.valid() || !cfg_.commissioned) return "not_commissioned_or_fault";
    if (pumping_) return "busy";
    if (!fresh(ms,s) || !s.tankOK || s.soil >= cfg_.high) return "sensor_tank_or_wet";
    if (cooldownRemaining(ms)) return "cooldown";
    if (!duration || duration > cfg_.maxPulseMs) return "duration_limit";
    const bool manual=cfg_.separateManualQuota && source==Source::Manual;
    auto& window=manual?state_.manualWindowStart:state_.windowStart;
    auto& reserved=manual?state_.manualReservedMs:state_.reservedMs;
    auto& starts=manual?state_.manualStarts:state_.starts;
    if (utc < 1700000000 || utc < window || utc < state_.lastWaterAt) return "clock";
    if (!window || utc-window >= 86400) { window=utc;reserved=0;starts=0; }
    if ((!(source==Source::Manual && cfg_.manualUnlimitedStarts) && starts >= cfg_.maxDayStarts)
        || reserved > cfg_.maxDayMs || duration > cfg_.maxDayMs-reserved) return "quota";
    if (state_.eventCount == 32 || state_.nextEvent == UINT32_MAX) return "event_log_full";
    Event& e=state_.events[state_.eventCount++];
    e=Event{}; e.id=state_.nextEvent++; e.commandSeq=seq; e.plannedMs=duration;
    e.startedAt=utc; e.source=source;
    state_.lastWaterAt=utc; reserved+=duration; ++starts;
    // Commit reservation and event BEFORE enabling the physical output.
    if (!persist()) return "storage_fault";
    durationMs_=duration; startedMs_=ms; pumping_=true; dryCount_=0;
    if (output_ && !output_->start(duration)) {
      stop(ms, Reason::Guard); fault_=true; return "output_fault";
    }
    if (output_) startedMs_=output_->startedAt(ms);
    return "started";
  }
  void stop(uint32_t ms,Reason reason) {
    if (!pumping_) return;
    if (output_) output_->off(); // Physical OFF before potentially slow NVS writes.
    pumping_=false; stoppedMs_=ms; dryCount_=0;
    Event& e=state_.events[state_.eventCount-1];
    e.actualMs=output_?output_->actualDuration(uint32_t(ms-startedMs_)):uint32_t(ms-startedMs_); e.reason=reason;
    persist(); // reservation is intentionally not refunded
  }
  Config cfg_; State state_; Storage& storage_; PumpOutput* output_;
  bool pumping_=false,fault_=false;
  uint32_t stoppedMs_=0,startedMs_=0,durationMs_=0,lastSample_=0;
  uint8_t dryCount_=0;
};
} // namespace garden
