#pragma once

#ifndef SG_TELEMETRY_ONLY
#define SG_TELEMETRY_ONLY true
#endif

namespace runtime {
constexpr bool telemetryOnly=SG_TELEMETRY_ONLY;
constexpr bool allowPump(bool hardwareVerified,bool calibrationVerified) {
  return !telemetryOnly && hardwareVerified && calibrationVerified;
}
}
