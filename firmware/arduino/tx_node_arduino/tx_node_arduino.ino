/**
 * Wi-Fi CSI Transmitter Node (Beacon) - Arduino IDE Compatible
 * Transmits broadcast packets at 80 Hz on Channel 6
 */

#include <WiFi.h>
#include <esp_wifi.h>
#include <esp_now.h>

#define WIFI_CHANNEL 6

static uint8_t s_broadcast_mac[] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
static uint8_t s_payload[64];
static uint32_t s_pkt_id = 0;

void setup() {
    Serial.begin(115200);
    delay(500);

    WiFi.mode(WIFI_STA);
    WiFi.disconnect();

    // Lock to Channel 6
    esp_wifi_set_channel(WIFI_CHANNEL, WIFI_SECOND_CHAN_NONE);

    if (esp_now_init() != ESP_OK) {
        Serial.println("[!] ESP-NOW Init Failed");
        return;
    }

    esp_now_peer_info_t peerInfo = {};
    memcpy(peerInfo.peer_addr, s_broadcast_mac, 6);
    peerInfo.channel = WIFI_CHANNEL;
    peerInfo.encrypt = false;

    if (esp_now_add_peer(&peerInfo) != ESP_OK) {
        Serial.println("[!] Add Peer Failed");
        return;
    }

    memset(s_payload, 0xAA, sizeof(s_payload));
    Serial.println("[*] ESP32 CSI Tx Broadcasting on Channel 6 @ 80 Hz");
}

void loop() {
    memcpy(s_payload, &s_pkt_id, sizeof(s_pkt_id));
    esp_now_send(s_broadcast_mac, s_payload, sizeof(s_payload));
    s_pkt_id++;
    delay(12); // ~80 Hz
}
