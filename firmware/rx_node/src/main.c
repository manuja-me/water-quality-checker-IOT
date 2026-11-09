/**
 * Wi-Fi CSI-Based Human Presence and Movement Monitoring System
 * Receiver Node (ESP32-WROOM-32)
 *
 * Implements real-time edge mathematical signal processing:
 * - Subcarrier Amplitude Extraction: A_k = sqrt(I_k^2 + Q_k^2)
 * - Sliding Window Variance: V(t) = (1/N) * sum((A_i - mean)^2)
 * - Exponential Moving Average (EMA)
 * - Hysteresis dual-threshold state machine
 * - GPIO actuation: 5V Relay, Piezo Buzzer, Alert LED
 * - Real-time UART telemetry stream
 */

#include <stdio.h>
#include <string.h>
#include <math.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_system.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_log.h"
#include "nvs_flash.h"
#include "driver/gpio.h"
#include "config.h"

static const char *TAG = "CSI_RX_NODE";

// DSP State Variables
static float g_window[WINDOW_SIZE] = {0};
static int g_window_index = 0;
static int g_sample_count = 0;
static float g_ema_variance = 0.0f;
static bool g_movement_detected = false;
static uint32_t g_last_trigger_time = 0;

static void init_peripherals(void) {
    gpio_config_t io_conf = {
        .pin_bit_mask = (1ULL << PIN_RELAY) | (1ULL << PIN_BUZZER) | 
                        (1ULL << PIN_LED_ALERT) | (1ULL << PIN_LED_LINK),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_ENABLE,
        .intr_type = GPIO_INTR_DISABLE
    };
    gpio_config(&io_conf);

    // Initial state: all OFF
    gpio_set_level(PIN_RELAY, 0);
    gpio_set_level(PIN_BUZZER, 0);
    gpio_set_level(PIN_LED_ALERT, 0);
    gpio_set_level(PIN_LED_LINK, 0);
}

static void csi_rx_callback(void *ctx, wifi_csi_info_t *info) {
    if (!info || !info->buf) {
        return;
    }

    // Toggle link LED on packet reception
    static bool link_state = false;
    link_state = !link_state;
    gpio_set_level(PIN_LED_LINK, link_state ? 1 : 0);

    // CSI subcarrier data format: interleaved signed 8-bit [Imaginary, Real]
    int8_t *csi_bytes = (int8_t *)info->buf;
    int subcarriers = info->len / 2;
    if (subcarriers > CSI_MAX_SUBCARRIERS) {
        subcarriers = CSI_MAX_SUBCARRIERS;
    }

    // Compute mean amplitude across valid data subcarriers (skip DC / pilots if desired)
    float sum_amplitude = 0.0f;
    int valid_subcarriers = 0;

    for (int i = 0; i < subcarriers; i++) {
        int8_t imag = csi_bytes[2 * i];
        int8_t real = csi_bytes[2 * i + 1];
        float amp = sqrtf((float)(real * real + imag * imag));
        sum_amplitude += amp;
        valid_subcarriers++;
    }

    if (valid_subcarriers == 0) return;
    float current_avg_amp = sum_amplitude / (float)valid_subcarriers;

    // Push into circular sliding window buffer
    g_window[g_window_index] = current_avg_amp;
    g_window_index = (g_window_index + 1) % WINDOW_SIZE;
    if (g_sample_count < WINDOW_SIZE) {
        g_sample_count++;
        return; // Fill buffer before computing variance
    }

    // 1. Calculate Sliding Window Mean
    float mean = 0.0f;
    for (int i = 0; i < WINDOW_SIZE; i++) {
        mean += g_window[i];
    }
    mean /= (float)WINDOW_SIZE;

    // 2. Calculate Sliding Window Variance: V(t) = (1/N) * sum((A_i - mean)^2)
    float variance = 0.0f;
    for (int i = 0; i < WINDOW_SIZE; i++) {
        float diff = g_window[i] - mean;
        variance += diff * diff;
    }
    variance /= (float)WINDOW_SIZE;

    // 3. Apply Exponential Moving Average: S(t) = alpha * V(t) + (1 - alpha) * S(t-1)
    g_ema_variance = (EMA_ALPHA * variance) + ((1.0f - EMA_ALPHA) * g_ema_variance);

    // 4. Hysteresis Dual-Threshold State Machine
    uint32_t now = xTaskGetTickCount() * portTICK_PERIOD_MS;
    if (!g_movement_detected) {
        if (g_ema_variance >= VARIANCE_THRESHOLD_HIGH) {
            g_movement_detected = true;
            g_last_trigger_time = now;
        }
    } else {
        if (g_ema_variance >= VARIANCE_THRESHOLD_HIGH) {
            g_last_trigger_time = now; // Refresh holdoff timer on active movement
        } else if (g_ema_variance < VARIANCE_THRESHOLD_LOW && (now - g_last_trigger_time) > ALARM_HOLDOFF_MS) {
            g_movement_detected = false;
        }
    }

    // 5. Hardware Actuation
    gpio_set_level(PIN_RELAY, g_movement_detected ? 1 : 0);
    gpio_set_level(PIN_BUZZER, g_movement_detected ? 1 : 0);
    gpio_set_level(PIN_LED_ALERT, g_movement_detected ? 1 : 0);

    // 6. Real-time Telemetry Frame over Serial:
    // Format: $CSI,timestamp_ms,rssi,raw_var,ema_var,state
    printf("$CSI,%lu,%d,%.2f,%.2f,%d\n",
           now,
           info->rx_ctrl.rssi,
           variance,
           g_ema_variance,
           g_movement_detected ? 1 : 0);
}

void app_main(void) {
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);

    init_peripherals();
    ESP_LOGI(TAG, "Hardware Peripherals Initialized.");

    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));
    ESP_ERROR_CHECK(esp_wifi_set_storage(WIFI_STORAGE_RAM));
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_NULL));
    ESP_ERROR_CHECK(esp_wifi_start());

    // Promiscuous mode to capture raw frames on selected channel
    ESP_ERROR_CHECK(esp_wifi_set_promiscuous(true));
    ESP_ERROR_CHECK(esp_wifi_set_channel(WIFI_CHANNEL, WIFI_SECOND_CHAN_NONE));

    // Enable Channel State Information (CSI)
    wifi_csi_config_t csi_config = {
        .lltf_en = true,
        .htltf_en = true,
        .stbc_htltf2_en = true,
        .ltf_merge_en = true,
        .channel_filter_en = false,
        .manu_scale = false,
    };
    ESP_ERROR_CHECK(esp_wifi_set_csi_config(&csi_config));
    ESP_ERROR_CHECK(esp_wifi_set_csi_rx_cb(csi_rx_callback, NULL));
    ESP_ERROR_CHECK(esp_wifi_set_csi(true));

    ESP_LOGI(TAG, "Wi-Fi CSI Active on Channel %d. Monitoring...", WIFI_CHANNEL);

    while (1) {
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}
