#include "runtime_profile.h"
#include <cassert>
int main() {
  assert(!runtime::allowPump(false,false));
  assert(!runtime::allowPump(false,true));
  assert(!runtime::allowPump(true,false));
#if SG_TELEMETRY_ONLY
  static_assert(runtime::telemetryOnly,"Telemetry-only mode");
  static_assert(!runtime::allowPump(true,true),"Even commissioned sites must not start a pump in telemetry-only mode");
#else
  static_assert(!runtime::telemetryOnly,"Normal runtime profile");
  assert(runtime::allowPump(true,true));
#endif
}
