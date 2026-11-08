#include "runtime_profile.h"
#include <cassert>
int main() {
  assert(!runtime::allowPump(false,false));
  assert(!runtime::allowPump(false,true));
  assert(!runtime::allowPump(true,false));
#ifdef SG_DAY3_BUILD
  static_assert(runtime::telemetryOnly,"Day 3 must use telemetry-only mode");
  static_assert(!runtime::allowPump(true,true),"Even commissioned sites must not start a pump in day3");
#else
  static_assert(!runtime::telemetryOnly,"Normal runtime profile");
  assert(runtime::allowPump(true,true));
#endif
}
