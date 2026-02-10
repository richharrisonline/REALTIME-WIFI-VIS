#!/usr/bin/env python3
"""
Raspberry Pi WiFi Neighbor Collector
====================================
This script scans for nearby WiFi Access Points using 'nmcli' and relays the 
signal data (RSSI, SSID, MAC) to the Python Visualizer Dashboard via TCP.

Role:
- Acts as a high-power "Anchor" node.
- Reports its own connection status + the top 12 strongest nearby neighbors.

Requirements:
- A Raspberry Pi with WiFi (Pi 3, 4, 5, or Zero W).
- NetworkManager installed (`sudo apt install network-manager`).
- The Dashboard PC and the Pi must be on the same local network.

Author: [richharrisonline]
License: NO
"""

import subprocess
import time
import socket
import re

# ────────────────────────────────────────────────
# CONFIGURATION – MATCH THESE TO YOUR DASHBOARD
# ────────────────────────────────────────────────
SERVER_IP = "192.168.0.168"       # IP Address of the PC running the dashboard
SERVER_PORT = 65432               # Must match SERVER_PORT in your visualizer code
INTERFACE = "wlan0"               # WiFi interface name
SCAN_INTERVAL = 3.0               # Frequency of updates (seconds)

# ────────────────────────────────────────────────
# SYSTEM UTILITIES
# ────────────────────────────────────────────────

def get_own_info():
    """
    Retrieves the Raspberry Pi's own WiFi details (The Anchor).
    Uses 'iw' and system files to bypass standard scanning.
    """
    try:
        # Get hardware MAC address
        mac = subprocess.check_output(["cat", f"/sys/class/net/{INTERFACE}/address"]).decode().strip()
    except:
        mac = "00:00:00:00:00:00"

    try:
        # Get the SSID the Pi is currently connected to
        ssid = subprocess.check_output(["iwgetid", "-r"]).decode().strip()
    except:
        ssid = "UNKNOWN_RPI"

    try:
        # Extract signal strength of the current connection
        link = subprocess.check_output(["iw", INTERFACE, "link"]).decode()
        rssi_match = re.search(r'signal: (-\d+) dBm', link)
        rssi = int(rssi_match.group(1)) if rssi_match else -50
    except:
        rssi = -50

    return rssi, mac, ssid

def scan_wifi():
    """
    Uses NetworkManager (nmcli) to perform a quick background scan of nearby APs.
    Converts 0-100 quality scores into approximate dBm values.
    """
    try:
        # -t (terse): easy to parse, -f: specific fields
        cmd = "nmcli -t -f SSID,BSSID,SIGNAL dev wifi list"
        output = subprocess.check_output(cmd, shell=True).decode('utf-8')
        
        networks = []
        for line in output.strip().split('\n'):
            parts = line.split(':')
            # nmcli separates MAC parts by ':', so we reconstruct the full BSSID
            if len(parts) >= 8: 
                ssid = parts[0]
                mac = ":".join(parts[1:7]).replace('\\', '')
                try:
                    signal_quality = int(parts[7])
                    # Rough conversion from % quality to dBm
                    dbm = (signal_quality / 2) - 100 
                    if ssid: 
                        networks.append((ssid, int(dbm), mac))
                except:
                    continue

        # Sort by signal strength (descending)
        networks.sort(key=lambda x: x[1], reverse=True)
        return networks[:12]  # Limit to top 12 to keep data packets small

    except Exception as e:
        print(f"Scan error: {e}")
        return []

def build_data_line():
    """
    Packages 'own info' and 'neighbor info' into a CSV string compatible
    with the Dashboard's network parser.
    """
    own_rssi, own_mac, own_ssid = get_own_info()
    networks = scan_wifi()

    # Format: DATA, <RSSI_0>, <MAC_0>, <RSSI_1>, <SSID_1>, <MAC_1>...
    parts = ["DATA", str(own_rssi), own_mac]

    for ssid, rssi, mac in networks:
        # Don't report self as a neighbor
        if mac.lower() == own_mac.lower():
            continue
        parts.append(str(rssi))
        parts.append(ssid)
        parts.append(mac)

    return ", ".join(parts)

# ────────────────────────────────────────────────
# NETWORK TRANSMISSION
# ────────────────────────────────────────────────

def sender_thread():
    """
    Main loop: Handles socket connection and periodic data relay.
    Includes auto-reconnect logic if the dashboard is restarted.
    """
    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(10)
                print(f"[*] Connecting to Dashboard at {SERVER_IP}:{SERVER_PORT}...")
                s.connect((SERVER_IP, SERVER_PORT))
                print("[+] Connection established.")
                
                while True:
                    data_line = build_data_line()
                    print(f"[>] Sending data: {len(data_line)} bytes ({data_line.count(',')//2} nodes)")
                    s.sendall((data_line + "\n").encode())
                    time.sleep(SCAN_INTERVAL)
        except Exception as e:
            print(f"[!] Connection error: {e}. Retrying in 5 seconds...")
            time.sleep(5)

if __name__ == "__main__":
    print("="*40)
    print(" RPI NEIGHBOR COLLECTOR STARTING")
    print("="*40)
    sender_thread()
