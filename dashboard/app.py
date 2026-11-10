#!/usr/bin/env python3
"""
Wi-Fi CSI Real-Time Telemetry & Radar Dashboard Host Server
Hardened for Edge Cases with Guaranteed Event Recording & CSV Export.
"""

import os
import glob
import sys
import time
import json
import random
import argparse
from urllib.parse import urlparse, parse_qs
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from threading import Thread, Lock
from collections import deque

try:
    import serial
    HAVE_SERIAL = True
except ImportError:
    HAVE_SERIAL = False

telemetry_lock = Lock()
pending_events = deque()
session_log_records = []  # In-memory session recorder for CSV export

latest_data = {
    "rssi": -58,
    "raw_var": 1.5,
    "ema_var": 1.4,
    "baseline": 1.2,
    "state_id": 0,
    "state_name": "EMPTY (QUIET)",
    "occupant_count": 0,
    "active_edge_case": "Normal Baseline Monitoring",
    "targets": [],
    "event": None
}

# Edge Case Simulation State Machine
sim_override = "auto"
sim_override_time = 0

def resolve_state(state_id, ema_var, baseline):
    # Host DSP refinement: 1 ESP32 + 1 iPhone Hotspot setup
    if state_id == 0:
        delta = ema_var - baseline
        if delta >= 4.0 or ema_var >= 5.0:
            state_id = 1
        elif delta >= 0.25 or (baseline > 0.2 and ema_var >= baseline * 1.2):
            state_id = 3

    names = {
        0: ("EMPTY (QUIET)", 0, []),
        1: ("ACTIVE HUMAN MOTION", 1, [{"angle": 0.0, "dist": 0.50, "label": "Human (Moving)"}]),
        2: ("HIGH-INTENSITY HUMAN MOTION", 1, [{"angle": 0.0, "dist": 0.40, "label": "Human (Fast Movement)"}]),
        3: ("HUMAN PRESENCE DETECTED", 1, [{"angle": 0.0, "dist": 0.50, "label": "Human (Present)"}]),
        4: ("HUMAN OCCLUSION (BLOCKING PATH)", 1, [{"angle": 0.0, "dist": 0.30, "label": "Human (Blocking Path)"}])
    }
    name, count, targets = names.get(state_id, ("UNKNOWN", 0, []))
    return name, count, targets, state_id

def run_serial_listener(port, baudrate):
    global latest_data
    if not HAVE_SERIAL:
        print("[!] pyserial not found. Using edge-case simulation generator.")
        run_mock_generator()
        return

    last_state = -1
    while True:
        target_port = port
        if not os.path.exists(target_port):
            detected = sorted(glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*'))
            if detected:
                target_port = detected[0]
            else:
                print("[*] No serial port detected. Waiting for ESP32 USB connection...")
                time.sleep(1.0)
                continue

        print(f"[*] Opening serial port {target_port} at {baudrate} baud...")
        try:
            with serial.Serial(target_port, baudrate, timeout=1.0) as ser:
                while True:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    if "$CSI" in line:
                        try:
                            csi_start = line.find("$CSI")
                            parts = line[csi_start:].split(',')
                            # Format: $CSI,timestamp_ms,rssi,raw_var,ema_var,baseline,state_id
                            if len(parts) >= 7 and parts[0] == "$CSI":
                                rssi = int(parts[2])
                                raw_var = float(parts[3])
                                ema_var = float(parts[4])
                                baseline = float(parts[5])
                                state_id = int(parts[6])

                                name, count, targets, state_id = resolve_state(state_id, ema_var, baseline)
                                event = None
                                if state_id != last_state:
                                    event = f"State Shift: {name} (EMA: {ema_var:.1f}, Base: {baseline:.1f})"
                                    last_state = state_id
                                    with telemetry_lock:
                                        session_log_records.append({
                                            "time": time.strftime("%H:%M:%S"),
                                            "case": "Live Hardware",
                                            "state": name,
                                            "raw_var": raw_var,
                                            "ema_var": ema_var,
                                            "baseline": baseline,
                                            "event": event
                                        })

                                with telemetry_lock:
                                    latest_data = {
                                        "rssi": rssi,
                                        "raw_var": raw_var,
                                        "ema_var": ema_var,
                                        "baseline": baseline,
                                        "state_id": state_id,
                                        "state_name": name,
                                        "occupant_count": count,
                                        "active_edge_case": "Live Hardware Stream",
                                        "targets": targets,
                                        "event": event
                                    }
                        except (ValueError, IndexError):
                            continue
        except Exception as e:
            print(f"[!] Serial error on {target_port}: {e}. Retrying in 1s...")
            time.sleep(1.0)

def run_mock_generator():
    global latest_data, sim_override, pending_events, session_log_records
    print("[*] Edge-case simulation engine active.")
    t = 0
    ema = 1.5
    baseline = 1.2
    last_case = ""

    while True:
        time.sleep(0.08)
        t += 1

        # Check mode: interactive manual lock or auto cycle
        if sim_override != "auto":
            case = sim_override
        else:
            cycle = t % 420
            if cycle < 90:
                case = "quiet"
            elif cycle < 150:
                case = "single_walk"
            elif cycle < 230:
                case = "static_presence"
            elif cycle < 260:
                case = "microwave_spike"
            elif cycle < 350:
                case = "multi_human"
            elif cycle < 390:
                case = "packet_loss"
            else:
                case = "quiet"

        # Edge Case Logic
        if case == "quiet":
            raw = baseline + random.uniform(-0.3, 0.4)
            ema = (0.25 * raw) + (0.75 * ema)
            state_id = 0
            rssi = -55
            desc = "Quiet Baseline (No Motion)"
        elif case == "single_walk":
            raw = baseline + random.uniform(20.0, 35.0)
            ema = (0.25 * raw) + (0.75 * ema)
            state_id = 1
            rssi = -58
            desc = "1-Human Active Motion"
        elif case == "static_presence":
            raw = baseline + random.uniform(1.2, 2.8)
            ema = (0.05 * raw) + (0.95 * ema)
            state_id = 3
            rssi = -57
            desc = "Seated / Still Occupant (Breathing Hold)"
        elif case == "microwave_spike":
            # Outlier spike clamped by Hampel filter
            is_spike = (t % 12 == 0)
            raw = 95.0 if is_spike else (baseline + 0.5)
            ema = min(ema + 1.8, 6.2) # Clamped below 18.5 threshold
            state_id = 0
            rssi = -72 if is_spike else -58
            desc = "Microwave / EMI Spike (Clamped & Filtered)"
        elif case == "multi_human":
            raw = baseline + random.uniform(48.0, 80.0)
            ema = (0.25 * raw) + (0.75 * ema)
            state_id = 2
            rssi = -61
            desc = "Multi-Human Crossing"
        elif case == "packet_loss":
            raw = 0.0
            ema = 0.0
            state_id = 4
            rssi = -99
            desc = "Wi-Fi Link Drop (Watchdog Triggered)"
        else:
            raw = baseline
            ema = baseline
            state_id = 0
            rssi = -55
            desc = case

        name, count, targets, state_id = resolve_state(state_id, ema, baseline)

        # Detect case transition and record
        event = None
        if case != last_case:
            event = f"Scenario Active: {desc}"
            last_case = case
            with telemetry_lock:
                session_log_records.append({
                    "time": time.strftime("%H:%M:%S"),
                    "case": desc,
                    "state": name,
                    "raw_var": round(raw, 2),
                    "ema_var": round(ema, 2),
                    "baseline": round(baseline, 2),
                    "event": event
                })

        # Pop any queued manual trigger events
        with telemetry_lock:
            if pending_events:
                event = pending_events.popleft()

            latest_data = {
                "rssi": rssi,
                "raw_var": round(raw, 2),
                "ema_var": round(ema, 2),
                "baseline": round(baseline, 2),
                "state_id": state_id,
                "state_name": name,
                "occupant_count": count,
                "active_edge_case": desc,
                "active_key": case,
                "targets": targets,
                "event": event
            }

class DashboardHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/' or parsed.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'index.html')
            with open(html_path, 'rb') as f:
                self.wfile.write(f.read())
        elif parsed.path == '/stream':
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
                except Exception:
                    break
                time.sleep(0.08)
        elif parsed.path == '/trigger-edge-case':
            global sim_override, pending_events, session_log_records
            qs = parse_qs(parsed.query)
            case = qs.get('case', ['quiet'])[0]
            sim_override = case

            case_labels = {
                "quiet": "Quiet Baseline (No Motion)",
                "single_walk": "1-Human Walking",
                "static_presence": "Seated / Still (Breathing Hold)",
                "microwave_spike": "Microwave / EMI Spike (Hampel Rejection)",
                "multi_human": "Multi-Human Crowd",
                "packet_loss": "Packet Drop / Link Degradation",
                "auto": "Auto Scenario Rotation"
            }
            label = case_labels.get(case, case)
            log_msg = f"[Manual Trigger] Activated: {label}"

            with telemetry_lock:
                pending_events.append(log_msg)
                session_log_records.append({
                    "time": time.strftime("%H:%M:%S"),
                    "case": label,
                    "state": "TRIGGERED",
                    "raw_var": 0.0,
                    "ema_var": 0.0,
                    "baseline": 1.2,
                    "event": log_msg
                })

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "case": case, "label": label}).encode('utf-8'))
        elif parsed.path == '/export-log':
            # Export session log as CSV
            self.send_response(200)
            self.send_header('Content-Type', 'text/csv')
            self.send_header('Content-Disposition', 'attachment; filename="csi_simulation_events.csv"')
            self.end_headers()
            csv_lines = ["Timestamp,Scenario,State,RawVariance,EMAVariance,Baseline,EventDetails\n"]
            with telemetry_lock:
                for rec in session_log_records:
                    clean_event = rec["event"].replace(',', ';') if rec["event"] else ""
                    csv_lines.append(f"{rec['time']},{rec['case']},{rec['state']},{rec['raw_var']},{rec['ema_var']},{rec['baseline']},{clean_event}\n")
            self.wfile.write("".join(csv_lines).encode('utf-8'))
        else:
            self.send_error(404)

def main():
    parser = argparse.ArgumentParser(description="Edge-Case Resilient Wi-Fi CSI Dashboard")
    parser.add_argument('--port', type=str, default='/dev/ttyUSB0', help="Serial port")
    parser.add_argument('--baud', type=int, default=115200, help="Baud rate")
    parser.add_argument('--http-port', type=int, default=8080, help="HTTP server port")
    parser.add_argument('--mock', action='store_true', help="Force mock generator mode")
    args = parser.parse_args()

    if not args.mock and not os.path.exists(args.port):
        detected = sorted(glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*'))
        if detected:
            print(f"[*] Port {args.port} not found; auto-detected {detected[0]}")
            args.port = detected[0]

    if args.mock:
        worker = Thread(target=run_mock_generator, daemon=True)
    else:
        worker = Thread(target=run_serial_listener, args=(args.port, args.baud), daemon=True)
    worker.start()

    server = ThreadingHTTPServer(('0.0.0.0', args.http_port), DashboardHandler)
    print(f"[*] Edge-Case Dashboard running at http://localhost:{args.http_port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Shutting down server.")

if __name__ == '__main__':
    main()
