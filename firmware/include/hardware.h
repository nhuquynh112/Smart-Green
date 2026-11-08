#pragma once
#include <Arduino.h>
#include <DHT.h>
#include <driver/gpio.h>
#include <esp_timer.h>
#include "runtime_config.h"
#include "sensor_math.h"
#include "pump_guard.h"

namespace hardware {
struct Reading {
  garden::Sensor soil;
  int soilRaw=0, lightRaw=0;
  float temperature=NAN,humidity=NAN;
  uint32_t airMs=0;
  int64_t measuredAt=0;
};
inline int medianRead(int pin) {
  int v[15];for(int& x:v) x=analogRead(pin);
  std::sort(v,v+15);return v[7];
}
// esp_timer task checks relay even if HTTP, sensor task or main loop stalls.
// Not an electrical safety cutoff; reset/high-impedance protection must be validated on the board.
class Pump : public garden::PumpOutput {
 public:
  bool begin() {
    digitalWrite(runtime::relayPin,offLevel);pinMode(runtime::relayPin,OUTPUT);
    pinMode(runtime::floatPin,INPUT_PULLUP);
    esp_timer_create_args_t a={};a.callback=guardCallback;a.arg=this;a.name="pump-guard";
    if(esp_timer_create(&a,&timer)!=ESP_OK) return false;
    ready=esp_timer_start_periodic(timer,10000)==ESP_OK;
    return ready;
  }
  bool start(uint32_t duration) override {
    portENTER_CRITICAL(&mux);
    lastDuration=0;
    bool ok=ready && runtime::allowPump(SG_HARDWARE_VERIFIED,SG_CALIBRATION_VERIFIED) && !tripped && !on
      && duration && duration<=SG_MAX_PULSE_MS && gpio_get_level((gpio_num_t)runtime::floatPin)==0;
    if(ok) {started=millis();limit=duration;on=true;gpio_set_level((gpio_num_t)runtime::relayPin,!offLevel);}
    portEXIT_CRITICAL(&mux);
    return ok;
  }
  void off() override {
    portENTER_CRITICAL(&mux);gpio_set_level((gpio_num_t)runtime::relayPin,offLevel);if(on) lastDuration=uint32_t(millis()-started);on=false;portEXIT_CRITICAL(&mux);
  }
  uint32_t actualDuration(uint32_t) override {portENTER_CRITICAL(&mux);uint32_t v=lastDuration;portEXIT_CRITICAL(&mux);return v;}
  void heartbeat() {portENTER_CRITICAL(&mux);beat=millis();portEXIT_CRITICAL(&mux);}
  bool running() {portENTER_CRITICAL(&mux);bool v=on;portEXIT_CRITICAL(&mux);return v;}
  bool takeTrip(uint32_t& when,garden::Reason& why) {
    portENTER_CRITICAL(&mux);bool v=tripped;
    if(v) {when=stopped;why=reason;tripped=false;}
    portEXIT_CRITICAL(&mux);return v;
  }
 private:
  static constexpr int offLevel=SG_RELAY_ACTIVE_LOW?1:0;
  static void guardCallback(void* p) {static_cast<Pump*>(p)->guard();}
  void guard() {
    uint32_t now=millis();
    portENTER_CRITICAL(&mux);
    if(on) {
      garden::Reason decision=garden::guardReason(now,started,limit,beat,
          gpio_get_level((gpio_num_t)runtime::floatPin)==0);
      if(decision!=garden::Reason::Running) {
        gpio_set_level((gpio_num_t)runtime::relayPin,offLevel);on=false;tripped=true;stopped=now;lastDuration=uint32_t(now-started);
        reason=decision;
      }
    }
    portEXIT_CRITICAL(&mux);
  }
  portMUX_TYPE mux=portMUX_INITIALIZER_UNLOCKED;
  esp_timer_handle_t timer=nullptr;
  bool ready=false,on=false,tripped=false;
  uint32_t started=0,limit=0,beat=0,stopped=0,lastDuration=0;
  garden::Reason reason=garden::Reason::Guard;
};
}
