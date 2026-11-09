/**
 * Wi-Fi CSI Receiver Node - Arduino IDE Compatible
 * Open directly in Arduino IDE (Select "ESP32 Dev Module")
 */

#include <WiFi.h>
#include <esp_wifi.h>
#include <math.h>

// Pins
#define PIN_RELAY       26
#define PIN_BUZZER      27
#define PIN_LED_ALERT   25
#define PIN_LED_LINK    33

#define WIFI_CHANNEL    6
#define WINDOW_SIZE     40

// Threshold offsets
#define THRESH_SINGLE   16.0f
#define THRESH_MULTI    35.0f
#define THRESH_LOW      6.0f

static float g_window[WINDOW_SIZE] = {0};
static int g_idx = 0;
static int g_count = 0;
static float g_baseline = 1.2f;
static float g_ema = 1.2f;
static int g_state = 0; // 0:Empty, 1:Single, 2:Multi, 3:Static, 4:Loss
static uint32_t g_last_pkt = 0;
static uint32_t g_last_motion = 0;

void IRAM_ATTR csi_callback(void *ctx, wifi_csi_info_t *info) {
    if (!info || !info->buf) return;
    g_last_pkt = millis();

    digitalWrite(PIN_LED_LINK, !digitalRead(PIN_LED_LINK));

    int8_t *csi_bytes = (int8_t *)info->buf;
    int subcarriers = min((int)(info->len / 2), 64);

    float sum_amp = 0.0f;
    for (int i = 0; i < subcarriers; i++) {
        int8_t imag = csi_bytes[2 * i];
        int8_t real = csi_bytes[2 * i + 1];
        sum_amp += sqrtf((float)(real * real + imag * imag));
    }
    float avg_amp = sum_amp / (float)subcarriers;

    // EMI Spike clamp
    if (g_count > 5) {
        float prev = g_window[(g_idx + WINDOW_SIZE - 1) % WINDOW_SIZE];
        if (prev > 1.0f && avg_amp > prev * 4.5f) {
            avg_amp = prev * 1.5f;
        }
    }

    g_window[g_idx] = avg_amp;
    g_idx = (g_idx + 1) % WINDOW_SIZE;
    if (g_count < WINDOW_SIZE) { g_count++; return; }

    // Sliding Mean & Variance
    float mean = 0.0f;
    for (int i = 0; i < WINDOW_SIZE; i++) mean += g_window[i];
    mean /= (float)WINDOW_SIZE;

    float raw_var = 0.0f;
    for (int i = 0; i < WINDOW_SIZE; i++) {
        float diff = g_window[i] - mean;
        raw_var += diff * diff;
    }
    raw_var /= (float)WINDOW_SIZE;

    // Fast EMA
    g_ema = (0.25f * raw_var) + (0.75f * g_ema);

    // Adaptive Baseline (in quiet periods)
    if (g_ema < (g_baseline + 8.0f)) {
        g_baseline = (0.995f * g_baseline) + (0.005f * raw_var);
        if (g_baseline < 0.5f) g_baseline = 0.5f;
    }

    float t_single = g_baseline + THRESH_SINGLE;
    float t_multi  = g_baseline + THRESH_MULTI;
    float t_rel    = g_baseline + THRESH_LOW;

    uint32_t now = millis();
    if (g_ema >= t_single) {
        g_last_motion = now;
        g_state = (g_ema >= t_multi) ? 2 : 1;
    } else if (g_ema < t_rel) {
        if ((now - g_last_motion) < 12000) {
            g_state = 3; // Static Presence hold
        } else {
            g_state = 0; // Empty
        }
    }

    bool alert = (g_state == 1 || g_state == 2);
    digitalWrite(PIN_RELAY, alert ? HIGH : LOW);
    digitalWrite(PIN_BUZZER, alert ? HIGH : LOW);
    digitalWrite(PIN_LED_ALERT, alert ? HIGH : LOW);

    // Stream telemetry to Laptop: $CSI,timestamp_ms,rssi,raw_var,ema_var,baseline,state_id
    Serial.printf("$CSI,%lu,%d,%.2f,%.2f,%.2f,%d\n",
                  now, info->rx_ctrl.rssi, raw_var, g_ema, g_baseline, g_state);
}

void setup() {
    Serial.begin(115200);
    delay(500);

    pinMode(PIN_RELAY, OUTPUT);
    pinMode(PIN_BUZZER, OUTPUT);
    pinMode(PIN_LED_ALERT, OUTPUT);
    pinMode(PIN_LED_LINK, OUTPUT);

    digitalWrite(PIN_RELAY, LOW);
    digitalWrite(PIN_BUZZER, LOW);
    digitalWrite(PIN_LED_ALERT, LOW);
    digitalWrite(PIN_LED_LINK, LOW);

    WiFi.mode(WIFI_STA);
    WiFi.disconnect();

    esp_wifi_set_promiscuous(true);
    esp_wifi_set_channel(WIFI_CHANNEL, WIFI_SECOND_CHAN_NONE);

    wifi_csi_config_t csi_config = {
        .lltf_en = true,
        .htltf_en = true,
        .stbc_htltf2_en = true,
        .ltf_merge_en = true,
        .channel_filter_en = false,
        .manu_scale = false,
    };
    esp_wifi_set_csi_config(&csi_config);
    esp_wifi_set_csi_rx_cb(csi_callback, NULL);
    esp_wifi_set_csi(true);

    Serial.println("[*] ESP32 CSI Rx Ready on Channel 6");
}

void loop() {
    // Watchdog check for packet loss
    if (g_count >= WINDOW_SIZE && (millis() - g_last_pkt) > 400) {
        g_state = 4; // Link loss
        digitalWrite(PIN_LED_LINK, LOW);
        Serial.printf("$CSI,%lu,-99,0.0,0.0,%.2f,4\n", millis(), g_baseline);
    }
    delay(100);
}
