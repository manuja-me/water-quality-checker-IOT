#!/usr/bin/env python3
"""
Generates publication-ready simulation plots for the Project Proposal Report.
Simulates Wi-Fi CSI subcarrier fluctuations, sliding variance, and hysteresis.
"""

import math
import random

def run_simulation(samples=300):
    time_series = []
    raw_amplitudes = []
    variances = []
    emas = []
    triggers = []

    window_size = 40
    window = []
    ema = 2.0
    state = 0
    t_high = 18.5
    t_low = 8.0

    for t in range(samples):
        # Samples 100-180: Human walking behind wall
        in_motion = (100 <= t <= 180)

        # Base amplitude with multipath noise
        if in_motion:
            amp = 25.0 + random.uniform(-12.0, 12.0) + 8.0 * math.sin(t * 0.4)
        else:
            amp = 20.0 + random.uniform(-1.5, 1.5)

        raw_amplitudes.append(amp)
        window.append(amp)
        if len(window) > window_size:
            window.pop(0)

        # Sliding variance
        mean = sum(window) / len(window)
        var = sum((x - mean) ** 2 for x in window) / len(window)
        variances.append(var)

        # EMA smoothing
        ema = (0.25 * var) + (0.75 * ema)
        emas.append(ema)

        # Hysteresis state machine
        if state == 0 and ema >= t_high:
            state = 1
        elif state == 1 and ema < t_low:
            state = 0
        triggers.append(state)
        time_series.append(t)

    print(f"[+] Simulation Complete: {samples} samples evaluated.")
    print(f"[+] Baseline Noise Variance: {sum(variances[:90])/90:.2f}")
    print(f"[+] Active Motion Variance:  {sum(variances[110:170])/60:.2f}")
    print(f"[+] Signal-to-Noise Ratio:   {(sum(variances[110:170])/60) / (sum(variances[:90])/90):.1f}x")
    print(f"[+] False Positives in Idle: {sum(triggers[:90])}")
    print(f"[+] Detection in Motion:     {sum(triggers[110:170])}/60 frames active")

if __name__ == "__main__":
    run_simulation()
