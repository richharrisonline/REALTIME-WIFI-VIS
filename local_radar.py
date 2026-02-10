import serial, time, json, os, socket, threading, re
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Button
from scipy.ndimage import gaussian_filter
from PIL import Image
from datetime import datetime

# ────────────────────────────────────────────────
# CONFIGURATION
# ────────────────────────────────────────────────
PORT = '/dev/ttyUSB0'          
BAUD = 115200
SERVER_PORT = 65432            
POS_FILE = 'node_positions.json'
IMG_FILE = 'floorplan.png'
MAX_NODES = 24                 
N_NODES = MAX_NODES + 1
TIMEOUT_SEC = 30.0
EMA_ALPHA = 0.18
GRID_DECAY = 0.96
RPIBASE_FALLBACK = "RPIBASE"
MCUBASE_NAME = "MCUBASE"

raw_log = []
node_ssids = {i: "" for i in range(N_NODES)} 
node_macs = {i: "" for i in range(N_NODES)} 
custom_names = {i: None for i in range(N_NODES)}
mac_to_slot = {} 

MAC_REGEX = re.compile(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$')

if os.path.exists(IMG_FILE):
    with Image.open(IMG_FILE) as img_ref:
        img_w, img_h = img_ref.size
        VIEW_LIMIT_X, VIEW_LIMIT_Y = img_w, img_h
        FIG_W, FIG_H = 12, (img_h / img_w) * 12 if img_w > 0 else 9
        img_data = np.array(img_ref)
else:
    VIEW_LIMIT_X, VIEW_LIMIT_Y, FIG_W, FIG_H = 800, 600, 12, 9
    img_data = None

signals = [-100.0] * N_NODES
signal_smoothed = [-100.0] * N_NODES
last_update = [0.0] * N_NODES

def load_positions_and_names():
    global custom_names
    if os.path.exists(POS_FILE):
        try:
            with open(POS_FILE, 'r') as f:
                data = json.load(f)
                pos = np.array(data.get('fixed', []))
                if len(pos) < N_NODES:
                    extra = np.array([[VIEW_LIMIT_X/2, VIEW_LIMIT_Y/2] for _ in range(N_NODES - len(pos))])
                    pos = np.vstack([pos, extra])
                names_dict = data.get('names', {})
                for k, v in names_dict.items():
                    if int(k) < N_NODES: custom_names[int(k)] = v
                return pos[:N_NODES]
        except: pass
    return np.array([[(i % 4) * (VIEW_LIMIT_X//5) + 100, (i // 4) * (VIEW_LIMIT_Y//5) + 100] for i in range(N_NODES)], dtype=float)

node_coords = load_positions_and_names()

def save_positions_and_names():
    data = {'fixed': node_coords.tolist(), 'names': {str(k): v for k, v in custom_names.items() if v is not None}}
    with open(POS_FILE, 'w') as f: json.dump(data, f, indent=2)

# ────────────────────────────────────────────────
# TCP SERVER
# ────────────────────────────────────────────────
net_status = "DISCONNECTED"

def network_listener():
    global signals, last_update, net_status, node_ssids, node_macs, raw_log, mac_to_slot
    host = '0.0.0.0' 
    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((host, SERVER_PORT))
                s.listen(1)
                net_status = "LISTENING"
                conn, addr = s.accept()
                with conn:
                    net_status = "CONNECTED"
                    while True:
                        data = conn.recv(4096).decode('utf-8', errors='ignore')
                        if not data: break
                        for line in data.strip().split('\n'):
                            if "DATA" in line:
                                raw_log.append(f"NET: {line}")
                                parts = [p.strip() for p in line.split(',')]
                                next_available_slot = 11
                                i, is_first_signal = 1, True 
                                while i < len(parts):
                                    try:
                                        val = parts[i]
                                        if val.startswith('-') and (val[1:].isdigit() or val[1:].replace('.','',1).isdigit()):
                                            current_rssi, current_ssid, current_mac = float(val), "", ""
                                            if i + 1 < len(parts):
                                                if MAC_REGEX.match(parts[i+1]):
                                                    current_mac = parts[i+1]
                                                    i += 1 
                                                else:
                                                    current_ssid = parts[i+1]
                                                    i += 1
                                                    if i + 1 < len(parts) and MAC_REGEX.match(parts[i+1]):
                                                        current_mac = parts[i+1]
                                                        i += 1
                                            if is_first_signal: target_idx, is_first_signal = 0, False
                                            else:
                                                if current_mac and current_mac in mac_to_slot: target_idx = mac_to_slot[current_mac]
                                                else:
                                                    while next_available_slot < N_NODES and (time.time() - last_update[next_available_slot] <= TIMEOUT_SEC): next_available_slot += 1
                                                    target_idx = next_available_slot
                                                    if current_mac: mac_to_slot[current_mac] = target_idx
                                                    next_available_slot += 1
                                            if target_idx < N_NODES:
                                                signals[target_idx] = current_rssi
                                                if current_ssid: node_ssids[target_idx] = current_ssid
                                                if current_mac: node_macs[target_idx] = current_mac
                                                last_update[target_idx] = time.time()
                                    except: pass
                                    i += 1
        except: net_status = "ERR"; time.sleep(2)

threading.Thread(target=network_listener, daemon=True).start()

# ────────────────────────────────────────────────
# SERIAL & UI SETUP
# ────────────────────────────────────────────────
def connect_serial():
    try:
        s = serial.Serial(PORT, BAUD, timeout=0.1)
        s.dtr, s.rts = False, False
        return s, "USB OK"
    except: return None, "USB FAIL"

ser, serial_status = connect_serial()

fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))
plt.subplots_adjust(left=0.01, right=0.99, top=0.92, bottom=0.06)
fig.patch.set_facecolor('#FFFFFF')

if img_data is not None:
    ax.imshow(img_data, extent=[0, VIEW_LIMIT_X, 0, VIEW_LIMIT_Y], alpha=1.0, zorder=0)

current_scene_idx = 0
last_scene_idx = 0 # Track scene changes for hard cut-off
contour_objs = []
node_scatter = ax.scatter([], [], s=15, c='black', edgecolors='none', zorder=60, animated=True)
texts = [ax.text(0, 0, '', fontsize=6, color='black', ha='center', va='top', zorder=61, animated=True) for _ in range(N_NODES)]
bottom_header = fig.text(0.02, 0.02, "", fontsize=6, color='black', family='monospace')

debug_console = ax.text(0.01, 0.06, "", transform=ax.transAxes, fontsize=5, color='black',
                        family='monospace', va='bottom', zorder=100, wrap=False,
                        bbox=dict(facecolor='white', alpha=0.9, edgecolor='none'), animated=True)

ax_btn = plt.axes([0.45, 0.01, 0.1, 0.03], frameon=False)
btn_scene = Button(ax_btn, 'TOGGLE SCENE', color='#EEEEEE', hovercolor='skyblue')
btn_scene.label.set_fontsize(6)
btn_scene.on_clicked(lambda e: globals().update(current_scene_idx=(current_scene_idx + 1) % 4))

grid_usb, grid_rpi = None, None

def update(frame):
    global signals, signal_smoothed, last_update, contour_objs, ser, grid_usb, grid_rpi, serial_status, raw_log, last_scene_idx
    now = time.time()
    
    # HARD CUT-OFF LOGIC: Detect scene change
    scene_changed = (current_scene_idx != last_scene_idx)
    last_scene_idx = current_scene_idx

    base_title = "REALTIME WIFI VIS (ESP8266/WIFI)"
    bottom_header.set_text(f"{base_title} | SERIAL: {serial_status} | TCP: {net_status} | {datetime.now().strftime('%H:%M:%S')}")

    if ser and ser.is_open:
        try:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if "DATA" in line:
                    raw_log.append(f"USB: {line}")
                    parts = [p.strip() for p in line.split(',')]
                    idx = 1
                    for p_idx, part in enumerate(parts):
                        if part.startswith('-') and part[1:].isdigit():
                            if idx <= 10:
                                signals[idx] = float(part)
                                last_update[idx] = now
                                if p_idx + 1 < len(parts) and MAC_REGEX.match(parts[p_idx+1]):
                                    node_macs[idx] = parts[p_idx+1]
                                idx += 1
        except: ser = None; serial_status = "FAIL"
    else: ser, serial_status = connect_serial()

    for i in range(N_NODES):
        if (now - last_update[i]) > TIMEOUT_SEC: signals[i] = -100.0
        target = signals[i] if signals[i] > -99 else -100.0
        alpha = (EMA_ALPHA * 2.5) if i <= 1 else EMA_ALPHA
        signal_smoothed[i] += alpha * (target - signal_smoothed[i])

    ds = 8
    gx, gy = int(VIEW_LIMIT_X // ds), int(VIEW_LIMIT_Y // ds)
    if grid_usb is None: 
        grid_usb, grid_rpi = np.zeros((gy, gx)), np.zeros((gy, gx))
    
    # Apply fade only if scene didn't just change; otherwise, hard reset
    if scene_changed:
        grid_usb.fill(0)
        grid_rpi.fill(0)
    else:
        grid_usb *= GRID_DECAY
        grid_rpi *= GRID_DECAY

    active_coords = []
    for i in range(N_NODES):
        s_val = signal_smoothed[i]
        is_rpi = (i >= 11 or i == 0)
        
        # Immediate visibility cut-off logic
        visible = not (current_scene_idx == 1 and is_rpi) and not (current_scene_idx == 2 and not is_rpi)
        if s_val <= -94 or not visible:
            texts[i].set_visible(False)
            continue

        x, y = node_coords[i]
        active_coords.append([x, y])
        intensity = np.clip((s_val + 95) / 60, 0, 1.0)
        ix, iy = int(x // ds), int(y // ds)
        if 0 <= ix < gx and 0 <= iy < gy:
            r = 15
            sy, sx = slice(max(0, iy-r), iy+r), slice(max(0, ix-r), ix+r)
            if is_rpi: grid_rpi[sy, sx] = np.maximum(grid_rpi[sy, sx], intensity)
            else: grid_usb[sy, sx] = np.maximum(grid_usb[sy, sx], intensity)

        if i == 0: name = node_ssids[0] if node_ssids[0] else RPIBASE_FALLBACK
        elif i == 1: name = MCUBASE_NAME
        elif i >= 11: name = node_ssids[i] if node_ssids[i] else f"R{i-10}"
        else: name = custom_names[i] if custom_names[i] else f"N{i}"
        
        label = f"{name}\n{int(s_val)} dB"
        if current_scene_idx == 3 and node_macs[i]: 
            label += f"\n[{node_macs[i]}]"
            
        texts[i].set_text(label)
        texts[i].set_position((x, y-5))
        texts[i].set_visible(True)

    node_scatter.set_offsets(active_coords if active_coords else [[-1000,-1000]])
    for obj in contour_objs: obj.remove()
    contour_objs.clear()

    if current_scene_idx != 3:
        X, Y = np.linspace(0, VIEW_LIMIT_X, gx), np.linspace(0, VIEW_LIMIT_Y, gy)
        if np.max(grid_usb) > 0.05:
            contour_objs.append(ax.contourf(X, Y, gaussian_filter(grid_usb, 8), levels=8, cmap='Blues', alpha=0.3, zorder=10))
        if np.max(grid_rpi) > 0.05:
            contour_objs.append(ax.contourf(X, Y, gaussian_filter(grid_rpi, 8), levels=8, cmap='Greens', alpha=0.45, zorder=11))

    if current_scene_idx == 3:
        debug_console.set_text("DEBUG LOG (SCENE 4):\n" + "\n".join(raw_log[-12:]))
        debug_console.set_visible(True)
    else: debug_console.set_visible(False)

    return [node_scatter, debug_console] + texts + contour_objs

dragging_node = None
def on_press(event):
    global dragging_node
    if event.inaxes == ax and event.xdata:
        dists = np.sqrt((node_coords[:,0]-event.xdata)**2 + (node_coords[:,1]-event.ydata)**2)
        if np.min(dists) < 40: dragging_node = np.argmin(dists)

fig.canvas.mpl_connect('button_press_event', on_press)
fig.canvas.mpl_connect('button_release_event', lambda e: (save_positions_and_names(), globals().update(dragging_node=None)) if dragging_node is not None else None)
fig.canvas.mpl_connect('motion_notify_event', lambda e: node_coords.__setitem__(dragging_node, [e.xdata, e.ydata]) if dragging_node is not None and e.inaxes==ax else None)

ax.set_xlim(0, VIEW_LIMIT_X); ax.set_ylim(0, VIEW_LIMIT_Y); ax.axis('off')
ani = FuncAnimation(fig, update, interval=50, blit=True, cache_frame_data=False)
plt.show()
