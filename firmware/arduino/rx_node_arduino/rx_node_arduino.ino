/**
 * Wi-Fi CSI Receiver Node - Single ESP32 + Router/iPhone Mode
 * Works with 1 ESP32, an existing Wi-Fi Router, or iPhone Personal Hotspot.
 */

#include <WiFi.h>
#include <WiFiUdp.h>
#include <esp_wifi.h>
#include <math.h>

// ==========================================
// Wi-Fi Configuration
// Put your Home Router or iPhone Hotspot SSID & Password here.
// (Ensure 2.4 GHz band is enabled on iPhone: "Maximize Compatibility" ON)
// ==========================================
const char* WIFI_SSID = "Manuja";
const char* WIFI_PASS = "AHTBD3B03NE";

// Output Pin Assignments
#define PIN_RELAY       26
#define PIN_BUZZER      27
#define PIN_LED_ALERT   25
#define PIN_LED_LINK    33

#define WINDOW_SIZE     40
#define THRESH_SINGLE   5.0f
#define THRESH_MULTI    18.0f
#define THRESH_LOW      1.2f

static WiFiUDP udp;
static IPAddress gatewayIP;
static float g_window[WINDOW_SIZE] = {0};
static int g_idx = 0;
static int g_count = 0;
static float g_baseline = 1.0f;
static float g_ema = 1.0f;
static int g_state = 0; // 0:Empty, 1:Single, 2:Multi, 3:Static, 4:Loss
static uint32_t g_last_pkt = 0;
static uint32_t g_last_motion = 0;
static float g_prev_amp[64] = {0};
static bool g_has_prev = false;

void IRAM_ATTR csi_callback(void *ctx, wifi_csi_info_t *info) {
    if (!info || !info->buf) return;
    g_last_pkt = millis();

    digitalWrite(PIN_LED_LINK, !digitalRead(PIN_LED_LINK));

    int8_t *csi_bytes = (int8_t *)info->buf;
    int subcarriers = min((int)(info->len / 2), 64);

    // Per-subcarrier differential multipath energy (prevents frequency-selective fading cancellation)
    float sum_diff = 0.0f;
    for (int i = 0; i < subcarriers; i++) {
        int8_t imag = csi_bytes[2 * i];
        int8_t real = csi_bytes[2 * i + 1];
        float amp = sqrtf((float)(real * real + imag * imag));
        if (g_has_prev) {
            float diff = amp - g_prev_amp[i];
            sum_diff += diff * diff;
        }
        g_prev_amp[i] = amp;
    }
    g_has_prev = true;

    float raw_var = (subcarriers > 0) ? (sum_diff / (float)subcarriers) : 0.0f;

    // Fast EMA of subcarrier disruption
    g_ema = (0.25f * raw_var) + (0.75f * g_ema);

    // Adaptive baseline tracker (adapts only during quiet baseline periods)
    if (g_ema < (g_baseline + 3.0f)) {
        g_baseline = (0.995f * g_baseline) + (0.005f * raw_var);
        if (g_baseline < 0.4f) g_baseline = 0.4f;
    }

    float t_single = g_baseline + THRESH_SINGLE;
    float t_multi  = g_baseline + THRESH_MULTI;
    float t_rel    = g_baseline + THRESH_LOW;

    uint32_t now = millis();
    if (g_ema >= t_single) {
        g_last_motion = now;
        g_state = (g_ema >= t_multi) ? 2 : 1;
    } else if (g_ema >= t_rel) {
        g_last_motion = now;
        g_state = 1; // Subtle motion
    } else {
        if ((now - g_last_motion) < 8000) {
            g_state = 3; // Static presence hold (8s)
        } else {
            g_state = 0; // Empty
        }
    }

    bool alert = (g_state == 1 || g_state == 2 || g_state == 3);
    digitalWrite(PIN_RELAY, alert ? HIGH : LOW);
    digitalWrite(PIN_BUZZER, (g_state == 1 || g_state == 2) ? HIGH : LOW);
    digitalWrite(PIN_LED_ALERT, alert ? HIGH : LOW);

    // Telemetry output to Laptop: $CSI,timestamp_ms,rssi,raw_var,ema_var,baseline,state_id
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

    // Connect to Wi-Fi Router or iPhone Hotspot
    Serial.print("[*] Connecting to Wi-Fi: ");
    Serial.println(WIFI_SSID);

    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASS);

    uint32_t start_connect = millis();
    while (WiFi.status() != WL_CONNECTED && (millis() - start_connect) < 8000) {
        delay(300);
        Serial.print(".");
    }

    if (WiFi.status() == WL_CONNECTED) {
        gatewayIP = WiFi.gatewayIP();
        Serial.println("\n[+] Wi-Fi Connected!");
        Serial.print("[+] ESP32 IP: "); Serial.println(WiFi.localIP());
        Serial.print("[+] Router Gateway: "); Serial.println(gatewayIP);
        udp.begin(12345);
    } else {
        Serial.println("\n[!] Wi-Fi connection timed out. Falling back to Promiscuous Sniffer Mode on Channel 6.");
        WiFi.disconnect();
        esp_wifi_set_promiscuous(true);
        esp_wifi_set_channel(6, WIFI_SECOND_CHAN_NONE);
    }

    // Enable Channel State Information (CSI)
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

    Serial.println("[*] Wi-Fi CSI Active. Sensing Multipath Disruption...");
}

void loop() {
    // If connected to router, send high-rate micro UDP pings (60 Hz) to gateway
    // Router returns 802.11 ACK frames -> triggers csi_callback continuously!
    if (WiFi.status() == WL_CONNECTED) {
        udp.beginPacket(gatewayIP, 80);
        udp.write((const uint8_t*)"\xAA\xBB", 2);
        udp.endPacket();
        delay(16); // ~60 Hz packet rate
    } else {
        delay(100);
    }

    // Link watchdog (2.0s timeout to allow heavy human body RF absorption without false link-loss)
    if (g_count >= WINDOW_SIZE && (millis() - g_last_pkt) > 2000) {
        g_state = 4;
        digitalWrite(PIN_LED_LINK, LOW);
        Serial.printf("$CSI,%lu,-99,0.0,0.0,%.2f,4\n", millis(), g_baseline);
    }
}
