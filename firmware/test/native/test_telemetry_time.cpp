#include "telemetry_time.h"
#include <cassert>
#include <string>
int main() {
  JsonDocument doc;
  serializeTime(doc,0);
  std::string payload;serializeJson(doc,payload);
  assert(payload=="{\"timestamp\":null}");
  serializeTime(doc,1700000000);
  payload.clear();serializeJson(doc,payload);
  assert(payload=="{\"timestamp\":\"2023-11-14T22:13:20Z\"}");
  serializeTime(doc,0);
  payload.clear();serializeJson(doc,payload);
  assert(payload=="{\"timestamp\":null}");
}
