#include <cassert>
#include <cstdint>
#include <iostream>
#include "float_telemetry.h"
int main() {
  FloatTelemetry f;
  f.observe(true,0);assert(!f.due(500));f.sent(true,0);
  f.observe(false,100);assert(!f.due(349));assert(!f.due(400));
  f.observe(true,500);assert(!f.due(1000)); // bounce returns to last reported
  f.observe(false,1100);assert(!f.due(1349));assert(f.due(1350));assert(!f.due(1350,false));assert(!f.due(5000,false));
  f.sent(false,1350);assert(!f.due(2400)); // no repeat while unchanged
  f.observe(true,1400);assert(!f.due(2349));assert(f.due(2350));
  f.sent(true,2350);assert(!f.due(3000));
  FloatTelemetry wrap;uint32_t t=UINT32_MAX-100;
  wrap.observe(true,t);wrap.sent(true,t);wrap.observe(false,t+50);
  assert(!wrap.due(t+999));assert(wrap.due(t+1000));
  // A regular/control publication acknowledges the actual raw state as well.
  wrap.sent(false,t+1000);assert(!wrap.due(t+2000));
  std::cout << "float telemetry: debounce, bounce, rate limit, unchanged, rollover PASS\n";
}
