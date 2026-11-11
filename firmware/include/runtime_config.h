#pragma once
#include "controller.h"
#if __has_include("site_config.h")
#include "site_config.h"
#endif
#include "runtime_profile.h"
#ifndef SG_WIFI_SSID
#define SG_WIFI_SSID ""
#endif
#ifndef SG_WIFI_PASSWORD
#define SG_WIFI_PASSWORD ""
#endif
#ifndef SG_BACKEND_URL
#define SG_BACKEND_URL ""
#endif
#ifndef SG_API_KEY
#define SG_API_KEY ""
#endif
#ifndef SG_DEVICE_ID
#define SG_DEVICE_ID "garden-01"
#endif
#ifndef SG_ROOT_CA
#define SG_ROOT_CA ""
#endif
#ifndef SG_ALLOW_LAN_HTTP
#define SG_ALLOW_LAN_HTTP false
#endif
#ifndef SG_HARDWARE_VERIFIED
#define SG_HARDWARE_VERIFIED false
#endif
#ifndef SG_CALIBRATION_VERIFIED
#define SG_CALIBRATION_VERIFIED false
#endif
#ifndef SG_AI_COMMANDS_ENABLED
#define SG_AI_COMMANDS_ENABLED false
#endif
#ifndef SG_DRY_RAW
#define SG_DRY_RAW -1
#endif
#ifndef SG_WET_RAW
#define SG_WET_RAW -1
#endif
#ifndef SG_CALIBRATION_ID
#define SG_CALIBRATION_ID "uncommissioned"
#endif
#ifndef SG_RELAY_ACTIVE_LOW
#define SG_RELAY_ACTIVE_LOW true
#endif
#ifndef SG_LOW
#define SG_LOW 30.0f
#endif
#ifndef SG_HIGH
#define SG_HIGH 45.0f
#endif
#ifndef SG_PULSE_MS
#define SG_PULSE_MS 1000
#endif
#ifndef SG_MAX_PULSE_MS
#define SG_MAX_PULSE_MS 1000
#endif
#ifndef SG_COOLDOWN_MS
#define SG_COOLDOWN_MS 600000
#endif
#ifndef SG_MANUAL_COOLDOWN_MS
#define SG_MANUAL_COOLDOWN_MS 0
#endif
#ifndef SG_DAY_MS
#define SG_DAY_MS 4000
#endif
#ifndef SG_DAY_STARTS
#define SG_DAY_STARTS 4
#endif
namespace runtime {
constexpr int soilPin=34, lightPin=35, dhtPin=27, floatPin=26, relayPin=25;
constexpr uint32_t telemetryMs=30000, serialMs=3000, sensorMs=1000, airMs=2500, pollMs=1000;
inline garden::Config config() {
  garden::Config c;
  c.commissioned=allowPump(SG_HARDWARE_VERIFIED,SG_CALIBRATION_VERIFIED);
  c.low=SG_LOW;c.high=SG_HIGH;c.aiCeiling=c.low; // AI cannot bypass the dry threshold until deliberately revised.
  c.pulseMs=SG_PULSE_MS;c.maxPulseMs=SG_MAX_PULSE_MS;c.cooldownMs=SG_COOLDOWN_MS;
  c.manualCooldownMs=SG_MANUAL_COOLDOWN_MS;
  c.manualUnlimitedStarts=true; // Manual operation is limited by time budget, not start count.
  c.maxDayMs=SG_DAY_MS;c.maxDayStarts=SG_DAY_STARTS;
  return c;
}
}
