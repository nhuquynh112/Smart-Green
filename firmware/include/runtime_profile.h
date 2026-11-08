#pragma once

namespace runtime {
#ifdef SG_DAY3_BUILD
constexpr bool telemetryOnly=true;
#else
constexpr bool telemetryOnly=false;
#endif
constexpr bool allowPump(bool hardwareVerified,bool calibrationVerified) {
  return !telemetryOnly && hardwareVerified && calibrationVerified;
}
}
