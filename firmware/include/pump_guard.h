#pragma once
#include "controller.h"
namespace garden {
inline Reason guardReason(uint32_t now,uint32_t started,uint32_t limit,uint32_t heartbeat,bool tankOK) {
  if(uint32_t(now-heartbeat)>500) return Reason::Guard;
  if(!tankOK) return Reason::Tank;
  if(uint32_t(now-started)>=limit) return Reason::Duration;
  return Reason::Running;
}
}
