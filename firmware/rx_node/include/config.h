#ifndef CONFIG_H
#define CONFIG_H

#include <stdint.h>

// ==========================================
// GPIO Pin Assignments
// ==========================================
#define PIN_RELAY           26  // 5V Relay trigger
#define PIN_BUZZER          27  // 2N2222 NPN Base drive for 5V Buzzer
#define PIN_LED_ALERT       25  // Red LED: Movement / Alarm
#define PIN_LED_LINK        33  // Green LED: CSI Packet Lock / Watchdog

// ==========================================
// Wi-Fi & CSI Configuration
// ==========================================
#define WIFI_CHANNEL        6
#define WIFI_SSID           "Manuja"
#define WIFI_PASS           "AHTBD3B03NE"
#define CSI_MAX_SUBCARRIERS 64

// ==========================================
// Edge Case Resilient DSP Parameters
// ==========================================
#define WINDOW_SIZE                 40      // N = 40 samples (~0.5s @ 80Hz)
#define EMA_ALPHA                   0.25f   // Fast EMA factor for movement
#define BASELINE_BETA               0.005f  // Very slow baseline drift adaptation

// Multi-Tier Detection Thresholds (Relative above dynamic baseline)
#define DELTA_THRESH_SINGLE         16.0f   // Baseline + 16.0 = 1 Human
#define DELTA_THRESH_MULTI          35.0f   // Baseline + 35.0 = 2 Humans
#define DELTA_THRESH_CROWD          65.0f   // Baseline + 65.0 = 3+ Humans
#define HYSTERESIS_DELTA_LOW        6.0f    // Release threshold offset

// Edge Case 1: Impulse / EMI Spike Rejection
#define IMPULSE_MAX_SPIKE_RATIO     4.5f    // Reject single-frame jump > 4.5x mean
#define CONSECUTIVE_TRIGGER_FRAMES  3       // Require 3 consecutive high frames

// Edge Case 2: Static / Seated Occupant Retention
#define STATIC_HOLD_DURATION_MS     12000   // Retain presence state for 12s after motion stops
#define MICRO_MOTION_VAR_MIN        0.9f    // Subtle chest/breathing variance band
#define MICRO_MOTION_VAR_MAX        4.0f

// Edge Case 3: Packet Loss Watchdog
#define PACKET_WATCHDOG_TIMEOUT_MS  350     // Flag link loss if no packet within 350ms

// Edge Case 4: Relay Chattering Protection
#define RELAY_MIN_ACTIVE_MS         1500    // Minimum dwell time for mechanical relay
#define RELAY_REFRACTORY_MS         800     // Minimum OFF cooldown before re-trigger

// Serial Telemetry
#define SERIAL_BAUD_RATE            115200

#endif // CONFIG_H
