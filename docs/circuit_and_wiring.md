# Circuit Design & Breadboard Wiring Guide

## 1. System Overview & Architecture

The sensing system consists of:
1. **Tx Node (Transmitter):** Standalone ESP32 broadcasting raw 802.11 frames at 50–100 Hz.
2. **Rx Node (Receiver & Edge DSP):** ESP32 capturing CSI (Channel State Information), computing sliding variance in real time, and driving local indicators and alarms.
3. **Power Subsystem:** 5V mains input with automatic, glitch-free switchover to an onboard 18650 Li-ion battery via Schottky diode OR-gating.
4. **Actuation & HCI:** Active piezo buzzer, 1-channel 5V relay module, status LEDs, and USB-UART telemetry link.

---

## 2. Complete Breadboard Pin-to-Pin Netlist

### ESP32-WROOM-32 (30-Pin DevKit) Connections

| Component | Component Pin | ESP32 Pin | Function | Electrical Specification |
| :--- | :--- | :--- | :--- | :--- |
| **Relay Module** | VCC | 5V Rail | Relay coil supply | 5V DC, ~70 mA coil current |
| | GND | Common GND | Ground return | Common 0V |
| | IN | **GPIO 26** | Relay trigger | 3.3V logic compatible, Active LOW/HIGH |
| **Active Buzzer** | (+) | 5V Rail | Positive supply | 5V DC, ~30 mA |
| | (-) | 2N2222 Collector | Switched low-side | Controlled via NPN switch |
| **2N2222 NPN** | Base | **GPIO 27** | Base drive via $1\,\text{k}\Omega$ | $I_B \approx 2.6\,\text{mA}$ ($V_{GPIO}=3.3\text{V}, V_{BE}=0.7\text{V}$) |
| | Emitter | Common GND | Ground return | 0V |
| | Collector | Buzzer (-) | Switched ground | Clamped by 1N4148 flyback |
| **1N4148 Diode** | Cathode (bar) | 5V Rail | Flyback clamp | Suppresses inductive spike |
| | Anode | 2N2222 Collector | Flyback clamp | Across buzzer coil |
| **Red LED** (Alert) | Anode (+) | **GPIO 25** | Movement indicator | Via $330\,\Omega$ series resistor ($\sim 4\,\text{mA}$) |
| | Cathode (-) | Common GND | Ground | |
| **Green LED** (Link)| Anode (+) | **GPIO 33** | CSI packet lock | Via $330\,\Omega$ series resistor ($\sim 4\,\text{mA}$) |
| | Cathode (-) | Common GND | Ground | |
| **Blue LED** (Mains)| Anode (+) | 5V USB Input | Mains presence | Via $1\,\text{k}\Omega$ series resistor ($\sim 3\,\text{mA}$) |
| | Cathode (-) | Common GND | Ground | |
| **ESP32 DevKit** | VIN / 5V | Switched 5V Rail | Power input | Feeds onboard 3.3V AMS1117 LDO |
| | GND | Common GND | Ground | Connected to power ground plane |
| | TX0 / RX0 | USB-UART bridge | Telemetry | 115200 / 921600 baud to Linux Host |

---

## 3. Power Subsystem with Seamless Battery Backup

### Circuit Schematic

```
Mains 5V USB IN ────┬───>| 1N5819 (D1) ───┬───────> Switched 5V Rail ──> ESP32 VIN, Relay VCC
                    │                     │
                    ├───> [TP4056]        │
                    │       │ (B+/B-)     │
                    │   [18650 Cell]      │
                    │       │             │
                    │   [MT3608 Boost]    │
                    │    (Set to 4.8V)    │
                    │       │             │
                    │       └───>| 1N5819 (D2)
                    │
                    └───> [1kΩ Resistor] ───> [Blue LED] ───> GND
```

### Operation Theory
1. **Mains Powered ($V_{in} = 5.0\,\text{V}$):**
   - $V_{D1,\text{out}} = 5.0\,\text{V} - 0.3\,\text{V} = 4.7\,\text{V}$.
   - MT3608 output trimmer is adjusted to $4.8\,\text{V}$.
   - $V_{D2,\text{out}} = 4.8\,\text{V} - 0.3\,\text{V} = 4.5\,\text{V}$.
   - Since $4.7\,\text{V} > 4.5\,\text{V}$, diode D2 is reverse-biased ($\Delta V = -0.2\,\text{V}$). Zero current drawn from 18650 cell.
   - TP4056 charges 18650 cell to $4.2\,\text{V}$ using mains current.
2. **Mains Loss ($V_{in} \to 0\,\text{V}$):**
   - D1 ceases conduction immediately.
   - Rail voltage dips to $4.5\,\text{V}$, forward-biasing D2 instantaneously ($< 1\,\mu\text{s}$).
   - Onboard ESP32 AMS1117 LDO requires $\ge 4.2\,\text{V}$ to output regulated $3.3\,\text{V}$; $4.5\,\text{V}$ provides sufficient headroom.
   - Result: No brownout reset on ESP32.

---

## 4. Actuation & Signal Level Isolation

### Buzzer Low-Side Switch
ESP32 GPIO pins supply max $12\,\text{mA}$ at $3.3\,\text{V}$. An active buzzer consumes $30\,\text{mA}$ at $5\,\text{V}$. 
- 2N2222 NPN transistor operates in saturation:
  $$I_B = \frac{3.3\,\text{V} - 0.7\,\text{V}}{1000\,\Omega} = 2.6\,\text{mA}$$
  With $h_{FE,\text{sat}} \approx 10$, $I_C$ capability is up to $26\,\text{mA}$ (full saturation reached for buzzer load).
- 1N4148 clamped in parallel with the buzzer drains inductive discharge on turn-off, protecting the transistor.

### Relay Module Driver
- Connected to **GPIO 26**.
- The relay module integrates an EL817 optocoupler and protection diode. Direct connection of the `IN` pin to GPIO 26 provides galvanic isolation between ESP32 digital logic and the relay coil.
