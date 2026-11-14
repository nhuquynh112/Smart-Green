#include "controller.h"
#include <cassert>
#include <iostream>
#include <string>
using namespace garden;
namespace {
constexpr int64_t utc = 1800000001;
struct Store : Storage { State saved; bool save(const State& value) override { saved=value; return true; } };
Config config() { Config c; c.commissioned=true; c.cooldownMs=1000; return c; }
Sensor sample(uint32_t ms, float soil=20) { Sensor s; s.valid=true; s.tankOK=true; s.soil=soil; s.sampledMs=ms; return s; }
Command water(uint32_t seq=1) { Command c; c.kind=Command::Kind::Water; c.seq=seq; c.durationMs=1000; c.issuedAt=utc; c.expiresAt=utc+60; return c; }
void cooldown_boundary() {
  Store s; State st; st.mode=Mode::Manual; Controller c(config(),st,s,0);
  assert(std::string(c.command(water(),999,utc,sample(999)))=="cooldown");
  assert(!c.pumping());
  assert(std::string(c.command(water(2),1000,utc,sample(1000)))=="started");
  c.tick(2000,utc+1,sample(2000));
  assert(!c.pumping());
  assert(std::string(c.command(water(3),2999,utc+2,sample(2999)))=="cooldown");
  assert(std::string(c.command(water(4),3000,utc+2,sample(3000)))=="started");
}
void time_quota_and_reboot() {
  Store s; State st; st.mode=Mode::Manual; st.windowStart=utc; st.reservedMs=11500;
  Controller c(config(),st,s,0);
  assert(std::string(c.command(water(),1000,utc,sample(1000)))=="quota");
  assert(!c.pumping() && c.state().eventCount==0);
  auto w=water(2); w.durationMs=500;
  assert(std::string(c.command(w,2000,utc,sample(2000)))=="started");
  c.tick(2500,utc+1,sample(2500));
  Controller reboot(config(),s.saved,s,0);
  assert(reboot.state().reservedMs==12000);
  assert(std::string(reboot.command(water(3),1000,utc+2,sample(1000)))=="quota");
  assert(!reboot.pumping());
}
void full_event_queue() {
  Store s; State st; st.mode=Mode::Manual; st.eventCount=32; st.nextEvent=33;
  for(unsigned i=0;i<32;++i) { st.events[i].id=i+1; st.events[i].reason=Reason::Duration; }
  Controller c(config(),st,s,0);
  assert(std::string(c.command(water(),1000,utc,sample(1000)))=="event_log_full");
  assert(!c.pumping()); assert(!c.acknowledgeEvent(2)); assert(c.acknowledgeEvent(1));
  assert(std::string(c.command(water(2),2000,utc,sample(2000)))=="started");
  assert(c.state().eventCount==32 && c.state().events[31].id==33);
}
void ai_mode_and_ceiling() {
  for (Mode mode : {Mode::Off, Mode::Manual, Mode::Auto}) {
    Store s; State st; st.mode=mode; Controller c(config(),st,s,0);
    auto w=water(); w.source=Source::AI;
    assert(std::string(c.command(w,1000,utc,sample(1000,41)))=="mode_or_ai_ceiling");
    w.seq=2;
    const auto result=std::string(c.command(w,2000,utc,sample(2000,40)));
    assert(result==(mode==Mode::Auto ? "started" : "mode_or_ai_ceiling"));
    assert(c.pumping()==(mode==Mode::Auto));
  }
}
void noisy_dry_samples() {
  Store s; State st; st.mode=Mode::Auto; Controller c(config(),st,s,0);
  c.tick(1000,utc,sample(1000,20)); c.tick(2000,utc+1,sample(2000,20));
  c.tick(3000,utc+2,sample(3000,31)); // Break the consecutive dry sequence.
  c.tick(4000,utc+3,sample(4000,20)); c.tick(5000,utc+4,sample(5000,20));
  assert(!c.pumping());
  c.tick(6000,utc+5,sample(6000,20)); assert(c.pumping());
  c.tick(6100,utc+5,sample(6100,44)); assert(c.pumping());
  c.tick(6200,utc+5,sample(6200,45)); assert(!c.pumping());
  assert(c.state().events[0].reason==Reason::Wet);
}
void clock_rollback() {
  Store s; State st; st.mode=Mode::Manual; st.lastWaterAt=utc+10;
  Controller c(config(),st,s,0);
  assert(std::string(c.command(water(),1000,utc,sample(1000)))=="clock");
  assert(!c.pumping() && c.state().eventCount==0);
}
}
int main() {
  cooldown_boundary(); time_quota_and_reboot(); full_event_queue();
  ai_mode_and_ceiling(); noisy_dry_samples(); clock_rollback();
  std::cout << "safety boundaries: 6 scenario groups passed (host simulation only)\n";
}
