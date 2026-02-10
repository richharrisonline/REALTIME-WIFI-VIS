#!/usr/bin/env python3
# RPi Wi-Fi scanner → sends DATA line with RSSI + SSID + MAC interleaved
# Run with: python3 rpi_collector.py

import subprocess
import time
import socket
import re

# ────────────────────────────────────────────────
# CONFIG – FILL THESE IN
# ────────────────────────────────────────────────
SERVER_IP = "192.168.0.168"       # ← IP of the computer running the dashboard
SERVER_PORT = 65432               # ← must match the RPI_PORT in your dashboard code
INTERFACE = "wlan0"               # usually wlan0 on Raspberry Pi
SCAN_INTERVAL = 3.0               # seconds between scans (RPi can handle 3s easily)

# ────────────────────────────────────────────────
# Get own MAC, SSID and RSSI (The "Anchor" node)
# ────────────────────────────────────────────────
def get_own_info():
    try:
        mac = subprocess.check_output(["cat", f"/sys/class/net/{INTERFACE}/address"]).decode().strip()
    except:
        mac = "00:00:00:00:00:00"

    try:
        ssid = subprocess.check_output(["iwgetid", "-r"]).decode().strip()
    except:
        ssid = "UNKNOWN_RPI"

    try:
        link = subprocess.check_output(["iw", INTERFACE, "link"]).decode()
        rssi_match = re.search(r'signal: (-\d+) dBm', link)
        rssi = int(rssi_match.group(1)) if rssi_match else -50
    except:
        rssi = -50

    return rssi, mac, ssid

# ────────────────────────────────────────────────
# Scan nearby networks via nmcli (Faster background scan)
# ────────────────────────────────────────────────
def scan_wifi():
    try:
        # -t (terse), -f (fields). Separator is ':'
        cmd = "nmcli -t -f SSID,BSSID,SIGNAL dev wifi list"
        output = subprocess.check_output(cmd, shell=True).decode('utf-8')
        
        networks = []
        for line in output.strip().split('\n'):
            parts = line.split(':')
            if len(parts) >= 8: # nmcli MACs come out as AA:BB:CC... (6 parts)
                ssid = parts[0]
                # Reconstruct MAC because split(':') breaks the MAC address
                mac = ":".join(parts[1:7]).replace('\\', '')
                try:
                    rssi = int(parts[7])
                    # nmcli returns positive 0-100 for signal, convert to dBm roughly
                    dbm = (rssi / 2) - 100 
                    if ssid: # Only add if it has a name
                        networks.append((ssid, int(dbm), mac))
                except:
                    continue

        # Sort by signal strength (strongest first)
        networks.sort(key=lambda x: x[1], reverse=True)
        return networks[:12]  # top 12 neighbors

    except Exception as e:
        print(f"Scan error: {e}")
        return []

# ────────────────────────────────────────────────
# Build DATA line: DATA, <rssi0>, <mac0>, <rssi1>, <ssid1>, <mac1>...
# ────────────────────────────────────────────────
def build_data_line():
    own_rssi, own_mac, own_ssid = get_own_info()
    networks = scan_wifi()

    # Dashboard expects: DATA, RSSI_0, MAC_0, RSSI_1, SSID_1, MAC_1...
    # Note: Slot 0 is usually the "Primary" node on the map
    parts = ["DATA", str(own_rssi), own_mac]

    for ssid, rssi, mac in networks:
        # Skip your own network if it appears in the scan to avoid duplicates
        if mac.lower() == own_mac.lower():
            continue
        parts.append(str(rssi))
        parts.append(ssid)
        parts.append(mac)

    return ", ".join(parts)

# ────────────────────────────────────────────────
# Connect & send continuously
# ────────────────────────────────────────────────
def sender_thread():
    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(10)
                print(f"Connecting to {SERVER_IP}:{SERVER_PORT}...")
                s.connect((SERVER_IP, SERVER_PORT))
                print("Connected successfully")
                
                while True:
                    data_line = build_data_line()
                    print(f"Relaying {data_line.count(',')//2} neighbors...")
                    s.sendall((data_line + "\n").encode())
                    time.sleep(SCAN_INTERVAL)
        except Exception as e:
            print(f"Connection lost: {e}. Retrying in 5s...")
            time.sleep(5)

if __name__ == "__main__":
    print("RPi Neighbor Collector Active")
    sender_thread()
