#ifndef CONFIG_H
#define CONFIG_H

#include <stdint.h>

// ==========================================
// GPIO Pin Assignments
// ==========================================
#define PIN_RELAY           26  // 5V Relay trigger (Active LOW/HIGH)
#define PIN_BUZZER          27  // 2N2222 NPN Base drive for 5V Buzzer
#define PIN_LED_ALERT       25  // Red LED: Movement detected
#define PIN_LED_LINK        33  // Green LED: CSI frame received/locked

// ==========================================
// Wi-Fi & CSI Configuration
// ==========================================
#define WIFI_CHANNEL        6
#define CSI_MAX_SUBCARRIERS 64
#define CSI_TARGET_MAC      {0x1A, 0xFE, 0x34, 0xD2, 0x51, 0x90} // Match Tx MAC or accept any

// ==========================================
// Mathematical DSP Parameters
// ==========================================
#define WINDOW_SIZE                 40      // N = 40 samples (~0.5s @ 80Hz)
#define VARIANCE_THRESHOLD_HIGH     18.5f   // Trigger threshold
#define VARIANCE_THRESHOLD_LOW      8.0f    // Release threshold (Hysteresis)
#define EMA_ALPHA                   0.25f   // Exponential Moving Average weight [0.0 - 1.0]
#define ALARM_HOLDOFF_MS            1500    // Min alarm sustain duration (ms)

// ==========================================
// Telemetry & Serial
// ==========================================
#define SERIAL_BAUD_RATE    115200

#endif // CONFIG_H
