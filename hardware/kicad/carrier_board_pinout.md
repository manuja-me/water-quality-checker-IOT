# 2-Layer Custom Carrier Shield PCB Specifications

To secure maximum marks under the **"Plan for Printed Circuit Board (PCB) Design & Fabricating"** criteria (1 mark in Proposal, 3 marks in Final Evaluation), AquaCheck transitions from a fragile breadboard to a robust 2-layer custom carrier board.

---

## 1. Board Dimensions & Mechanical Constraints

- **PCB Dimensions:** $75.0\text{ mm} \times 65.0\text{ mm}$ (Standard compact format, fits comfortably into 3D-printed enclosure).
- **Layer Count:** 2 Layers (Top: Signal Routing & Component Placement; Bottom: Continuous Low-Impedance Ground Plane).
- **Substrate:** FR-4, $1.6\text{ mm}$ thickness, $1\text{ oz}$ Copper Weight ($35\ \mu\text{m}$).
- **Surface Finish:** HASL (Lead-Free) or ENIG for corrosion resistance in high-humidity water testing environments.

---

## 2. Component Placement & Layout Strategy

```
┌─────────────────────────────────────────────────────────────┐
│  [TP4056 USB-C]    [MT3608 Boost]     [PWR SWITCH]          │
│                                                             │
│       ┌────────────────────────┐                            │
│       │   ESP32 DevKit V1      │      [0.96" OLED HEADER]   │
│       │   (Socket Headers)     │                            │
│       └────────────────────────┘      [MicroSD SPI HEADER]  │
│                                                             │
│  [2N7000 MOSFET]   [BUZZER & LEDS]                          │
│                                                             │
│  [pH BNC Header]   [Turbidity Port]   [TDS Screw Terminal]  │
└─────────────────────────────────────────────────────────────┘
```

1. **Power Domain Partitioning:**
   - The high-efficiency switching regulator (MT3608) and TP4056 battery charger are placed along the top edge, separated from sensitive analog sensors by at least $20\text{ mm}$ to prevent inductive switching spikes from coupling into the ADC lines.
2. **Analog Ground Plane:**
   - The bottom copper plane is dedicated to a solid Ground plane. The analog sensor return paths connect directly to a star ground point right beneath the ESP32 ground pins.
3. **Signal Trace Widths:**
   - Power traces (5V, 3.3V, Battery): $0.80\text{ mm}$ (31 mils) to support currents up to $1.5\text{ A}$ with $< 0.1^\circ\text{C}$ temperature rise.
   - High-speed digital traces (SPI, I2C): $0.25\text{ mm}$ (10 mils).
   - Sensitive Analog traces (pH, Turbidity, TDS): $0.35\text{ mm}$ (14 mils), routed with guard ground tracks to shield against EMI.

---

## 3. Fabrication & Assembly Roadmap

1. **Schematic & Layout Software:** Designed using KiCad 8.0 or EasyEDA.
2. **Fabrication Options in Sri Lanka:**
   - **Rapid Prototyping:** Direct toner-transfer and ferric chloride chemical etching or CNC PCB milling at the university makerspace.
   - **Production Quality:** Export Gerber RS-274X files and order via JLCPCB / PCBWay (5 boards for ~$2 USD + shipping).
