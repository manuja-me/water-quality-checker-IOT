# Testing & Validation Methodology

## 1. Experimental Setup

The test environment evaluates sensing through three wall materials:
1. **Partition Wall:** 12 mm Gypsum Drywall.
2. **Solid Wall:** 150 mm Brick / Concrete plaster.
3. **Internal Door:** 35 mm Solid Timber.

Distances tested: $1.0\,\text{m}$, $2.5\,\text{m}$, $4.0\,\text{m}$ from the wall boundary.

---

## 2. Test Cases & Verification Protocol

| Test ID | Test Scenario | Expected Outcome | Verification Metric |
| :--- | :--- | :--- | :--- |
| **TC-01** | Static empty room (30 min) | Zero false triggers ($S(t) < 8.0$) | False Positive Rate (FPR) $< 1\%$ |
| **TC-02** | Person walking behind Drywall | Trigger within 300 ms ($S(t) > 18.5$) | True Positive Rate (TPR) $\ge 95\%$ |
| **TC-03** | Person walking behind Brick Wall | Trigger within 500 ms | TPR $\ge 90\%$ |
| **TC-04** | Small non-human motion (fan, pet) | Filtered out by EMA and threshold | FPR $< 5\%$ |
| **TC-05** | Sudden disconnection of 5V USB mains | ESP32 continues operation without brownout reset | Oscilloscope $V_{cc}$ drop $< 200\,\text{mV}$, uptime uninterrupted |
| **TC-06** | Relay & Buzzer actuation | Relay latches within 5 ms of threshold crossing | Measured by logic analyzer |

---

## 3. Parameter Fine-Tuning Grid

| Parameter | Tested Range | Selected Optimal Value | Rationale |
| :--- | :--- | :--- | :--- |
| **Packet Rate** | 20 Hz – 150 Hz | **80 Hz** | Optimal temporal resolution without buffer overflow in ESP32 RAM. |
| **Window Size $N$** | 10 – 100 samples | **40 samples** | $\approx 0.5\,\text{s}$ observation window balances rapid response vs stability. |
| **$\alpha$ (EMA factor)**| 0.10 – 0.50 | **0.25** | Suppresses single-packet outliers while tracking continuous movement. |
| **$T_{\text{high}}$** | 12.0 – 25.0 | **18.5** | Clears baseline ambient multipath noise floor by $> 10\,\text{dB}$. |
| **$T_{\text{low}}$** | 5.0 – 12.0 | **8.0** | Prevents relay chattering on boundary movements. |
| **Holdoff Time** | 500 ms – 3000 ms | **1500 ms** | Ensures reliable alarm indication for external security sirens. |
