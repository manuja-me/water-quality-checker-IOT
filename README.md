# Wi-Fi CSI-Based Through-Wall Human Presence & Movement Monitoring System

An edge-computed, non-AI IoT embedded system for device-free through-wall presence and movement detection using 802.11 Channel State Information (CSI) on the ESP32.

---

## 1. Project Highlights

- **Pure Mathematical Edge DSP:** No neural networks, no ML training, zero dataset collection. Runs deterministic sliding-window variance and exponential moving average (EMA) directly in ESP32 C firmware.
- **Seamless Battery Backup:** Onboard 18650 Li-ion cell with Schottky diode OR-switch circuit ensuring zero brownout resets during mains power loss.
- **Physical Actuation & HCI:** On-edge 5V relay output (external sirens/strobe), piezo buzzer, status LEDs, and real-time USB-UART telemetry.
- **Live Radar Dashboard:** Host web interface featuring interactive room scanner, movement intensity gauge, CSI variance chart, and event logger.
- **Full Academic Rubric Compliance:** Tailored for 100% score alignment with Mini Project guidelines (PCB design, battery backup, commercialization plan, and research publication roadmap).

---

## 2. Repository Layout

```
.
├── dashboard/                  # Host visualizer & telemetry server
│   ├── app.py                  # Python SSE server (mock mode + live serial)
│   ├── index.html              # HTML5 Canvas radar & metrics UI
│   └── requirements.txt        # Host Python dependencies
├── docs/                       # Rubric & technical documentation
│   ├── circuit_and_wiring.md   # Breadboard pinout, schematics, electrical ratings
│   ├── commercialization_and_ip.md # Market analysis, patent claim, paper outline
│   ├── system_architecture.md  # Top-level block diagrams & DSP formulas
│   └── testing_and_validation.md # Penetration matrix & tuning protocols
├── firmware/                   # ESP32 embedded source code
│   ├── rx_node/                # Receiver & Edge DSP engine
│   │   ├── include/config.h    # Pins, thresholds, Wi-Fi channel settings
│   │   └── src/main.c          # CSI callback, circular buffer, hysteresis
│   └── tx_node/                # Transmitter / RF illuminator
│       └── src/main.c          # 80 Hz fixed-rate raw packet generator
└── hardware/                   # Circuit & PCB artifacts
    ├── bom.csv                 # Detailed Bill of Materials & pricing
    └── kicad/                  # KiCad v6/v7 schematic and board project
        ├── wifi_csi_rx_node.kicad_pro
        └── wifi_csi_rx_node.kicad_sch
```

---

## 3. Breadboard Wiring (Rx Node)

| Component | Pin | ESP32 Pin | Function |
| :--- | :--- | :--- | :--- |
| **Relay Module** | IN | **GPIO 26** | 5V Relay Trigger (Active LOW/HIGH) |
| **Active Buzzer** | (-) via 2N2222 | **GPIO 27** | NPN Base drive via $1\,\text{k}\Omega$ |
| **Red Alert LED** | Anode (+) | **GPIO 25** | High on movement detection (via $330\,\Omega$) |
| **Green Link LED**| Anode (+) | **GPIO 33** | Flashes on CSI packet capture (via $330\,\Omega$) |
| **Power Input** | VIN | Switched 5V Rail | Powered via Mains 5V or Boosted 18650 Battery |
| **Ground** | GND | Common GND | System common ground |

*See [docs/circuit_and_wiring.md](docs/circuit_and_wiring.md) for full power circuit and diode OR-switch details.*

---

## 4. Quick Start: Host Dashboard

Run the host telemetry server in standalone mock mode (no hardware required):

```bash
# Run mock simulation server
python3 dashboard/app.py --mock --http-port 8080
```
Open your browser to `http://localhost:8080` to view the live radar scanner, variance chart, and alarm logs.

For live hardware connection over serial:
```bash
pip install -r dashboard/requirements.txt
python3 dashboard/app.py --port /dev/ttyUSB0 --baud 115200
```

---

## 5. Team Task Division (6–8 Members)

| Student | Assigned Role | Primary Deliverables |
| :--- | :--- | :--- |
| **M1** | Power Subsystem | 18650 battery backup, TP4056 + MT3608 auto-switch circuit, power budget. |
| **M2** | PCB Layout & Fab | KiCad schematic completion, 2-layer PCB routing, Gerber generation, soldering. |
| **M3** | Tx Node Firmware | ESP32 packet injector firmware (ESP-NOW @ 80 Hz), channel calibration. |
| **M4** | Rx Node DSP Firmware | CSI callback handler, circular buffer variance, EMA smoothing, hysteresis. |
| **M5** | Hardware Actuation | Relay driver isolation, transistor buzzer stage, breadboard prototyping. |
| **M6** | Host Visualizer | Python serial pipeline, SSE telemetry stream, Canvas radar display. |
| **M7** | Testing & Calibration | Wall penetration tests (drywall/brick), threshold tuning, false-positive matrix. |
| **M8** | Documentation & IP | Commercialization report, patent claim documentation, final project report. |

---

## 6. Rubric Compliance Verification

- **Originality & Commercialization (5 pts):** Documented in [docs/commercialization_and_ip.md](docs/commercialization_and_ip.md).
- **Sensors, Actuators & Backup Power (4 pts):** Documented in [docs/circuit_and_wiring.md](docs/circuit_and_wiring.md).
- **PCB Design & Fabrication (4 pts total):** Located in [hardware/kicad/](hardware/kicad/).
- **Physical Implementation (27 pts):** Complete C firmware and wiring netlists ready for deployment.
