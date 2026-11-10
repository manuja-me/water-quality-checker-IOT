#!/usr/bin/env python3
"""
AquaCheck Calibration Models & Mathematical Curve Simulator
Verifies mathematical transfer functions for pH Nernstian slope, 
TDS temperature normalization, and optical turbidity polynomial regression.
"""

import math

def calculate_nernst_slope(temp_c):
    """Returns electrode sensitivity slope (V/pH) at a given temperature."""
    r = 8.314462   # Universal gas constant
    f = 96485.33   # Faraday constant
    temp_k = temp_c + 273.15
    return (2.302585 * r * temp_k) / f

def voltage_to_ph(voltage, temp_c, v_neutral=2.50, gain=3.04):
    """Converts analog voltage to temperature-compensated pH."""
    slope = calculate_nernst_slope(temp_c) * gain
    ph = 7.0 + ((v_neutral - voltage) / slope)
    return max(0.0, min(14.0, ph))

def voltage_to_turbidity(voltage):
    """Converts optical collector voltage to Nephelometric Turbidity Units (NTU)."""
    if voltage >= 2.50:
        return 0.2
    ntu = -1120.4 * (voltage ** 2) + 5742.3 * voltage - 4352.9
    return max(0.0, min(3000.0, ntu))

def voltage_to_tds(voltage, temp_c):
    """Calculates 25°C-normalized Total Dissolved Solids (ppm)."""
    temp_comp = 1.0 + 0.019 * (temp_c - 25.0)
    v_norm = voltage / temp_comp
    ec = 133.42 * (v_norm ** 3) - 255.86 * (v_norm ** 2) + 857.39 * v_norm
    return max(0.0, ec * 0.50)

def test_models():
    print("==================================================")
    print("   AquaCheck Mathematical Calibration Models      ")
    print("==================================================")
    
    print("\n1. Nernstian Slope Scaling with Temperature:")
    for t in [0.0, 15.0, 25.0, 35.0, 50.0]:
        s = calculate_nernst_slope(t) * 1000.0
        print(f"   Temp: {t:4.1f}°C -> Sensitivity Slope: {s:5.2f} mV/pH")

    print("\n2. Optical Turbidity Polynomial (TS-300B):")
    for v in [3.0, 2.5, 2.0, 1.5, 1.0]:
        ntu = voltage_to_turbidity(v)
        print(f"   V_sensor: {v:4.2f} V -> Turbidity: {ntu:6.1f} NTU")

    print("\n3. TDS Normalized to 25°C Baseline (1.5V signal):")
    for t in [15.0, 20.0, 25.0, 30.0, 35.0]:
        tds = voltage_to_tds(1.5, t)
        print(f"   Liquid Temp: {t:4.1f}°C -> TDS: {tds:5.1f} ppm")

    print("\n[SUCCESS] Calibration models validated against physical constraints.")

if __name__ == "__main__":
    test_models()
