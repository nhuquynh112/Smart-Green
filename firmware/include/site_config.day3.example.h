#pragma once
// Day 3 starting configuration. Credentials blank; calibration remains unverified until checked.
// Copy to site_config.h locally; build using -e day3. Never commit credentials.
#define SG_WIFI_SSID ""
#define SG_WIFI_PASSWORD ""
#define SG_BACKEND_URL "" // e.g. http://192.168.1.10:8000 ; no trailing slash
#define SG_API_KEY ""
#define SG_DEVICE_ID "garden-01"
#define SG_ALLOW_LAN_HTTP false // true ONLY for a trusted isolated development LAN
#define SG_ROOT_CA "" // PEM CA for HTTPS; never disable certificate verification
#define SG_HARDWARE_VERIFIED false // relay logic, OFF at reset, float, measured flow and limits
#define SG_CALIBRATION_VERIFIED false
#define SG_AI_COMMANDS_ENABLED false // after real-data evaluation + integration acceptance only
#define SG_DRY_RAW 2511
#define SG_WET_RAW 979
#define SG_CALIBRATION_ID "soil-2511-979"
#define SG_RELAY_ACTIVE_LOW false // matches tested bringup; verify before powering relay/load
// EXAMPLES ONLY: choose limits from the actual plant, soil and measured pump flow.
#define SG_LOW 30.0f
#define SG_HIGH 45.0f
#define SG_PULSE_MS 1000
#define SG_MAX_PULSE_MS 1000
#define SG_COOLDOWN_MS 600000
#define SG_DAY_MS 4000
#define SG_DAY_STARTS 4
