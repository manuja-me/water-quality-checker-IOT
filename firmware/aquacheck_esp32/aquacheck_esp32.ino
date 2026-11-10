/*
 * ======================================================================================
 * AquaCheck – Portable Multi-Parameter Water Quality Monitoring & Assessment Device
 * Target: ESP32 Dev Module (Dual-Core Xtensa 240MHz)
 * 
 * Features:
 * - Synchronous 4-probe acquisition: pH, Turbidity, TDS/EC, Water Temperature (DS18B20)
 * - Time-Multiplexed Power Gating to prevent TDS AC interference on high-impedance pH probe
 * - Real-time physical temperature compensation (Nernstian pH & 25°C normalized TDS)
 * - FreeRTOS dual-core tasking: Core 0 (DSP & Sampling), Core 1 (OLED, MicroSD, Alerts)
 * - SLS 614:2013 and WHO Drinking Water Benchmark Classification
 * ======================================================================================
 */

#include <Arduino.h>
#include <Wire.h>
#include <SPI.h>
#include <SD.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <OneWire.h>
#include <DallasTemperature.h>

// --------------------------------------------------------------------------------------
// Pin Definitions
// --------------------------------------------------------------------------------------
#define PIN_PH_ANALOG       32    // ADC1_CH4
#define PIN_TURBIDITY       33    // ADC1_CH5
#define PIN_TDS_ANALOG      34    // ADC1_CH6
#define PIN_DS18B20         4     // 1-Wire Digital Bus (with 4.7k pullup)
#define PIN_TDS_GATE        14    // 2N7000 MOSFET Gate for TDS power gating
#define PIN_BUZZER          25    // Active Piezo Buzzer
#define PIN_LED_GREEN       26    // Status Safe Indicator
#define PIN_LED_RED         27    // Status Danger/Warning Indicator

// SPI Pins for MicroSD Card
#define PIN_SD_CS           5
#define PIN_SD_MOSI         23
#define PIN_SD_MISO         19
#define PIN_SD_SCK          18

// OLED Display Configuration
#define SCREEN_WIDTH        128
#define SCREEN_HEIGHT       64
#define OLED_RESET          -1
#define SCREEN_ADDRESS      0x3C

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);
OneWire oneWire(PIN_DS18B20);
DallasTemperature tempSensor(&oneWire);

// --------------------------------------------------------------------------------------
// Calibration Constants
// --------------------------------------------------------------------------------------
const float VREF               = 3.30f;
const float ADC_RESOLUTION     = 4095.0f;
const float PH_NEUTRAL_VOLTAGE = 2.50f;   // Measured voltage at pH 7.00
const float PH_SLOPE_25C       = 0.180f;  // Volts per pH unit at 25°C (approx 59.16mV * amplifier gain)
const float TDS_FACTOR         = 0.50f;   // ppm per uS/cm conversion

// --------------------------------------------------------------------------------------
// Data Structures & FreeRTOS Synchronization
// --------------------------------------------------------------------------------------
enum WaterStatus {
  STATUS_SAFE,
  STATUS_PERMISSIBLE,
  STATUS_UNSAFE_TURBIDITY,
  STATUS_UNSAFE_PH,
  STATUS_HAZARDOUS_TDS
};

struct WaterQualityData {
  float temperatureC;
  float pH;
  float turbidityNTU;
  float tdsPPM;
  WaterStatus status;
  uint32_t timestampMs;
};

// Queue to transfer measurements from Core 0 to Core 1
QueueHandle_t dataQueue;
bool sdCardAvailable = false;

// --------------------------------------------------------------------------------------
// Function Prototypes
// --------------------------------------------------------------------------------------
float readFilteredVoltage(uint8_t pin, int samples = 40);
float computeCompensatedPH(float rawVoltage, float tempC);
float computeTurbidityNTU(float rawVoltage);
float computeCompensatedTDS(float rawVoltage, float tempC);
WaterStatus evaluateWaterSafety(float ph, float tds, float ntu);
void TaskSensorAcquisition(void *pvParameters);
void TaskHCIAndLogging(void *pvParameters);

// --------------------------------------------------------------------------------------
// Arduino Setup
// --------------------------------------------------------------------------------------
void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("\n[AquaCheck] Initializing Embedded Diagnostics System...");

  // Initialize GPIOs
  pinMode(PIN_PH_ANALOG, INPUT);
  pinMode(PIN_TURBIDITY, INPUT);
  pinMode(PIN_TDS_ANALOG, INPUT);
  pinMode(PIN_TDS_GATE, OUTPUT);
  digitalWrite(PIN_TDS_GATE, LOW); // Keep TDS powered off initially

  pinMode(PIN_BUZZER, OUTPUT);
  pinMode(PIN_LED_GREEN, OUTPUT);
  pinMode(PIN_LED_RED, OUTPUT);
  digitalWrite(PIN_BUZZER, LOW);
  digitalWrite(PIN_LED_GREEN, LOW);
  digitalWrite(PIN_LED_RED, LOW);

  // Initialize Temperature Sensor
  tempSensor.begin();

  // Initialize I2C OLED
  Wire.begin(21, 22);
  if (!display.begin(SSD1306_SWITCHCAPVCC, SCREEN_ADDRESS)) {
    Serial.println("[AquaCheck ERROR] SSD1306 allocation failed!");
  } else {
    display.clearDisplay();
    display.setTextSize(1);
    display.setTextColor(SSD1306_WHITE);
    display.setCursor(15, 20);
    display.println("AQUACHECK v1.0");
    display.setCursor(10, 35);
    display.println("Booting System...");
    display.display();
  }

  // Initialize MicroSD Card
  SPI.begin(PIN_SD_SCK, PIN_SD_MISO, PIN_SD_MOSI, PIN_SD_CS);
  if (SD.begin(PIN_SD_CS)) {
    sdCardAvailable = true;
    Serial.println("[AquaCheck] MicroSD Card mounted successfully.");
    // Write CSV header if file doesn't exist
    if (!SD.exists("/aquacheck_log.csv")) {
      File logFile = SD.open("/aquacheck_log.csv", FILE_WRITE);
      if (logFile) {
        logFile.println("Timestamp_ms,Temp_C,pH,Turbidity_NTU,TDS_ppm,Safety_Verdict");
        logFile.close();
      }
    }
  } else {
    Serial.println("[AquaCheck WARN] MicroSD Card failed to mount! Running in local-only mode.");
  }

  // Create Inter-task FreeRTOS Queue (capacity: 5 items)
  dataQueue = xQueueCreate(5, sizeof(WaterQualityData));

  // Spawn Core 0 Task: High-priority Sensor Acquisition
  xTaskCreatePinnedToCore(
    TaskSensorAcquisition,
    "SensorTask",
    4096,
    NULL,
    2,        // Priority 2 (Higher)
    NULL,
    0         // Core 0
  );

  // Spawn Core 1 Task: UI Rendering, MicroSD Logging, and Alerts
  xTaskCreatePinnedToCore(
    TaskHCIAndLogging,
    "HCITask",
    4096,
    NULL,
    1,        // Priority 1
    NULL,
    1         // Core 1
  );

  Serial.println("[AquaCheck] FreeRTOS Tasks running on Cores 0 and 1.");
}

void loop() {
  // Empty. Execution is governed by FreeRTOS tasks.
  vTaskDelay(pdMS_TO_TICKS(1000));
}

// --------------------------------------------------------------------------------------
// Core 0: High-Priority Sensor Acquisition Task
// --------------------------------------------------------------------------------------
void TaskSensorAcquisition(void *pvParameters) {
  for (;;) {
    WaterQualityData data;
    data.timestampMs = millis();

    // 1. Measure Liquid Temperature
    tempSensor.requestTemperatures();
    float temp = tempSensor.getTempCByIndex(0);
    if (temp < -50.0f || temp > 100.0f) {
      temp = 25.0f; // Fallback default if probe disconnected
    }
    data.temperatureC = temp;

    // 2. Measure pH (Ensure TDS excitation is OFF to prevent galvanic interference)
    digitalWrite(PIN_TDS_GATE, LOW);
    vTaskDelay(pdMS_TO_TICKS(30)); // Allow charge stabilization
    float phVoltage = readFilteredVoltage(PIN_PH_ANALOG, 50);
    data.pH = computeCompensatedPH(phVoltage, data.temperatureC);

    // 3. Measure Optical Turbidity
    float turbidityVoltage = readFilteredVoltage(PIN_TURBIDITY, 40);
    data.turbidityNTU = computeTurbidityNTU(turbidityVoltage);

    // 4. Measure TDS (Power gate TDS ON, stabilize, sample, then power gate OFF)
    digitalWrite(PIN_TDS_GATE, HIGH);
    vTaskDelay(pdMS_TO_TICKS(50)); // Stabilize AC excitation waveform
    float tdsVoltage = readFilteredVoltage(PIN_TDS_ANALOG, 40);
    digitalWrite(PIN_TDS_GATE, LOW); // Immediately isolate
    data.tdsPPM = computeCompensatedTDS(tdsVoltage, data.temperatureC);

    // 5. Evaluate Overall Water Quality Verdict
    data.status = evaluateWaterSafety(data.pH, data.tdsPPM, data.turbidityNTU);

    // 6. Push to Queue for Core 1 consumption
    xQueueSend(dataQueue, &data, pdMS_TO_TICKS(100));

    // Yield for 1 second before next acquisition cycle
    vTaskDelay(pdMS_TO_TICKS(1000));
  }
}

// --------------------------------------------------------------------------------------
// Core 1: HCI, Display, Alerts & MicroSD Logging Task
// --------------------------------------------------------------------------------------
void TaskHCIAndLogging(void *pvParameters) {
  WaterQualityData data;

  for (;;) {
    if (xQueueReceive(dataQueue, &data, portMAX_DELAY) == pdTRUE) {
      
      // Update Actuator Indicators
      if (data.status == STATUS_SAFE || data.status == STATUS_PERMISSIBLE) {
        digitalWrite(PIN_LED_GREEN, HIGH);
        digitalWrite(PIN_LED_RED, LOW);
        digitalWrite(PIN_BUZZER, LOW);
      } else {
        digitalWrite(PIN_LED_GREEN, LOW);
        digitalWrite(PIN_LED_RED, HIGH);
        // Beep buzzer for alert
        digitalWrite(PIN_BUZZER, HIGH);
        vTaskDelay(pdMS_TO_TICKS(80));
        digitalWrite(PIN_BUZZER, LOW);
      }

      // Render to 128x64 OLED Display
      display.clearDisplay();
      display.setTextSize(1);
      display.setTextColor(SSD1306_WHITE);

      // Header Banner
      display.setCursor(0, 0);
      display.print("AquaCheck | ");
      display.print(data.temperatureC, 1);
      display.println(" C");
      display.drawLine(0, 9, 128, 9, SSD1306_WHITE);

      // Parameter Readings
      display.setCursor(0, 14);
      display.print("pH:   ");
      display.print(data.pH, 2);

      display.setCursor(0, 26);
      display.print("TDS:  ");
      display.print((int)data.tdsPPM);
      display.println(" ppm");

      display.setCursor(0, 38);
      display.print("Turb: ");
      display.print(data.turbidityNTU, 1);
      display.println(" NTU");

      // Status Bar
      display.drawLine(0, 49, 128, 49, SSD1306_WHITE);
      display.setCursor(0, 53);
      display.setTextSize(1);

      const char *statusStr = "SAFE (POTABLE)";
      switch (data.status) {
        case STATUS_SAFE:
          display.print("STATUS: SAFE [OK]");
          statusStr = "SAFE";
          break;
        case STATUS_PERMISSIBLE:
          display.print("STATUS: PERMISSIBLE");
          statusStr = "PERMISSIBLE";
          break;
        case STATUS_UNSAFE_TURBIDITY:
          display.print("STATUS: HIGH TURBID");
          statusStr = "UNSAFE_TURBIDITY";
          break;
        case STATUS_UNSAFE_PH:
          display.print("STATUS: ABNORMAL pH");
          statusStr = "UNSAFE_PH";
          break;
        case STATUS_HAZARDOUS_TDS:
          display.print("STATUS: HAZARD TDS");
          statusStr = "HAZARDOUS_TDS";
          break;
      }
      display.display();

      // Serial Output (JSON Telemetry for USB / Host Dashboard)
      Serial.printf("{\"temp\":%.1f,\"ph\":%.2f,\"turb\":%.1f,\"tds\":%d,\"status\":\"%s\"}\n",
                    data.temperatureC, data.pH, data.turbidityNTU, (int)data.tdsPPM, statusStr);

      // Write to MicroSD Card if available
      if (sdCardAvailable) {
        File logFile = SD.open("/aquacheck_log.csv", FILE_APPEND);
        if (logFile) {
          logFile.printf("%lu,%.2f,%.2f,%.1f,%d,%s\n",
                         data.timestampMs, data.temperatureC, data.pH, data.turbidityNTU, (int)data.tdsPPM, statusStr);
          logFile.close();
        }
      }
    }
  }
}

// --------------------------------------------------------------------------------------
// Mathematical Signal Conditioning & Calibration Helpers
// --------------------------------------------------------------------------------------

float readFilteredVoltage(uint8_t pin, int samples) {
  uint32_t rawSum = 0;
  for (int i = 0; i < samples; i++) {
    rawSum += analogRead(pin);
    delayMicroseconds(250);
  }
  float avgRaw = (float)rawSum / (float)samples;
  return (avgRaw / ADC_RESOLUTION) * VREF;
}

float computeCompensatedPH(float rawVoltage, float tempC) {
  // Thermodynamic slope calculation: S(T) = S_25 * (T_K / 298.15)
  float tempKelvin = tempC + 273.15f;
  float dynamicSlope = PH_SLOPE_25C * (tempKelvin / 298.15f);

  // Calibration formula: pH = 7.0 + (V_neutral - V_measured) / Slope
  float calculatedPH = 7.0f + ((PH_NEUTRAL_VOLTAGE - rawVoltage) / dynamicSlope);

  // Clamping to realistic chemical bounds
  if (calculatedPH < 0.0f) calculatedPH = 0.0f;
  if (calculatedPH > 14.0f) calculatedPH = 14.0f;
  return calculatedPH;
}

float computeTurbidityNTU(float rawVoltage) {
  // TS-300B transfer function: NTU = -1120.4 * V^2 + 5742.3 * V - 4352.9
  if (rawVoltage >= 2.50f) {
    return 0.2f; // Clear water threshold
  }
  float ntu = -1120.4f * (rawVoltage * rawVoltage) + 5742.3f * rawVoltage - 4352.9f;
  if (ntu < 0.0f) ntu = 0.0f;
  if (ntu > 3000.0f) ntu = 3000.0f;
  return ntu;
}

float computeCompensatedTDS(float rawVoltage, float tempC) {
  // 1. Temperature coefficient compensation to 25.0°C baseline
  float compensationCoefficient = 1.0f + 0.019f * (tempC - 25.0f);
  float compensatedVoltage = rawVoltage / compensationCoefficient;

  // 2. Convert voltage to EC (uS/cm): Empirical polynomial
  float ec = (133.42f * pow(compensatedVoltage, 3) - 255.86f * pow(compensatedVoltage, 2) + 857.39f * compensatedVoltage);
  if (ec < 0.0f) ec = 0.0f;

  // 3. Convert EC to TDS (ppm)
  float tds = ec * TDS_FACTOR;
  return tds;
}

WaterStatus evaluateWaterSafety(float ph, float tds, float ntu) {
  // SLS 614 & WHO Thresholds
  if (tds > 1000.0f) {
    return STATUS_HAZARDOUS_TDS;
  }
  if (ntu > 5.0f) {
    return STATUS_UNSAFE_TURBIDITY;
  }
  if (ph < 6.5f || ph > 8.5f) {
    return STATUS_UNSAFE_PH;
  }
  if (tds > 500.0f || ntu > 2.0f) {
    return STATUS_PERMISSIBLE;
  }
  return STATUS_SAFE;
}
