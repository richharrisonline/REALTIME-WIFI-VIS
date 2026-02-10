Realtime WIFI Visualization with ESP32/ESP8266/WIFI
-------
A realtime WIFI heatmap that can display 2.4 GHz Wi-Fi, ESP32 or ESP8266 "nodes". A "collector" NODEMCU ESP8266 collects signal strength from "sender" NODEMCUs/RPI and displays it ontop of your floorplan.png. Monitor your Wi-Fi signals visualy in real time with this wireless heatmap tool. (can be used to optimize and analyze wireless network coverage) Click and drag nodes around on top of a floorplan image for visualization of Wi-Fi signals, change the "floorplan.png" to your custom image.

FILES: 
ESP32HOTSPOTS.ino - Create multiple WIFI hotspots for testing.
NODEMCUCOLLECTORFINALNODEMCU.ino - Collect node info from "sender" ESP32 devices. (example configured for NODEMCU ESP8266 boards)
NODEMCUNODEMCUSENDERSFINAL.ino - Send node info to the "collector" ESP32 device. (example configured for NODEMCU ESP8266 boards)
local_radar.py - Main "dashboard" compiles the node info from the "collector" and displays them on top of the heatmap.
rpisender.py - Scans Wi-Fi networks and sends node info to the dashboard.
floorplan.png - Change this file to add your own custom floorplan.
SCREENSHOT.png - Screenshot of the current version.

CHANGES TO COME - make it easier to upload floorplan file, add nodes from the dashboard interface, add and edit nodes directly from the dashboard, change heatmap "blob" size and accuracy.

Clean interface, realtime monitor, created on Ubuntu with the help of AI. 
This is my first GITHUB submission, open source project.. feel free to modify or change anything.

Have fun.

cd ~/YOURFOLDER

source venv/bin/activate

sudo chmod 666 /dev/ttyUSB0

python local_radar.py
