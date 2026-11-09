#!/usr/bin/env python3
"""
Wi-Fi CSI Real-Time Telemetry & Radar Dashboard Host Server
Streams serial CSI telemetry from ESP32 Rx Node to Web Browser via SSE.
Stdlib-only server (optional: pyserial for live hardware connection).
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
    "event": None
}
clients = []

def run_serial_listener(port, baudrate):
    global latest_data
    if not HAVE_SERIAL:
        print("[!] pyserial not installed. Falling back to mock generator.")
        run_mock_generator()
        return

    print(f"[*] Opening serial port {port} at {baudrate} baud...")
    try:
        ser = serial.Serial(port, baudrate, timeout=1.0)
        last_state = 0
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

                    event = None
                    if state == 1 and last_state == 0:
                        event = "Movement Detected (Threshold Triggered)"
                    elif state == 0 and last_state == 1:
                        event = "Room Quiet (Alarm Released)"
                    last_state = state

                    with telemetry_lock:
                        latest_data = {
                            "rssi": rssi,
                            "raw_var": raw_var,
                            "ema_var": ema_var,
                            "state": state,
                            "event": event
                        }
    except Exception as e:
        print(f"[!] Serial error: {e}. Switching to mock generator.")
        run_mock_generator()

def run_mock_generator():
    """Generates synthetic CSI variance data for testing without hardware."""
    global latest_data
    print("[*] Running synthetic CSI generator (Mock mode).")
    t = 0
    state = 0
    ema = 2.0
    while True:
        time.sleep(0.08)  # ~12.5 Hz update
        t += 1

        # Simulate movement every 120 ticks (~10 seconds)
        in_movement = (t % 150) > 100
        if in_movement:
            noise = random.uniform(15.0, 32.0)
        else:
            noise = random.uniform(1.0, 4.5)

        ema = (0.25 * noise) + (0.75 * ema)

        event = None
        if ema >= 18.5 and state == 0:
            state = 1
            event = "Movement Detected (Through-Wall Trigger)"
        elif ema < 8.0 and state == 1:
            state = 0
            event = "Zone Clear (Signal Stabilized)"

        with telemetry_lock:
            latest_data = {
                "rssi": -55 + random.randint(-3, 3),
                "raw_var": round(noise, 2),
                "ema_var": round(ema, 2),
                "state": state,
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
    parser = argparse.ArgumentParser(description="Wi-Fi CSI Host Dashboard Server")
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
    print(f"[*] Dashboard running at http://localhost:{args.http_port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Shutting down server.")

if __name__ == '__main__':
    main()
