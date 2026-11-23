#pragma once
#include <cstdint>

// Notification timing only. Never use this debounced value for pump safety.
class FloatTelemetry {
 public:
  void observe(bool value, uint32_t now) {
    if(!initialized) {initialized=true;candidate=value;since=now;}
    else if(candidate!=value) {candidate=value;since=now;}
  }
  bool due(uint32_t now, bool enabled=true) const {
    return enabled && initialized && published && candidate!=reported
        && uint32_t(now-since)>=250 && uint32_t(now-lastPublish)>=1000;
  }
  void sent(bool value,uint32_t now) {
    reported=value;published=true;lastPublish=now;
  }
 private:
  bool initialized=false,published=false,candidate=false,reported=false;
  uint32_t since=0,lastPublish=0;
};
