# Circuit, Schematics & Hardware Wiring Guide

This document specifies the complete pin mapping, power subsystem architecture, and wiring connections for assembling AquaCheck on a prototyping perfboard or custom 2-layer PCB.

---

## 1. Full ESP32 Pin Allocation Table

| Component | Pin Function | ESP32 Pin | Interface Type | Operating Voltage |
|---|---|---|---|---|
| **Analog pH Sensor V1.1** | Signal Out (`A0`) | `GPIO 32` | ADC1_CH4 Analog In | 5.0V VCC / 3.3V Logic |
| **TS-300B Turbidity Sensor**| Signal Out (`A0`) | `GPIO 33` | ADC1_CH5 Analog In | 5.0V VCC |
| **Gravity TDS Sensor** | Signal Out (`A0`) | `GPIO 34` | ADC1_CH6 Analog In | 3.3V - 5.0V |
| **TDS Power Gate MOSFET** | Gate (`2N7000`) | `GPIO 14` | Digital Output | 3.3V Logic (10k pulldown)|
| **DS18B20 Temp Probe** | Data Wire (Yellow) | `GPIO 4` | 1-Wire Digital Bus | 3.3V (4.7kΩ pull-up) |
| **SSD1306 0.96" OLED** | `SDA` | `GPIO 21` | I2C Data Bus | 3.3V VCC |
| **SSD1306 0.96" OLED** | `SCL` | `GPIO 22` | I2C Clock Bus | 3.3V VCC |
| **MicroSD SPI Breakout** | `SCK` | `GPIO 18` | SPI Clock | 3.3V VCC |
| **MicroSD SPI Breakout** | `MISO` | `GPIO 19` | SPI Master In | 3.3V VCC |
| **MicroSD SPI Breakout** | `MOSI` | `GPIO 23` | SPI Master Out | 3.3V VCC |
| **MicroSD SPI Breakout** | `CS` | `GPIO 5` | SPI Chip Select | 3.3V VCC |
| **Active Piezo Buzzer** | Anode (+) | `GPIO 25` | Digital Out (Active High)| 3.3V Logic |
| **Status LED Green (Safe)**| Anode (+) | `GPIO 26` | Digital Out (220Ω series)| 3.3V Logic |
| **Status LED Red (Alert)** | Anode (+) | `GPIO 27` | Digital Out (220Ω series)| 3.3V Logic |

---

## 2. Power Subsystem Architecture

To guarantee 8+ hours of untethered field operation without voltage sag or brownout resets:

```
[ 5V USB-C Charger / Power Bank ]
             │
             ▼
   [ TP4056 Charger & Protection Board ]
             ▲
             │ (Bi-directional Charge/Discharge)
             ▼
   [ 18650 Li-ion Cell (3.7V, 2600mAh) ]
             │
             ▼
    [ SPST Mini Rocker Switch ]
             │
             ▼
   [ MT3608 DC-DC Step-Up Boost Converter ] ────► Regulated 5.0V System Rail
                                                       │
                                 ┌─────────────────────┴─────────────────────┐
                                 ▼                                           ▼
                     [ ESP32 VIN (Onboard LDO) ]                 [ 5V Sensors: Turbidity, pH ]
                                 │
                                 ▼
                     Regulated 3.3V Bus ──► [ OLED, DS18B20, MicroSD, TDS ]
```

### Power Ratings & Current Consumption:
- Total nominal system current draw at 5V: **~150 mA**
- Estimated battery draw from 3.7V Li-ion (at 85% boost efficiency): **~240 mA**
- Runtime with a 2600mAh 18650 cell: **~10.8 Hours continuous operation**.

---

## 3. Critical Wiring Guidelines

1. **ADC Reference Stability:**
   - ESP32 ADC channels are susceptible to high-frequency noise from WiFi operations. AquaCheck uses only `ADC1` pins (`GPIO 32`, `33`, `34`). A `0.1 µF` ceramic capacitor is placed across each analog input to ground to decouple switching noise.
2. **DS18B20 Pull-up Resistor:**
   - A `4.7 kΩ` resistor must be soldered between the `DATA` pin (`GPIO 4`) and `3.3V VCC`. Omitting this resistor causes the 1-Wire bus to return `-127.0°C` errors.
3. **Common Ground Plane:**
   - The ground lines of the 18650 battery, TP4056 board, MT3608 boost converter, ESP32, and all sensor boards must terminate at a single star ground point to prevent ground loop noise from shifting the sensitive millivolt pH reading.
