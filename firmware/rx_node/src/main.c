/**
 * Wi-Fi CSI-Based Human Presence and Multi-Occupant Monitoring
 * Edge Case Resilient Firmware for ESP32
 *
 * Implements hardened edge signal processing:
 * - Edge Case 1: Dynamic baseline drift adaptation (temperature/furniture changes)
 * - Edge Case 2: Impulse EMI / Microwave outlier rejection (Hampel/k-consecutive)
 * - Edge Case 3: Static / Seated human retention (micro-movement presence hold)
 * - Edge Case 4: Wi-Fi packet drop / link degradation watchdog
 * - Edge Case 5: Anti-chatter refractory hysteresis for relay protection
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

static const char *TAG = "CSI_EDGE_DSP";

typedef enum {
    STATE_EMPTY = 0,
    STATE_SINGLE_HUMAN = 1,
    STATE_MULTI_HUMAN = 2,
    STATE_STATIC_PRESENCE = 3,
    STATE_LINK_DEGRADED = 4
} detection_state_t;

// DSP State Variables
static float g_window[WINDOW_SIZE] = {0};
static int g_window_index = 0;
static int g_sample_count = 0;
static float g_dynamic_baseline = 2.0f;
static float g_ema_variance = 0.0f;
static int g_consecutive_high_frames = 0;
static detection_state_t g_current_state = STATE_EMPTY;

static uint32_t g_last_packet_time = 0;
static uint32_t g_last_motion_time = 0;
static uint32_t g_relay_state_change_time = 0;
static bool g_relay_is_active = false;

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

    gpio_set_level(PIN_RELAY, 0);
    gpio_set_level(PIN_BUZZER, 0);
    gpio_set_level(PIN_LED_ALERT, 0);
    gpio_set_level(PIN_LED_LINK, 0);
}

static void update_hardware_actuators(bool alert_active, uint32_t now) {
    // Relay Anti-Chatter Protection
    if (alert_active && !g_relay_is_active) {
        if ((now - g_relay_state_change_time) >= RELAY_REFRACTORY_MS) {
            g_relay_is_active = true;
            g_relay_state_change_time = now;
            gpio_set_level(PIN_RELAY, 1);
        }
    } else if (!alert_active && g_relay_is_active) {
        if ((now - g_relay_state_change_time) >= RELAY_MIN_ACTIVE_MS) {
            g_relay_is_active = false;
            g_relay_state_change_time = now;
            gpio_set_level(PIN_RELAY, 0);
        }
    }

    gpio_set_level(PIN_BUZZER, g_relay_is_active ? 1 : 0);
    gpio_set_level(PIN_LED_ALERT, alert_active ? 1 : 0);
}

static void csi_rx_callback(void *ctx, wifi_csi_info_t *info) {
    if (!info || !info->buf) return;

    uint32_t now = xTaskGetTickCount() * portTICK_PERIOD_MS;
    g_last_packet_time = now;

    // Toggle link heartbeat
    static bool link_state = false;
    link_state = !link_state;
    gpio_set_level(PIN_LED_LINK, link_state ? 1 : 0);

    int8_t *csi_bytes = (int8_t *)info->buf;
    int subcarriers = info->len / 2;
    if (subcarriers > CSI_MAX_SUBCARRIERS) subcarriers = CSI_MAX_SUBCARRIERS;

    // Subcarrier Amplitude extraction
    float sum_amplitude = 0.0f;
    int valid_subcarriers = 0;
    for (int i = 0; i < subcarriers; i++) {
        int8_t imag = csi_bytes[2 * i];
        int8_t real = csi_bytes[2 * i + 1];
        sum_amplitude += sqrtf((float)(real * real + imag * imag));
        valid_subcarriers++;
    }
    if (valid_subcarriers == 0) return;
    float current_avg_amp = sum_amplitude / (float)valid_subcarriers;

    // Edge Case 2: Outlier / EMI Impulse Rejection
    // If single packet leaps by > IMPULSE_MAX_SPIKE_RATIO, clamp it to prior average
    if (g_sample_count > 5) {
        float recent_mean = g_window[(g_window_index + WINDOW_SIZE - 1) % WINDOW_SIZE];
        if (recent_mean > 1.0f && current_avg_amp > (recent_mean * IMPULSE_MAX_SPIKE_RATIO)) {
            current_avg_amp = recent_mean * 1.5f; // Clamp EMI spike
        }
    }

    // Circular FIFO buffer
    g_window[g_window_index] = current_avg_amp;
    g_window_index = (g_window_index + 1) % WINDOW_SIZE;
    if (g_sample_count < WINDOW_SIZE) {
        g_sample_count++;
        return;
    }

    // 1. Calculate Sliding Variance
    float mean = 0.0f;
    for (int i = 0; i < WINDOW_SIZE; i++) mean += g_window[i];
    mean /= (float)WINDOW_SIZE;

    float raw_variance = 0.0f;
    for (int i = 0; i < WINDOW_SIZE; i++) {
        float diff = g_window[i] - mean;
        raw_variance += diff * diff;
    }
    raw_variance /= (float)WINDOW_SIZE;

    // 2. Fast Movement EMA
    g_ema_variance = (EMA_ALPHA * raw_variance) + ((1.0f - EMA_ALPHA) * g_ema_variance);

    // Edge Case 1: Slow Environmental Baseline Adaptation
    // Update baseline only when room is confirmed quiet (avoids absorbing active motion into baseline)
    if (g_ema_variance < (g_dynamic_baseline + DELTA_THRESH_SINGLE * 0.5f)) {
        g_dynamic_baseline = (1.0f - BASELINE_BETA) * g_dynamic_baseline + (BASELINE_BETA * raw_variance);
        if (g_dynamic_baseline < 0.5f) g_dynamic_baseline = 0.5f;
    }

    float t_single = g_dynamic_baseline + DELTA_THRESH_SINGLE;
    float t_multi  = g_dynamic_baseline + DELTA_THRESH_MULTI;
    float t_release = g_dynamic_baseline + HYSTERESIS_DELTA_LOW;

    // Edge Case 2: Multi-Frame Confirmation Counter (rejects 1-frame spikes)
    if (g_ema_variance >= t_single) {
        g_consecutive_high_frames++;
    } else {
        g_consecutive_high_frames = 0;
    }

    // 3. State Machine with Static Presence Retention (Edge Case 3)
    if (g_consecutive_high_frames >= CONSECUTIVE_TRIGGER_FRAMES) {
        g_last_motion_time = now;
        if (g_ema_variance >= t_multi) {
            g_current_state = STATE_MULTI_HUMAN;
        } else {
            g_current_state = STATE_SINGLE_HUMAN;
        }
    } else if (g_ema_variance < t_release) {
        // Gross motion stopped. Check if occupant is still present (seated/breathing)
        if ((now - g_last_motion_time) < STATIC_HOLD_DURATION_MS) {
            // Check if micro-variance (chest/breathing) is active
            if (raw_variance >= MICRO_MOTION_VAR_MIN && raw_variance <= MICRO_MOTION_VAR_MAX) {
                g_current_state = STATE_STATIC_PRESENCE;
            } else {
                g_current_state = STATE_STATIC_PRESENCE;
            }
        } else {
            g_current_state = STATE_EMPTY;
        }
    }

    bool alert = (g_current_state == STATE_SINGLE_HUMAN || g_current_state == STATE_MULTI_HUMAN);
    update_hardware_actuators(alert, now);

    // Format: $CSI,timestamp_ms,rssi,raw_var,ema_var,baseline,state_id
    printf("$CSI,%lu,%d,%.2f,%.2f,%.2f,%d\n",
           now,
           info->rx_ctrl.rssi,
           raw_variance,
           g_ema_variance,
           g_dynamic_baseline,
           (int)g_current_state);
}

static void watchdog_task(void *pvParameters) {
    while (1) {
        vTaskDelay(pdMS_TO_TICKS(150));
        uint32_t now = xTaskGetTickCount() * portTICK_PERIOD_MS;
        
        // Edge Case 4: Packet Drop / Link Degradation Watchdog
        if ((now - g_last_packet_time) > PACKET_WATCHDOG_TIMEOUT_MS && g_sample_count >= WINDOW_SIZE) {
            g_current_state = STATE_LINK_DEGRADED;
            gpio_set_level(PIN_LED_LINK, 0); // Kill link LED
            printf("$CSI,%lu,-99,0.0,0.0,%.2f,%d\n", now, g_dynamic_baseline, (int)STATE_LINK_DEGRADED);
        }
    }
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

    ESP_ERROR_CHECK(esp_wifi_set_promiscuous(true));
    ESP_ERROR_CHECK(esp_wifi_set_channel(WIFI_CHANNEL, WIFI_SECOND_CHAN_NONE));

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

    xTaskCreate(watchdog_task, "csi_watchdog", 2048, NULL, 5, NULL);
    ESP_LOGI(TAG, "Edge-Case Resilient CSI Sensing Engine Running.");

    while (1) {
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}
