#!/usr/bin/env python3
"""
AquaCheck Live Telemetry Bridge & Web Visualizer
Provides real-time Server-Sent Events (SSE) telemetry from the ESP32 USB-UART interface
or simulates realistic multi-vial liquid sample testing in mock mode.
"""

import sys
import time
import json
import random
import argparse
from flask import Flask, Response, render_template_string

app = Flask(__name__)

# Sample Simulation Profiles (for Demo / Mock Mode)
SAMPLE_PROFILES = [
    {"name": "Vial A: Deionized Water", "temp": 24.8, "ph": 7.05, "turb": 0.2, "tds": 15, "status": "SAFE"},
    {"name": "Vial B: Municipal Tap Water", "temp": 25.1, "ph": 7.34, "turb": 1.4, "tds": 195, "status": "SAFE"},
    {"name": "Vial C: Muddy Silt Runoff", "temp": 24.9, "ph": 6.92, "turb": 46.8, "tds": 320, "status": "UNSAFE_TURBIDITY"},
    {"name": "Vial D: High-Saline Well", "temp": 25.5, "ph": 8.35, "turb": 1.8, "tds": 1380, "status": "HAZARDOUS_TDS"},
]

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AquaCheck | Live Telemetry Dashboard</title>
    <style>
        :root {
            --bg-color: #0F172A;
            --card-bg: #1E293B;
            --accent-teal: #0D9488;
            --accent-blue: #38BDF8;
            --text-main: #F8FAFC;
            --text-muted: #94A3B8;
            --border-color: #334155;
            --safe-green: #22C55E;
            --warn-yellow: #EAB308;
            --danger-red: #EF4444;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        body { background: var(--bg-color); color: var(--text-main); padding: 24px; min-height: 100vh; }
        .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border-color); padding-bottom: 16px; margin-bottom: 24px; }
        .logo { font-size: 24px; font-weight: 800; color: var(--accent-blue); letter-spacing: 0.5px; }
        .badge { background: #064E3B; color: #6EE7B7; padding: 4px 12px; border-radius: 999px; font-size: 12px; font-weight: 600; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 18px; margin-bottom: 24px; }
        .card { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 12px; padding: 20px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2); }
        .card-title { font-size: 13px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.7px; margin-bottom: 8px; }
        .card-value { font-size: 36px; font-weight: 700; color: var(--text-main); margin-bottom: 4px; }
        .card-unit { font-size: 14px; font-weight: 500; color: var(--accent-teal); }
        .card-subtext { font-size: 11px; color: var(--text-muted); margin-top: 8px; }
        .status-box { background: var(--card-bg); border: 2px solid var(--safe-green); border-radius: 12px; padding: 24px; text-align: center; margin-bottom: 24px; transition: all 0.3s ease; }
        .status-title { font-size: 14px; color: var(--text-muted); text-transform: uppercase; margin-bottom: 6px; }
        .status-badge { font-size: 28px; font-weight: 800; color: var(--safe-green); letter-spacing: 1px; }
        .status-benchmarks { display: flex; justify-content: space-around; margin-top: 14px; font-size: 12px; color: var(--text-muted); border-top: 1px solid var(--border-color); padding-top: 12px; }
        .footer { font-size: 11px; color: var(--text-muted); text-align: center; margin-top: 36px; }
    </style>
</head>
<body>
    <div class="header">
        <div>
            <div class="logo">AQUACHECK</div>
            <div style="font-size: 12px; color: var(--text-muted);">Portable Multi-Parameter Water Quality Monitor (ESP32)</div>
        </div>
        <div class="badge" id="conn-badge">LIVE STREAM ACTIVE</div>
    </div>

    <div class="status-box" id="status-card">
        <div class="status-title">Sri Lanka Standard SLS 614 & WHO Classification</div>
        <div class="status-badge" id="status-val">SAFE (POTABLE WATER)</div>
        <div class="status-benchmarks">
            <span>pH Limit: 6.5 - 8.5</span>
            <span>TDS Limit: &lt; 500 ppm</span>
            <span>Turbidity Limit: &lt; 5.0 NTU</span>
        </div>
    </div>

    <div class="grid">
        <div class="card">
            <div class="card-title">Acidity / Alkalinity</div>
            <div class="card-value"><span id="ph-val">7.20</span> <span class="card-unit">pH</span></div>
            <div class="card-subtext">Compensated Nernstian slope (±0.1)</div>
        </div>
        <div class="card">
            <div class="card-title">Total Dissolved Solids</div>
            <div class="card-value"><span id="tds-val">185</span> <span class="card-unit">ppm</span></div>
            <div class="card-subtext">25°C Normalized Conductivity</div>
        </div>
        <div class="card">
            <div class="card-title">Water Turbidity (Clarity)</div>
            <div class="card-value"><span id="turb-val">1.2</span> <span class="card-unit">NTU</span></div>
            <div class="card-subtext">Optical TS-300B IR Scattering</div>
        </div>
        <div class="card">
            <div class="card-title">Sample Liquid Temperature</div>
            <div class="card-value"><span id="temp-val">25.1</span> <span class="card-unit">°C</span></div>
            <div class="card-subtext">DS18B20 1-Wire Digital Sensor</div>
        </div>
    </div>

    <div class="footer">
        AquaCheck Embedded Systems Mini-Project | Technical Diagnostics Telemetry Engine
    </div>

    <script>
        const evtSource = new EventSource('/stream');
        evtSource.onmessage = function(event) {
            const data = JSON.parse(event.data);
            document.getElementById('ph-val').textContent = data.ph.toFixed(2);
            document.getElementById('tds-val').textContent = Math.round(data.tds);
            document.getElementById('turb-val').textContent = data.turb.toFixed(1);
            document.getElementById('temp-val').textContent = data.temp.toFixed(1);
            
            const statusCard = document.getElementById('status-card');
            const statusVal = document.getElementById('status-val');

            if (data.status === 'SAFE') {
                statusVal.textContent = 'SAFE (POTABLE WATER)';
                statusVal.style.color = '#22C55E';
                statusCard.style.borderColor = '#22C55E';
            } else if (data.status === 'PERMISSIBLE') {
                statusVal.textContent = 'PERMISSIBLE (SLS 614 MARGINAL)';
                statusVal.style.color = '#EAB308';
                statusCard.style.borderColor = '#EAB308';
            } else if (data.status === 'UNSAFE_TURBIDITY') {
                statusVal.textContent = 'UNSAFE - HIGH TURBIDITY (>5 NTU)';
                statusVal.style.color = '#EF4444';
                statusCard.style.borderColor = '#EF4444';
            } else {
                statusVal.textContent = 'HAZARDOUS - MINERAL OVERLOAD (>1000 PPM)';
                statusVal.style.color = '#EF4444';
                statusCard.style.borderColor = '#EF4444';
            }
        };
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

def generate_mock_stream():
    profile_idx = 0
    step = 0
    while True:
        profile = SAMPLE_PROFILES[profile_idx]
        # Add tiny realistic fluctuation
        temp = profile["temp"] + random.uniform(-0.1, 0.1)
        ph = profile["ph"] + random.uniform(-0.04, 0.04)
        turb = max(0.1, profile["turb"] + random.uniform(-0.2, 0.2))
        tds = max(5, profile["tds"] + random.uniform(-5, 5))
        
        payload = {
            "temp": round(temp, 1),
            "ph": round(ph, 2),
            "turb": round(turb, 1),
            "tds": int(tds),
            "status": profile["status"]
        }
        yield f"data: {json.dumps(payload)}\n\n"
        time.sleep(1.0)
        
        step += 1
        if step % 8 == 0:
            profile_idx = (profile_idx + 1) % len(SAMPLE_PROFILES)

def generate_serial_stream(port, baudrate=115200):
    import serial
    ser = serial.Serial(port, baudrate, timeout=1.5)
    while True:
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        if line.startswith('{') and line.endswith('}'):
            try:
                data = json.loads(line)
                yield f"data: {json.dumps(data)}\n\n"
            except json.JSONDecodeError:
                pass
        time.sleep(0.05)

@app.route('/stream')
def stream():
    if app.config.get('MOCK_MODE', True):
        return Response(generate_mock_stream(), mimetype='text/event-stream')
    else:
        return Response(generate_serial_stream(app.config['SERIAL_PORT']), mimetype='text/event-stream')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="AquaCheck Web Telemetry Server")
    parser.add_argument('--port', type=str, default=None, help="Serial port (e.g. /dev/ttyUSB0 or COM3)")
    parser.add_argument('--mock', action='store_true', default=True, help="Run in mock/simulation mode")
    args = parser.parse_args()

    if args.port and not args.mock:
        app.config['MOCK_MODE'] = False
        app.config['SERIAL_PORT'] = args.port
        print(f"[AquaCheck] Starting server with Serial bridge on {args.port}...")
    else:
        app.config['MOCK_MODE'] = True
        print("[AquaCheck] Starting server in MOCK / DEMO mode...")

    app.run(host='0.0.0.0', port=5000, debug=False)
