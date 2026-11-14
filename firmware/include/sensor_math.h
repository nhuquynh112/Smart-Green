#pragma once
#include <cmath>
#include <algorithm>
namespace sensors {
inline bool calibrated(int dry,int wet) {
  return dry>50 && dry<4045 && wet>50 && wet<4045 && std::abs(dry-wet)>=200;
}
inline bool convert(int raw,int dry,int wet,float& pct) {
  if (!calibrated(dry,wet) || raw<=50 || raw>=4045) return false;
  pct=std::max(0.0f,std::min(100.0f,100.0f*(raw-dry)/(wet-dry)));
  return true;
}
}
