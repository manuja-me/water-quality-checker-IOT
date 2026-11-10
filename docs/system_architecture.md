# System Architecture & Technical Specifications

AquaCheck is structured into four tightly coupled layers:
1. **Sensory Transduction Layer** (Multi-probe physical acquisition)
2. **Signal Conditioning & Hardware Isolation Layer** (Noise mitigation & power gating)
3. **Embedded Dual-Core Processing Layer** (ESP32 FreeRTOS tasks & physical calibration math)
4. **HCI, Storage & Diagnostic Output Layer** (OLED, MicroSD, Alert actuation & Serial/Web telemetry)

```
[ Water Sample Container ]
      │
      ├──────────────────────┬──────────────────────┬──────────────────────┐
      ▼                      ▼                      ▼                      ▼
  [pH Glass Probe]    [Optical Turbidity]     [TDS AC Probe]         [DS18B20 Temp]
      │                      │                      │                      │
 [Analog Signal Amp]   [Phototransistor]     [2N7000 MOSFET Gate]    [1-Wire Pull-up]
      │ (0.0 - 3.3V)         │ (0.5 - 4.0V)         │ (Power Gated)        │ (Digital Data)
      ▼                      ▼                      ▼                      ▼
   GPIO 32                GPIO 33                GPIO 34                 GPIO 4
      └──────────────────────┴──────────┬───────────┴──────────────────────┘
                                        ▼
                         [ ESP32 Dual-Core SoC (240MHz) ]
                        ┌───────────────────────────────┐
                        │ Core 0: High-Priority FreeRTOS│
                        │ - Time-Multiplexed Sampling   │
                        │ - Nernstian pH Correction     │
                        │ - 25°C Normalized EC/TDS Math │
                        │ - SLS 614 Classification Logic│
                        └───────────────┬───────────────┘
                                        │ Inter-task Queue
                        ┌───────────────▼───────────────┐
                        │ Core 1: HCI & Telemetry Task  │
                        │ - 0.96" SSD1306 OLED (I2C)    │
                        │ - MicroSD Card Logger (SPI)   │
                        │ - Piezo & Bi-Color LED Alerts │
                        │ - USB-UART / Web Stream       │
                        └───────────────────────────────┘
```

---

## 1. Physical Calibration Models & Mathematical Formulations

### A. Electrical Conductivity (EC) and Total Dissolved Solids (TDS)
Dissolved mineral ions exhibit increased thermal mobility of approximately 1.9% per °C. To provide consistent readings independent of ambient liquid temperature, measured conductivity ($EC_T$) is normalized to a standard 25.0°C baseline:

$$EC_{25} = \frac{EC_{\text{measured}}}{1.0 + 0.019 \times (T_{\text{water}} - 25.0)}$$

TDS (in parts-per-million, ppm) is derived using the standard 0.50 conversion ratio:

$$\text{TDS (ppm)} = EC_{25} (\mu\text{S/cm}) \times 0.50$$

### B. pH Temperature Slope Scaling (Nernst Equation)
The potential difference developed across the glass electrode membrane is governed by the Nernst relationship:

$$E = E_0 - S(T) \cdot (\text{pH} - 7.0)$$

where the temperature-dependent slope $S(T)$ (in mV per pH unit) is:

$$S(T) = \frac{2.3026 \cdot R \cdot T_{\text{Kelvin}}}{F}$$

- At $0^\circ\text{C}$ ($273.15\text{ K}$): $S = 54.20\text{ mV/pH}$
- At $25^\circ\text{C}$ ($298.15\text{ K}$): $S = 59.16\text{ mV/pH}$
- At $40^\circ\text{C}$ ($313.15\text{ K}$): $S = 62.13\text{ mV/pH}$

The temperature-corrected pH is computed in firmware via 2-point buffer calibration:

$$\text{pH}_{\text{corrected}} = 7.0 + \left[ \frac{V_{\text{neutral}} - V_{\text{probe}}}{S(T)} \right]$$

### C. Optical Turbidity Non-Linear Characteristic
The optical sensor measures infrared light attenuation through suspended matter. The relationship between output collector voltage ($V_{\text{out}}$) and nephelometric turbidity units (NTU) is modeled as a 2nd-order polynomial:

$$\text{Turbidity (NTU)} = -1120.4 \cdot (V_{\text{out}})^2 + 5742.3 \cdot V_{\text{out}} - 4352.9$$

For $V_{\text{out}} \ge 2.50\text{V}$, the sample is clear ($\le 0.5\text{ NTU}$).

---

## 2. Multi-Probe Electrical Isolation & Time-Multiplexing

A frequent pitfall in multi-sensor water testing is **galvanic cross-talk**:
- The TDS meter injects an alternating AC excitation voltage into the water.
- The high-impedance glass bulb pH probe (impedance $> 10^8\ \Omega$) picks up this AC excitation as massive millivolt noise, causing wild pH oscillations of $\pm 2.5\text{ pH}$.

**AquaCheck Hardware Solution:**
The TDS excitation circuitry is isolated through an N-channel MOSFET (2N7000) controlled by ESP32 `GPIO 14`.
1. TDS excitation power is held `LOW` (disconnected) while the pH probe is sampled and averaged (over 50 ADC samples).
2. TDS excitation power is switched `HIGH` for 50 ms to stabilize, sampled, and immediately switched back `LOW`.
3. This eliminates electrical coupling completely without requiring costly isolated DC-DC converters.
