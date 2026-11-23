#pragma once
#include "controller.h"

namespace garden {
inline bool isSafetyCommand(const Command& c) {
  return c.kind==Command::Kind::Stop ||
    (c.kind==Command::Kind::SetMode && c.mode==Mode::Off);
}
// Single network-task owner; each lane has a dedicated one-item core/ACK queue.
// Keep failed ACKs for retry. Only safe-off commands can bypass a normal ACK.
struct CommandDelivery {
  bool normalPending=false, normalWaiting=false;
  bool safetyPending=false, safetyWaiting=false;
  bool shouldPoll() const { return !safetyPending && !safetyWaiting; }
  bool canDispatch(bool safety) const {
    return shouldPoll() && (safety || (!normalPending && !normalWaiting));
  }
  void dispatched(bool safety) { (safety?safetyWaiting:normalWaiting)=true; }
  void receivedAck(bool safety) {
    (safety?safetyWaiting:normalWaiting)=false;
    (safety?safetyPending:normalPending)=true;
  }
  void ackResult(bool safety,int code) {
    if(code>=200 && code<300) (safety?safetyPending:normalPending)=false;
  }
};
}
