#pragma once
#include <Arduino.h>
#include <ArduinoJson.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <esp_sntp.h>
#include <atomic>
#include "runtime_config.h"
#include "protocol.h"

namespace net {
struct JsonPacket {char body[2048]{};};
struct Ack {uint32_t seq=0;char result[64]{};};
struct EventPacket {uint32_t id=0;JsonPacket json;};
struct Inbound {garden::Command command;char rejection[64]{};};
struct Channels {
  QueueHandle_t telemetry,commands,acks,events,eventAcks;
};
// Accessed across tasks without sharing controller or ArduinoJson documents.
extern std::atomic<bool> clockReady;
extern std::atomic<uint32_t> lastContactMs;
extern std::atomic<bool> contacted;
inline int64_t utc() {return clockReady.load() ? static_cast<int64_t>(time(nullptr)) : 0;}
inline void syncCallback(timeval*) {clockReady.store(true);}
inline bool identityOK(const char* s) {
  if(!s || !*s || strlen(s)>64) return false;
  for(const char* p=s;*p;++p) if(!isalnum(static_cast<unsigned char>(*p)) && *p!='-' && *p!='_') return false;
  return true;
}
// Bounded response sink: never allocate an arbitrary response body from a server.
class Body : public Stream {
 public:
  String text;bool overflow=false;
  size_t write(uint8_t b) override {if(text.length()>=4096) {overflow=true;return 0;}text+=char(b);return 1;}
  size_t write(const uint8_t* data,size_t len) override {
    size_t room=4096-text.length();size_t n=len<room?len:room;
    for(size_t i=0;i<n;++i) text+=char(data[i]);
    if(n<len) overflow=true;
    return n;
  }
  int available() override{return 0;}int read() override{return -1;}int peek() override{return -1;}void flush() override{}
};
inline int request(const String& path,const char* body,String& response) {
  response="";
  String base=SG_BACKEND_URL;
  if(!identityOK(SG_DEVICE_ID) || !strlen(SG_API_KEY) || base.endsWith("/")) return -1;
  bool tls=base.startsWith("https://");
  if(!tls && !(SG_ALLOW_LAN_HTTP && base.startsWith("http://"))) return -1;
  if(tls && !strlen(SG_ROOT_CA)) return -1;
  WiFiClient plain;WiFiClientSecure secure;HTTPClient http;
  if(tls) {secure.setCACert(SG_ROOT_CA);secure.setHandshakeTimeout(3);}
  WiFiClient& client=tls?static_cast<WiFiClient&>(secure):plain;
  if(!http.begin(client,base+path)) return -1;
  http.setConnectTimeout(1500);http.setTimeout(1500);http.setFollowRedirects(HTTPC_DISABLE_FOLLOW_REDIRECTS);
  http.addHeader("X-API-Key",SG_API_KEY);http.addHeader("Content-Type","application/json");
  int code=body?http.POST(String(body)):http.GET();
  if(code>0) {
    if(http.getSize()>4096) code=-2;
    else {Body sink;int read=http.writeToStream(&sink);if(read<0 || sink.overflow) code=-2;else response=sink.text;}
  }
  http.end();
  if(code>=200 && code<300) {lastContactMs.store(millis());contacted.store(true);}
  return code;
}
inline void task(void* argument) {
  Channels& q=*static_cast<Channels*>(argument);
  WiFi.mode(WIFI_STA);WiFi.setAutoReconnect(true);
  sntp_set_time_sync_notification_cb(syncCallback);configTime(0,0,"pool.ntp.org","time.google.com");
  Ack ack;bool pendingAck=false,waitingCore=false;
  JsonPacket telemetry;bool pendingTelemetry=false;
  uint32_t lastReconnect=millis()-15000;
  String root=String("/api/v1/devices/")+SG_DEVICE_ID;
  for(;;) {
    if(WiFi.status()!=WL_CONNECTED) {
      if(strlen(SG_WIFI_SSID) && uint32_t(millis()-lastReconnect)>=15000) {lastReconnect=millis();WiFi.begin(SG_WIFI_SSID,SG_WIFI_PASSWORD);}
      vTaskDelay(pdMS_TO_TICKS(200));continue;
    }
    String response;
    if(!pendingAck && xQueueReceive(q.acks,&ack,0)==pdTRUE) {pendingAck=true;waitingCore=false;}
    if(pendingAck) {
      JsonDocument j;j["schema_version"]=1;j["device_id"]=SG_DEVICE_ID;j["command_seq"]=ack.seq;j["result"]=ack.result;
      String body;serializeJson(j,body);
      int code=request(root+"/commands/"+ack.seq+"/ack",body.c_str(),response);
      if(code>=200 && code<300) pendingAck=false;
    }
    if(!pendingAck && !waitingCore) {
      // Ask oldest unacknowledged command, including an already executed seq after a reboot.
      // Core's persisted sequence prevents replay. Backend must ACK even a rejected command.
      int code=request(root+"/commands/next?after_seq=0",nullptr,response);
      if(code==200) {
        JsonDocument j;Inbound in;
        if(!deserializeJson(j,response)) {
          const char* error=protocol::parse(j,SG_DEVICE_ID,SG_MAX_PULSE_MS,in.command);
          // Never acknowledge a wrong-device or unidentifiable response as this device.
          bool identifiable=protocol::equal(j["device_id"],SG_DEVICE_ID) && j["command_seq"].is<uint32_t>() && j["command_seq"].as<uint32_t>()>0;
          if(identifiable) {
            in.command.seq=j["command_seq"].as<uint32_t>();
            if(error) snprintf(in.rejection,sizeof(in.rejection),"invalid_%s",error);
            if(xQueueSend(q.commands,&in,0)==pdTRUE) waitingCore=true;
          }
        }
      }
    }
    EventPacket event;
    if(xQueuePeek(q.events,&event,0)==pdTRUE) {
      int code=request(root+"/events",event.json.body,response);
      JsonDocument j;
      if(code>=200 && code<300 && !deserializeJson(j,response)
         && j["event_id"].is<uint32_t>() && j["event_id"].as<uint32_t>()==event.id) {
        xQueueSend(q.eventAcks,&event.id,0);
      }
    }
    if(!pendingTelemetry && xQueueReceive(q.telemetry,&telemetry,0)==pdTRUE) pendingTelemetry=true;
    if(pendingTelemetry) {
      int code=request(root+"/telemetry",telemetry.body,response);
      if(code>=200 && code<300) pendingTelemetry=false;
    }
    vTaskDelay(pdMS_TO_TICKS(runtime::pollMs));
  }
}
}
