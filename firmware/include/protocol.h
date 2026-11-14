#pragma once
#include <ArduinoJson.h>
#include <cstring>
#include "controller.h"
namespace protocol {
inline const char* mode(garden::Mode v) {
  return v==garden::Mode::Auto?"AUTO":v==garden::Mode::Manual?"MANUAL":"OFF";
}
inline const char* source(garden::Source v) {
  return v==garden::Source::AI?"AI":v==garden::Source::Manual?"MANUAL":"RULE";
}
inline const char* reason(garden::Reason v) {
  switch(v) {
    case garden::Reason::Running:return "Running";case garden::Reason::Duration:return "Duration";
    case garden::Reason::Wet:return "Wet";case garden::Reason::Sensor:return "Sensor";
    case garden::Reason::Tank:return "Tank";case garden::Reason::Stop:return "Stop";
    case garden::Reason::Reboot:return "Reboot";default:return "Guard";
  }
}
inline bool equal(JsonVariantConst v,const char* s) {return v.is<const char*>() && std::strcmp(v.as<const char*>(),s)==0;}
inline const char* parse(JsonVariantConst j,const char* device,uint32_t maxMs,garden::Command& c) {
  c=garden::Command{};
  if (!j.is<JsonObjectConst>() || !j["schema_version"].is<unsigned>() || j["schema_version"].as<unsigned>()!=1) return "schema";
  if (!equal(j["device_id"],device)) return "device";
  if (!j["command_seq"].is<uint32_t>() || !j["command_seq"].as<uint32_t>()) return "sequence";
  c.seq=j["command_seq"].as<uint32_t>();
  if (!j["issued_at"].is<int64_t>() || !j["expires_at"].is<int64_t>()) return "time_type";
  c.issuedAt=j["issued_at"].as<int64_t>();c.expiresAt=j["expires_at"].as<int64_t>();
  // Bound before subtraction in core; expired STOP is still allowed through to stop safely.
  if (c.issuedAt<1700000000 || c.expiresAt<1700000000 || c.issuedAt>4102444800LL || c.expiresAt>4102444800LL) return "time_range";
  if (equal(j["kind"],"STOP")) {c.kind=garden::Command::Kind::Stop;return nullptr;}
  if (equal(j["kind"],"SET_MODE")) {
    c.kind=garden::Command::Kind::SetMode;
    if (equal(j["mode"],"OFF")) c.mode=garden::Mode::Off;
    else if (equal(j["mode"],"MANUAL")) c.mode=garden::Mode::Manual;
    else if (equal(j["mode"],"AUTO")) c.mode=garden::Mode::Auto;
    else return "mode";
    return nullptr;
  }
  if (!equal(j["kind"],"WATER")) return "kind";
  c.kind=garden::Command::Kind::Water;
  if (equal(j["source"],"MANUAL")) c.source=garden::Source::Manual;
  else if (equal(j["source"],"AI")) c.source=garden::Source::AI;
  else return "source";
  if (!j["duration_ms"].is<uint32_t>()) return "duration_type";
  c.durationMs=j["duration_ms"].as<uint32_t>();
  if (!c.durationMs || c.durationMs>maxMs) return "duration_limit";
  return nullptr;
}
}
