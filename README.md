# Wi-Fi CSI-Based Through-Wall Human Presence & Movement Monitoring System

An edge-computed, non-AI IoT embedded system for device-free through-wall presence and movement detection using 802.11 Channel State Information (CSI) on the ESP32.

---

## 1. Project Highlights

- **Per-Subcarrier Differential Edge DSP:** Uses Mean Squared Subcarrier Variation ($D(t) = \frac{1}{K}\sum |A_i(t) - A_i(t-1)|^2$) directly in ESP32 firmware, eliminating frequency-selective fading cancellation for a 20x dynamic range boost over naive averaging.
- **Auto-Reconnecting Serial Telemetry:** Host server auto-detects USB-UART ports (`/dev/ttyUSB*` / `COM*`) and maintains an active reconnection loop if the hardware is replugged.
- **Focused Radar & Waveform Dashboard:** Clean HTML5 Canvas visualizer pairing a circular Spatial Radar Scope with a 12-second rolling CSI disturbance waveform and Line-of-Sight transmission beam tracking.
- **Direct Occlusion Reclassification:** Distinguishes between genuine Wi-Fi link drops and human body RF absorption (occlusion) when a person steps directly into the transmission path.
- **Physical Actuation & HCI:** On-edge 5V relay output (external sirens/strobe), piezo buzzer, status LEDs, and real-time USB-UART telemetry.
- **Seamless Battery Backup:** Onboard 18650 Li-ion cell with Schottky diode OR-switch circuit ensuring zero brownout resets during mains power loss.

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
│   ├── arduino/                # Arduino IDE sketches (Single ESP32 + Router/Hotspot)
│   │   ├── rx_node_arduino/    # Receiver & Edge DSP (ESP32 Dev Module)
│   │   └── tx_node_arduino/    # Standalone beacon injector (Optional)
│   ├── rx_node/                # ESP-IDF Receiver & Edge DSP engine
│   │   ├── include/config.h    # Pins, thresholds, Wi-Fi channel settings
│   │   └── src/main.c          # CSI callback, circular buffer, hysteresis
│   └── tx_node/                # ESP-IDF Transmitter / RF illuminator
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

## 4. Quick Start: Host Dashboard (Linux / macOS)

### Live Hardware Mode (Auto-Detects Port)
```bash
pip install -r dashboard/requirements.txt
python3 dashboard/app.py --http-port 8080
```
*(The server auto-detects `/dev/ttyUSB0`, `/dev/ttyUSB1`, or `COM*` automatically and connects at 115200 baud).*

### Standalone Mock / Simulation Mode
```bash
python3 dashboard/app.py --mock --http-port 8080
```
Open your browser to `http://localhost:8080` to view the live radar scope, disturbance waveform, and event log.

---

## 4.1. Single-Antenna (SISO) vs Multi-Node Tracking Principles

- **1 ESP32 + 1 Router/Hotspot (1x1 SISO):** A single antenna receives all multi-path reflections superimposed into a scalar metric. It provides high-precision **binary presence, velocity intensity, and Line-of-Sight occlusion**, tracking **1 human occupant** accurately.
- **Why It Cannot Count People:** Scalar amplitude variance cannot mathematically separate whether a high energy spike is caused by one person moving fast or multiple people moving slowly.
- **Scaling to Multi-Person Counting:** Requires either **Radio Tomographic Imaging (RTI)** (3–4 ESP32 nodes cross-intersecting multi-link shadows) or **Antenna Arrays (MIMO/AoA)** to resolve targets by Angle of Arrival.

---

## 5. Complete Windows 10 / 11 Setup & Testing Guide

This guide provides end-to-end instructions for team members running Windows 10 or 11 to set up the toolchain, flash the ESP32 receiver node, configure Wi-Fi/Hotspot connectivity, and run the real-time Python radar dashboard.

### Step 1: USB-UART Driver Installation & COM Port Check

Most ESP32-WROOM-32 dev boards use either a **Silicon Labs CP2102** or a **WCH CH340** USB-to-UART bridge.

1. **Install Driver (if not automatically detected):**
   - **Silicon Labs CP2102 / CP2104:** Download [CP210x Universal Windows Driver](https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers). Extract ZIP, right-click `silabser.inf` &rarr; **Install**, or run the executable installer.
   - **WCH CH340 / CH341:** Download and run [CH341SER.EXE](http://www.wch-ic.com/downloads/CH341SER_EXE.html) &rarr; click **Install**.
2. **Verify in Windows Device Manager:**
   - Plug the ESP32 into a USB port using a **micro-USB data cable** (ensure the cable has data lines; avoid power-only charging cables).
   - Press <kbd>Win</kbd> + <kbd>X</kbd> and select **Device Manager** (or press <kbd>Win</kbd> + <kbd>R</kbd>, type `devmgmt.msc`, and press <kbd>Enter</kbd>).
   - Expand **Ports (COM & LPT)**.
   - Verify your board is recognized:
     - `Silicon Labs CP210x USB to UART Bridge (COM3)`
     - or `USB-SERIAL CH340 (COM4)`
   - Note down the assigned COM port (e.g., `COM3`, `COM4`).
   - *Tip:* If multiple COM ports are listed, unplug and replug the ESP32; the port that disappears and reappears is your board.
   - *PowerShell CLI check:*
     ```powershell
     [System.IO.Ports.SerialPort]::GetPortNames()
     ```
   - *Note:* If the device appears under **Other devices** with a yellow exclamation mark (e.g., `CP2102 USB to UART Bridge Controller` or `USB2.0-Serial`), the driver was not detected; run the driver installer above.

### Step 2: Arduino IDE Setup for ESP32

1. Download and install **Arduino IDE 2.x** from [arduino.cc](https://www.arduino.cc/en/software) (Windows 10/11 64-bit installer).
2. Open Arduino IDE, open **File > Preferences** (<kbd>Ctrl</kbd> + <kbd>,</kbd>).
3. In **Additional boards manager URLs**, add:
   ```text
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
   *(If multiple URLs exist, separate them with commas).*
4. Click **OK**.
5. Open **Tools > Board > Boards Manager...** (or click the board icon on the left sidebar).
6. Search for `esp32` by **Espressif Systems** and click **Install** (version `2.0.14` or stable `3.x`).
7. Configure your target board settings under the **Tools** menu:
   - **Board:** `esp32` &rarr; `ESP32 Dev Module`
   - **Port:** Select your board's COM port (e.g., `COM3`)
   - **Upload Speed:** `115200` (or `921600` for faster flashing)
   - **CPU Frequency:** `240MHz (WiFi/BT)`
   - **Flash Frequency:** `80MHz`
   - **Partition Scheme:** `Default 4MB with spiffs (1.2MB APP/1.5MB SPIFFS)` or `Huge APP`
   - **Core Debug Level:** `None`

### Step 3: Configure & Flash Firmware

1. In Arduino IDE, open [`firmware/arduino/rx_node_arduino/rx_node_arduino.ino`](firmware/arduino/rx_node_arduino/rx_node_arduino.ino).
2. **Select Prototype Deployment Mode:**
   - **Option A — Single ESP32 + Router / Hotspot (Recommended):** The ESP32 connects to your 2.4 GHz Wi-Fi router or phone hotspot. It sends 60 Hz micro-UDP packets to the router gateway; the router replies with 802.11 ACK frames, continuously generating CSI data without requiring a second ESP32.
   - **Option B — Dual ESP32 Standalone (Tx Beacon + Rx Node):** Flash [`firmware/arduino/tx_node_arduino/tx_node_arduino.ino`](firmware/arduino/tx_node_arduino/tx_node_arduino.ino) onto a second ESP32 powered from any 5V USB charger. If the Rx node cannot connect to Wi-Fi, it automatically falls back to promiscuous sniffer mode on Channel 6 and receives CSI frames directly from the Tx beacon.
3. **Configure Wi-Fi Credentials (for Option A):**
   - In `rx_node_arduino.ino`, set your Wi-Fi credentials at lines 16–17:
     ```cpp
     const char* WIFI_SSID = "Your_WiFi_Or_Hotspot_Name";
     const char* WIFI_PASS = "Your_Password";
     ```
4. **2.4 GHz Network Band Setup (CRITICAL):**
   - ESP32 hardware operates exclusively on 2.4 GHz (802.11b/g/n) and cannot detect 5 GHz networks.
   - **iPhone Personal Hotspot:**
     1. Open **Settings > Personal Hotspot**.
     2. Turn ON **Allow Others to Join**.
     3. **MANDATORY:** Turn ON **"Maximize Compatibility"** (iPhone 12+ defaults to 5 GHz; this switch forces 2.4 GHz broadcast).
     4. Keep the Personal Hotspot settings screen open on the iPhone until the ESP32 associates.
   - **Android Personal Hotspot:**
     1. Open **Settings > Network & internet > Hotspot & tethering > Wi-Fi hotspot**.
     2. Set **AP Band** to **2.4 GHz Band** (not 5.0 GHz / 6.0 GHz).
   - **Home / Lab Router:**
     - Connect to the router's 2.4 GHz SSID.
5. **Compile and Upload:**
   - Click the **Upload** arrow icon (<kbd>Ctrl</kbd> + <kbd>U</kbd>).
   - *If the console shows `Connecting........_____.....`:* Press and hold the physical **BOOT** (or `IO0`) button on the ESP32 board until flashing starts (`Writing at 0x...`), then release it.
6. **Verify Telemetry Stream in Serial Monitor:**
   - Open **Tools > Serial Monitor** (<kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>M</kbd>).
   - Set baud rate to **115200 baud** in the dropdown.
   - Press the `EN` / `RST` button on the ESP32.
   - You should see connection confirmation and live telemetry output:
     ```text
     [*] Connecting to Wi-Fi: <SSID>
     .....
     [+] Wi-Fi Connected!
     [+] ESP32 IP: 192.168.1.50
     [+] Router Gateway: 192.168.1.1
     [*] Wi-Fi CSI Active. Sensing Multipath Disruption...
     $CSI,14320,-52,1.84,1.65,1.20,0
     ```
   - **CRITICAL WARNING:** **Close the Arduino Serial Monitor window** before moving to Step 4/5. Windows strictly prohibits shared serial access; the Python dashboard will fail to open the COM port if Serial Monitor is holding it open.

### Step 4: Python Host Environment Setup (Windows)

1. **Install Python 3.10+:**
   - Download the Windows installer from [python.org](https://www.python.org/downloads/windows/).
   - **CRITICAL:** Check **"Add python.exe to PATH"** on the first installer screen before clicking "Install Now".
2. **Open Terminal & Navigate to Project:**
   - Open Windows Terminal, PowerShell, or Command Prompt (`cmd.exe`).
   - Navigate to the project root directory:
     ```powershell
     cd "C:\path\to\embedded system mini project"
     ```
3. **PowerShell Script Execution Policy (PowerShell only):**
   - Windows restricts script execution by default. If activating the virtual environment is blocked, run this one-time command in PowerShell:
     ```powershell
     Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
     ```
   - *If restricted by Group Policy / Administrator rules:* Either switch to Command Prompt (`cmd.exe`), or run the activation script with bypass:
     ```powershell
     powershell -ExecutionPolicy Bypass -File .\.venv\Scripts\Activate.ps1
     ```
4. **Create & Activate Virtual Environment:**
   - *In PowerShell:*
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```
   - *In Command Prompt (cmd.exe):*
     ```cmd
     python -m venv .venv
     .venv\Scripts\activate.bat
     ```
   - *Note:* If `python` command is not recognized, use the built-in Windows Python launcher: `py -m venv .venv`.
   - Your terminal prompt will now be prefixed with `(.venv)`.
5. **Install Required Packages:**
   ```powershell
   python -m pip install --upgrade pip
   pip install -r dashboard/requirements.txt
   ```
   *(Installs `pyserial>=3.5` for real-time USB-UART streaming).*

### Step 5: Launching the Radar Dashboard on Windows

1. **Live Hardware Mode (ESP32 Connected via USB):**
   ```powershell
   python dashboard/app.py --port COM3 --baud 115200 --http-port 8080
   ```
   *(Replace `COM3` with the actual COM port identified in Device Manager in Step 1. Both forward slash `/` and backslash `\` path separators are supported).*
2. **Standalone Mock / Simulation Mode (No Hardware Needed):**
   ```powershell
   python dashboard/app.py --mock --http-port 8080
   ```
3. **Alternative HTTP Port (if 8080 is in use):**
   ```powershell
   python dashboard/app.py --port COM3 --http-port 8088
   ```
4. **Access the Visualizer:**
   - Open your browser to `http://localhost:8080` (or `http://127.0.0.1:8080`).
   - **Terminal Output Check:** When live hardware is streaming, the terminal will confirm `[*] Opening serial port COM3 at 115200 baud...`. If the port was locked, `app.py` prints `[!] Serial error: ... Switching to edge-case mock generator`, indicating you must close the Serial Monitor and restart.
   - Use the web interface to view the live radar PPI sweep, CSI variance graph, state alerts, and test edge-case injection scenarios.
   - Click **Export CSV** to download test logs for project reports.

### Step 6: Windows-Specific Troubleshooting & Gotchas

| Issue / Error Message | Root Cause | Solution |
| :--- | :--- | :--- |
| `PermissionError: [Errno 13] could not open port 'COM3': PermissionError(13, 'Access is denied.', None, 5)` | Arduino IDE Serial Monitor, PuTTY, or another serial console has locked the COM port. Windows strictly prohibits shared serial access.<br>*(Symptom: Dashboard logs `[!] Serial error... Switching to edge-case mock generator` and falls back to simulation).* | Close the Serial Monitor tab/window in Arduino IDE, close any open serial terminals, and re-run `python dashboard/app.py`. |
| Windows Defender Firewall popup: *"Windows Defender Firewall has blocked some features of this app"* | The Python dashboard server binds to `0.0.0.0:8080` to allow local/LAN web client connections. | Check **Private networks, such as my home or work network**, and click **Allow access**. (Localhost `http://localhost:8080` works even if blocked, but allowing private networks lets teammates view the dashboard from other devices on the LAN). |
| `File ... Activate.ps1 cannot be loaded because running scripts is disabled on this system` | Windows PowerShell default `Restricted` execution policy blocks running local activation scripts. | 1. In PowerShell run: `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`<br>2. OR bypass: `powershell -ExecutionPolicy Bypass -File .\.venv\Scripts\Activate.ps1`<br>3. OR use CMD: `.venv\Scripts\activate.bat`<br>4. OR run directly: `.\.venv\Scripts\python dashboard/app.py --port COM3`. |
| ESP32 loops `[!] Wi-Fi connection timed out` when connecting to iPhone | iPhone Personal Hotspot broadcasts at 5 GHz by default, which the ESP32 2.4 GHz radio cannot receive. | On iPhone, open **Settings > Personal Hotspot**, turn ON **"Maximize Compatibility"** (forces 2.4 GHz). Keep the screen open until connected. |
| ESP32 loops `[!] Wi-Fi connection timed out` when connecting to Android Hotspot | Android Hotspot AP band set to 5 GHz. | Open **Settings > Network & internet > Hotspot & tethering > Wi-Fi hotspot**, set **AP Band** to **2.4 GHz Band**. |
| Board not recognized in Device Manager or listed with yellow `!` under "Other devices" | Missing USB bridge driver or using a charge-only micro-USB cable lacking D+/D- data lines. | 1. Replace the cable with a verified data-sync micro-USB cable.<br>2. Install the Silicon Labs CP210x or WCH CH340 driver from Step 1. |
| Arduino upload stuck on `Connecting........_____.....` | ESP32 automatic bootloader circuit failed to pull GPIO0 low. | Hold down the physical **BOOT** (or `IO0`) button on the ESP32 while dots are printing until `Writing at 0x...` appears. |
| `'python' is not recognized as an internal or external command` | Python was installed without checking "Add python.exe to PATH". | 1. Use the built-in Windows Python launcher: `py dashboard/app.py --port COM3`<br>2. OR re-run the Python installer, click **Modify**, check **Add Python to environment variables**, and restart terminal. |
| `OSError: [Errno 10048] error while attempting to bind on address ('0.0.0.0', 8080)` | Port 8080 is already in use by another Windows service (e.g., IIS, Jenkins, Hyper-V, another dev server). | Pass a different port: `python dashboard/app.py --port COM3 --http-port 8088`, then open `http://localhost:8088`. |

---

## 6. Team Task Division (6–8 Members)

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

## 7. Rubric Compliance Verification

- **Originality & Commercialization (5 pts):** Documented in [docs/commercialization_and_ip.md](docs/commercialization_and_ip.md).
- **Sensors, Actuators & Backup Power (4 pts):** Documented in [docs/circuit_and_wiring.md](docs/circuit_and_wiring.md).
- **PCB Design & Fabrication (4 pts total):** Located in [hardware/kicad/](hardware/kicad/).
- **Physical Implementation (27 pts):** Complete C firmware and wiring netlists ready for deployment.
