#!/usr/bin/env python3
"""
Wi-Fi CSI Real-Time Telemetry & Radar Dashboard Host Server
Supports Multi-Human / Multi-Target Activity Estimation.
Streams serial CSI telemetry from ESP32 to Web Browser via SSE.
"""

import sys
import time
import json
import random
import argparse
from http.server import HTTPServer, SimpleHTTPRequestHandler
from threading import Thread, Lock

try:
    import serial
    HAVE_SERIAL = True
except ImportError:
    HAVE_SERIAL = False

# Shared state
telemetry_lock = Lock()
latest_data = {
    "rssi": -60,
    "raw_var": 1.5,
    "ema_var": 1.2,
    "state": 0,
    "occupant_count": 0,
    "activity_level": "Quiet",
    "targets": [],
    "event": None
}

def estimate_occupants(ema_var):
    """
    Quantizes RF multipath disruption energy into estimated human occupant count:
    - 0: Baseline static environment (< 8.0)
    - 1: Single occupant movement (8.0 <= var < 38.0)
    - 2: Two occupants moving simultaneously (38.0 <= var < 68.0)
    - 3+: Multiple occupants / high crowd movement (>= 68.0)
    """
    if ema_var < 8.0:
        return 0, "Quiet (Empty)"
    elif ema_var < 38.0:
        return 1, "Single Occupant"
    elif ema_var < 68.0:
        return 2, "Two Occupants"
    else:
        return 3, "Multiple Occupants (Crowd)"

def generate_target_blips(count):
    """Generates spatial radar blip coordinates corresponding to detected targets."""
    # Pre-defined spatial sectors for simulated human targets
    target_sectors = [
        {"angle": 0.85, "dist": 0.55, "label": "Target A (Center-Left)"},
        {"angle": 2.25, "dist": 0.70, "label": "Target B (Right Partition)"},
        {"angle": 3.80, "dist": 0.45, "label": "Target C (Perimeter)"}
    ]
    return target_sectors[:count]

def run_serial_listener(port, baudrate):
    global latest_data
    if not HAVE_SERIAL:
        print("[!] pyserial not installed. Falling back to mock generator.")
        run_mock_generator()
        return

    print(f"[*] Opening serial port {port} at {baudrate} baud...")
    try:
        ser = serial.Serial(port, baudrate, timeout=1.0)
        last_count = 0
        while True:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line.startswith("$CSI"):
                parts = line.split(',')
                # Format: $CSI,timestamp_ms,rssi,raw_var,ema_var,state
                if len(parts) >= 6:
                    rssi = int(parts[2])
                    raw_var = float(parts[3])
                    ema_var = float(parts[4])
                    state = int(parts[5])

                    count, activity = estimate_occupants(ema_var)
                    targets = generate_target_blips(count)

                    event = None
                    if count != last_count:
                        if count > last_count:
                            event = f"Occupancy Increased: {count} Human(s) Detected ({activity})"
                        elif count == 0:
                            event = "Zone Clear: All Targets Left / Static"
                        last_count = count

                    with telemetry_lock:
                        latest_data = {
                            "rssi": rssi,
                            "raw_var": raw_var,
                            "ema_var": ema_var,
                            "state": state,
                            "occupant_count": count,
                            "activity_level": activity,
                            "targets": targets,
                            "event": event
                        }
    except Exception as e:
        print(f"[!] Serial error: {e}. Switching to mock generator.")
        run_mock_generator()

def run_mock_generator():
    """Generates synthetic multi-human CSI variance scenarios."""
    global latest_data
    print("[*] Running multi-human synthetic CSI generator (Mock mode).")
    t = 0
    last_count = 0
    ema = 2.0

    while True:
        time.sleep(0.08)  # ~12.5 Hz update
        t += 1
        cycle = t % 360  # ~28 second full cycle

        # Multi-stage simulation scenario:
        # Phase 1 (0-100): Empty room (0 humans)
        # Phase 2 (100-200): 1 human walking behind wall
        # Phase 3 (200-300): 2-3 humans moving simultaneously
        # Phase 4 (300-360): Returning to quiet
        if cycle < 100:
            noise = random.uniform(1.2, 4.5)
        elif cycle < 200:
            noise = random.uniform(18.0, 32.0)
        elif cycle < 300:
            noise = random.uniform(45.0, 85.0)
        else:
            noise = random.uniform(2.0, 6.0)

        ema = (0.25 * noise) + (0.75 * ema)
        count, activity = estimate_occupants(ema)
        targets = generate_target_blips(count)
        state = 1 if count > 0 else 0

        event = None
        if count != last_count:
            if count > last_count:
                event = f"Occupancy Surge: {count} Human(s) Detected ({activity})"
            elif count == 0:
                event = "Zone Clear: Static Room / No Movement"
            last_count = count

        with telemetry_lock:
            latest_data = {
                "rssi": -55 + random.randint(-3, 3),
                "raw_var": round(noise, 2),
                "ema_var": round(ema, 2),
                "state": state,
                "occupant_count": count,
                "activity_level": activity,
                "targets": targets,
                "event": event
            }

class DashboardHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            with open('dashboard/index.html', 'rb') as f:
                self.wfile.write(f.read())
        elif self.path == '/stream':
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Connection', 'keep-alive')
            self.end_headers()

            while True:
                with telemetry_lock:
                    payload = json.dumps(latest_data)
                try:
                    self.wfile.write(f"data: {payload}\n\n".encode('utf-8'))
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    break
                time.sleep(0.08)
        else:
            self.send_error(404)

def main():
    parser = argparse.ArgumentParser(description="Wi-Fi CSI Multi-Human Telemetry Dashboard")
    parser.add_argument('--port', type=str, default='/dev/ttyUSB0', help="Serial port")
    parser.add_argument('--baud', type=int, default=115200, help="Baud rate")
    parser.add_argument('--http-port', type=int, default=8080, help="HTTP server port")
    parser.add_argument('--mock', action='store_true', help="Force mock generator mode")
    args = parser.parse_args()

    if args.mock:
        worker = Thread(target=run_mock_generator, daemon=True)
    else:
        worker = Thread(target=run_serial_listener, args=(args.port, args.baud), daemon=True)
    worker.start()

    server = HTTPServer(('0.0.0.0', args.http_port), DashboardHandler)
    print(f"[*] Multi-Human Radar Dashboard running at http://localhost:{args.http_port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Shutting down server.")

if __name__ == '__main__':
    main()
