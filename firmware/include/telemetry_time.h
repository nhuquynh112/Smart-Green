#pragma once
#include <ArduinoJson.h>
#include <ctime>
#include <cstdint>

inline void serializeTime(JsonDocument& document,int64_t value) {
  if(value<1700000000) {document["timestamp"]=nullptr;return;}
  time_t t=static_cast<time_t>(value);tm parts;
  if(!gmtime_r(&t,&parts)) {document["timestamp"]=nullptr;return;}
  char buffer[25];
  if(!strftime(buffer,sizeof(buffer),"%Y-%m-%dT%H:%M:%SZ",&parts)) {document["timestamp"]=nullptr;return;}
  document["timestamp"]=buffer;
}
