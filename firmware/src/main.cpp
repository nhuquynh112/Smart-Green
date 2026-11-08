#include <Arduino.h>
#include <ArduinoJson.h>
#include <Preferences.h>
#include <DHT.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include "controller.h"
#include "hardware.h"
#include "network_worker.h"
#include "telemetry_time.h"

std::atomic<bool> net::clockReady{false};
std::atomic<bool> net::contacted{false};
std::atomic<uint32_t> net::lastContactMs{0};
std::atomic<int> net::telemetryStatus{0};
std::atomic<uint32_t> net::telemetrySent{0},net::telemetryFailures{0};
hardware::Pump pump;
struct NvsStorage : garden::Storage {
  Preferences prefs;bool ready=false;
  bool save(const garden::State& s) override {return ready && prefs.putBytes("state",&s,sizeof(s))==sizeof(s);}
} storage;
net::Channels channels{};
QueueHandle_t readings=nullptr;
garden::Controller* controller=nullptr;
hardware::Reading reading;
bool runtimeReady=false,clockFault=false,commissioned=false;
char bootId[20];
uint32_t lastTelemetry=0,lastSerial=0,sequence=0,dropped=0;

void sensorTask(void*) {
  DHT dht(runtime::dhtPin,DHT22);dht.begin();
  analogReadResolution(12);
  analogSetPinAttenuation(runtime::soilPin,ADC_11db);analogSetPinAttenuation(runtime::lightPin,ADC_11db);
  hardware::Reading r;uint32_t lastAir=millis()-runtime::airMs;
  for(;;) {
    if(uint32_t(millis()-lastAir)>=runtime::airMs) {
      r.temperature=dht.readTemperature();r.humidity=dht.readHumidity();r.airMs=millis();lastAir=r.airMs;
    }
    r.soilRaw=hardware::medianRead(runtime::soilPin);r.lightRaw=hardware::medianRead(runtime::lightPin);
    r.soil.valid=SG_CALIBRATION_VERIFIED && sensors::convert(r.soilRaw,SG_DRY_RAW,SG_WET_RAW,r.soil.soil);
    r.soil.tankOK=digitalRead(runtime::floatPin)==LOW;
    r.soil.sampledMs=millis();r.measuredAt=net::utc();
    xQueueOverwrite(readings,&r);
    vTaskDelay(pdMS_TO_TICKS(runtime::sensorMs));
  }
}
void publish(uint32_t now) {
  JsonDocument j;
  j["schema_version"]=1;j["build_stage"]=runtime::telemetryOnly?"runtime_telemetry_only":"runtime_unverified";
  j["device_id"]=SG_DEVICE_ID;j["boot_id"]=bootId;j["sample_seq"]=++sequence;
  j["uptime_ms"]=reading.soil.sampledMs;serializeTime(j,clockFault?0:reading.measuredAt);
  j["data_origin"]="real";j["calibration_id"]=SG_CALIBRATION_ID;
  j["soil_raw"]=reading.soilRaw;j["light_raw"]=reading.lightRaw;j["light_lux"]=nullptr;
  bool valid=reading.soil.valid && uint32_t(now-reading.soil.sampledMs)<=runtime::config().staleMs;
  j["soil_valid"]=valid;if(valid) j["soil_pct"]=reading.soil.soil;else j["soil_pct"]=nullptr;
  bool air=std::isfinite(reading.temperature) && std::isfinite(reading.humidity)
    && reading.temperature>=-40 && reading.temperature<=80 && reading.humidity>=0 && reading.humidity<=100
    && uint32_t(now-reading.airMs)<=6000;
  j["air_valid"]=air;
  if(air) {j["temperature_c"]=reading.temperature;j["humidity_pct"]=reading.humidity;}
  else {j["temperature_c"]=nullptr;j["humidity_pct"]=nullptr;}
  j["tank_ok"]=reading.soil.tankOK;j["pump_on"]=pump.running();j["mode"]=protocol::mode(controller->mode());
  j["commissioned"]=commissioned;j["storage_fault"]=controller->fault();
  j["telemetry_only"]=runtime::telemetryOnly;j["wifi_connected"]=(WiFi.status()==WL_CONNECTED);
  j["telemetry_http_status"]=net::telemetryStatus.load();
  j["telemetry_sent"]=net::telemetrySent.load();j["telemetry_failures"]=net::telemetryFailures.load();
  j["clock_ready"]=net::clockReady.load();j["clock_fault"]=clockFault;
  j["server_available"]=net::contacted.load() && uint32_t(now-net::lastContactMs.load())<=60000;
  j["last_command_seq"]=controller->state().lastCommand;j["queued_events"]=controller->state().eventCount;
  if(uxQueueMessagesWaiting(channels.telemetry)) ++dropped;
  j["telemetry_overwrites"]=dropped;
  net::JsonPacket packet;
  if(measureJson(j)>=sizeof(packet.body)) {controller->emergencyStop(now);return;}
  serializeJson(j,packet.body,sizeof(packet.body));xQueueOverwrite(channels.telemetry,&packet);
  Serial.println(packet.body);
}
// Human-readable preview; not a telemetry record and does not consume sample_seq.
void printLive(uint32_t now) {
  bool soil=reading.soil.valid && uint32_t(now-reading.soil.sampledMs)<=runtime::config().staleMs;
  bool air=std::isfinite(reading.temperature) && std::isfinite(reading.humidity)
    && reading.temperature>=-40 && reading.temperature<=80 && reading.humidity>=0 && reading.humidity<=100
    && uint32_t(now-reading.airMs)<=6000;
  Serial.print("# live soil=");
  if(soil) {Serial.print(reading.soil.soil,1);Serial.print("%");} else Serial.print("invalid");
  Serial.print(" temp=");
  if(air) {Serial.print(reading.temperature,1);Serial.print("C humidity=");Serial.print(reading.humidity,1);Serial.print("%");}
  else Serial.print("invalid humidity=invalid");
  Serial.printf(" light_raw=%d tank=%s pump=%s wifi=%s clock=%s http=%d\n",
    reading.lightRaw,reading.soil.tankOK?"OK":"LOW",pump.running()?"ON":"OFF",
    WiFi.status()==WL_CONNECTED?"OK":"WAIT",net::clockReady.load()&&!clockFault?"OK":"WAIT",
    net::telemetryStatus.load());
}
void publishEvent() {
  const garden::State& state=controller->state();
  if(!state.eventCount || state.events[0].reason==garden::Reason::Running) return;
  const garden::Event& e=state.events[0];net::EventPacket packet;packet.id=e.id;
  JsonDocument j;j["schema_version"]=1;j["device_id"]=SG_DEVICE_ID;j["event_id"]=e.id;j["command_seq"]=e.commandSeq;
  j["started_at"]=e.startedAt;j["planned_ms"]=e.plannedMs;
  if(e.reason==garden::Reason::Reboot) j["actual_ms"]=nullptr;else j["actual_ms"]=e.actualMs;
  j["source"]=protocol::source(e.source);j["reason"]=protocol::reason(e.reason);
  serializeJson(j,packet.json.body,sizeof(packet.json.body));xQueueOverwrite(channels.events,&packet);
}
void setup() {
  bool outputReady=pump.begin();pump.off();Serial.begin(115200);
  snprintf(bootId,sizeof(bootId),"%08lx%08lx",(unsigned long)esp_random(),(unsigned long)esp_random());
  storage.ready=storage.prefs.begin("smartgreen-v1",false);
  garden::State state;
  if(!storage.ready) state.magic=0;
  else if(storage.prefs.isKey("state")) {
    if(storage.prefs.getBytesLength("state")!=sizeof(state)
       || storage.prefs.getBytes("state",&state,sizeof(state))!=sizeof(state)) state.magic=0;
  }
  garden::Config cfg=runtime::config();
  cfg.commissioned=cfg.commissioned && sensors::calibrated(SG_DRY_RAW,SG_WET_RAW) && outputReady;
  commissioned=cfg.commissioned && cfg.valid();
  controller=new garden::Controller(cfg,state,storage,millis(),&pump);
  channels.telemetry=xQueueCreate(1,sizeof(net::JsonPacket));channels.commands=xQueueCreate(1,sizeof(net::Inbound));
  channels.acks=xQueueCreate(1,sizeof(net::Ack));channels.events=xQueueCreate(1,sizeof(net::EventPacket));
  channels.eventAcks=xQueueCreate(1,sizeof(uint32_t));readings=xQueueCreate(1,sizeof(hardware::Reading));
  if(!channels.telemetry || !channels.commands || !channels.acks || !channels.events || !channels.eventAcks || !readings || !outputReady) {
    controller->emergencyStop(millis());Serial.println("# runtime init failure; output locked");return;
  }
  if(xTaskCreatePinnedToCore(sensorTask,"sensors",4096,nullptr,1,nullptr,1)!=pdPASS
     || xTaskCreatePinnedToCore(net::task,"network",12288,&channels,1,nullptr,0)!=pdPASS) {
    controller->emergencyStop(millis());Serial.println("# task init failure; output locked");return;
  }
  runtimeReady=true;
  if(runtime::telemetryOnly) Serial.println("# Runtime: telemetry only; pump locked; remote command polling disabled.");
  Serial.println("# Runtime candidate: pump locked until commissioning; no commands over Serial. Network config local.");
}
void loop() {
  if(!runtimeReady) {pump.off();delay(100);return;}
  uint32_t now=millis();pump.heartbeat();
  xQueueReceive(readings,&reading,0);
  reading.soil.tankOK=digitalRead(runtime::floatPin)==LOW;
  int64_t utc=net::utc();
  static int64_t lastUtc=0;static uint32_t clockMs=0;
  if(utc>=1700000000) {
    if(lastUtc && llabs((utc-lastUtc)-static_cast<int64_t>(uint32_t(now-clockMs)/1000))>10) clockFault=true;
    lastUtc=utc;clockMs=now;
  }
  if(clockFault) {controller->emergencyStop(now);utc=0;}
  uint32_t stopped;garden::Reason why;
  if(pump.takeTrip(stopped,why)) controller->externalStop(stopped,why);
  net::Inbound in;
  if(uxQueueSpacesAvailable(channels.acks) && xQueueReceive(channels.commands,&in,0)==pdTRUE) {
    const char* result;
    if(in.rejection[0]) result=in.rejection;
    else if(in.command.kind==garden::Command::Kind::Water && in.command.source==garden::Source::AI && !SG_AI_COMMANDS_ENABLED) result="ai_disabled";
    else result=controller->command(in.command,now,utc,reading.soil);
    net::Ack ack;ack.seq=in.command.seq;snprintf(ack.result,sizeof(ack.result),"%s",result);
    xQueueSend(channels.acks,&ack,0);
  }
  controller->tick(now,utc,reading.soil);
  uint32_t id;
  if(xQueueReceive(channels.eventAcks,&id,0)==pdTRUE && controller->state().eventCount
     && controller->state().events[0].id==id) {
    if(controller->acknowledgeEvent(id)) {net::EventPacket discarded;xQueueReceive(channels.events,&discarded,0);}
  }
  if(!runtime::telemetryOnly) publishEvent();
  if(reading.soil.sampledMs && (!sequence || uint32_t(now-lastTelemetry)>=runtime::telemetryMs)) {lastTelemetry=now;publish(now);}
  if(reading.soil.sampledMs && uint32_t(now-lastSerial)>=runtime::serialMs) {lastSerial=now;printLive(now);}
  delay(5);
}
