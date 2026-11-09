/**
 * Wi-Fi CSI-Based Human Presence and Movement Monitoring System
 * Transmitter Node (ESP32-WROOM-32)
 *
 * Transmits fixed-rate 802.11 raw frames at 80 Hz on Channel 6.
 * Acts as the continuous RF illumination source for through-wall sensing.
 */

#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_log.h"
#include "nvs_flash.h"
#include "esp_now.h"

#define WIFI_CHANNEL        6
#define PACKET_RATE_HZ      80
#define PACKET_PAYLOAD_LEN  64

static const char *TAG = "CSI_TX_NODE";
static uint8_t s_broadcast_mac[ESP_NOW_ETH_ALEN] = { 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF };

void app_main(void) {
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);

    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));
    ESP_ERROR_CHECK(esp_wifi_set_storage(WIFI_STORAGE_RAM));
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_start());

    ESP_ERROR_CHECK(esp_wifi_set_channel(WIFI_CHANNEL, WIFI_SECOND_CHAN_NONE));
    ESP_LOGI(TAG, "Wi-Fi initialized on Channel %d", WIFI_CHANNEL);

    ESP_ERROR_CHECK(esp_now_init());

    esp_now_peer_info_t peer_info = {};
    memcpy(peer_info.peer_addr, s_broadcast_mac, ESP_NOW_ETH_ALEN);
    peer_info.channel = WIFI_CHANNEL;
    peer_info.encrypt = false;
    ESP_ERROR_CHECK(esp_now_add_peer(&peer_info));

    uint8_t payload[PACKET_PAYLOAD_LEN];
    uint32_t packet_seq = 0;
    const TickType_t delay_ticks = pdMS_TO_TICKS(1000 / PACKET_RATE_HZ);

    ESP_LOGI(TAG, "Starting transmission at %d Hz...", PACKET_RATE_HZ);

    while (1) {
        memcpy(payload, &packet_seq, sizeof(packet_seq));
        memset(payload + sizeof(packet_seq), 0xAA, PACKET_PAYLOAD_LEN - sizeof(packet_seq));

        esp_now_send(s_broadcast_mac, payload, PACKET_PAYLOAD_LEN);
        packet_seq++;

        vTaskDelay(delay_ticks);
    }
}
