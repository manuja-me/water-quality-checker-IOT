# Strategic Commercialization, Intellectual Property & Publication Plan

## 1. Commercialization Plan

### Market Opportunity & Value Proposition
Conventional presence sensors suffer from major limitations:
- **PIR Sensors:** Require direct Line-of-Sight (LoS); blind through walls, partitions, and glass.
- **Cameras:** Pose severe privacy violations in private residences, patient rooms, and restrooms.
- **mmWave Radars:** Expensive ($25–$120 per node), specialized hardware, limited RF penetration.

**Proposed Product:** *AuraSense* — Privacy-preserving, through-wall presence detection utilizing low-cost commodity Wi-Fi silicon (ESP32, BOM cost < $15).

### Target Verticals
1. **Elderly Care & Fall Monitoring:** Non-intrusive monitoring inside bathrooms and bedrooms without cameras.
2. **Perimeter Intrusion Detection:** Through-wall detection behind doors, store rooms, and perimeter walls.
3. **Smart Building HVAC Automation:** True presence detection (even when occupant is seated/typing) to eliminate PIR timeout errors.

### Financial Viability (Unit Economics)
- **Bill of Materials (BOM):** ~$11.80 at 1,000 unit volume.
- **Manufacturing & Enclosure (Injection molded ABS):** ~$3.20.
- **MSRP:** $39.99 (62.5% Gross Margin).

---

## 2. Intellectual Property (IP) Protection Strategy

### Patent Claim Draft (Core Invention)
*Title: Edge-Computed RF Channel State Information Presence Detector with Dynamic Hysteresis and Zero-Inversion Power Switching.*

**Independent Claim 1:**
> "A device-free physical disturbance detection system comprising:
> an RF transceiver configured to capture raw 802.11 Channel State Information (CSI) subcarrier vectors at a sampling frequency exceeding 50 Hz;
> an onboard edge processor configured to execute deterministic, non-machine-learning variance extraction across a temporal sliding window buffer;
> an asymmetric dual-threshold Schmitt state machine configured to trigger local physical actuation; and
> a low-loss diode-isolated battery backup circuit providing uninterrupted RF packet reception during primary mains disconnection."

### Copyright Registration
- Firmware source code (embedded C / ESP-IDF) registered under national intellectual property laws as original computer program code.
- Schematic and PCB layout CAD files registered as technical drawings.

---

## 3. Potential for Research Publication

### Target Venues
- **IEEE Sensors Letters** or **IEEE International Conference on Wireless and Mobile Computing, Networking and Communications (WiMob)**.
- **Theme:** *Edge-computed, Zero-Training Wi-Fi CSI Presence Detection on Resource-Constrained Microcontrollers.*

### Publication Scope & Contribution
1. Proving that sliding variance + EMA on 32-bit microcontrollers achieves $>94\%$ through-wall presence detection accuracy without requiring deep learning or external GPU compute.
2. Characterizing RF penetration across common building materials (brick, drywall, wood) using 2.4 GHz 802.11n subcarriers.
3. Quantifying power consumption and uninterrupted edge processing during utility mains transitions.
