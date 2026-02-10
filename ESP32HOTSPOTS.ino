/**
 * @file ESP32_AccessPoint_Basic.ino
 * @author richharrisonline
 * @brief Demonstrates how to configure an ESP32 as a standalone WiFi Access Point (Hotspot).
 * @version 0.1
 * @date 2026-02-10
 * * @copyright Copyright (c) 2026
 * * INSTRUCTIONS:
 * 1. Open this file in the Arduino IDE.
 * 2. Select your ESP32 board (Tools > Board).
 * 3. Upload the sketch.
 * 4. Open the Serial Monitor (115200 baud) to see the IP address and connection count.
 * 5. Use a smartphone or laptop to scan for the "ESP32_Secure_Zone" network.
 */

#include <WiFi.h>

// ──────────────────────────────────────────────────────────────────────
// CONFIGURATION: Access Point Profiles
// ──────────────────────────────────────────────────────────────────────

// Profile 1: Secure Network
const char* ssid_1     = "ESP32_Secure_Zone";
const char* password_1 = "123456789";  // Minimum 8 characters for WPA2

// Profile 2: Open Network (Example for switching logic)
const char* ssid_2     = "Guest_Proximity_Node";
const char* password_2 = NULL; 

void setup() {
  // Initialize Serial communication for debugging
  Serial.begin(115200);
  delay(1000); // Short delay to allow serial to stabilize
  
  Serial.println("\n--- ESP32 WiFi AP Initializing ---");

  // 1. Set Wi-Fi to Access Point mode explicitly
  // This ensures the device behaves as a hotspot rather than trying to connect to a router.
  WiFi.mode(WIFI_AP);

  // 2. Start the Hotspot
  /**
   * softAP arguments:
   * ssid: The name of your network
   * password: Set to NULL for open network, or 8+ chars for WPA2
   * channel: WiFi channel (1-13)
   * ssid_hidden: 0 = visible, 1 = hidden
   * max_connection: Limits how many devices can connect (standard ESP32 supports up to 4-8)
   */
  bool success = WiFi.softAP(ssid_1, password_1, 1, 0, 4);
  
  if (success) {
    Serial.println("Result: Hotspot Started Successfully");
    Serial.print("SSID: ");
    Serial.println(ssid_1);
    Serial.print("AP IP Address: ");
    Serial.println(WiFi.softAPIP()); // Default is usually 192.168.4.1
  } else {
    Serial.println("Result: Hotspot Failed to Start");
  }

  /* * ARCHITECTURAL NOTE:
   * Standard ESP32 hardware uses a single radio. While you can define multiple 
   * profiles, the hardware typically supports only one active SSID at a time.
   * To implement multiple SSIDs, you would need to implement "SSID Cycling"
   * or use advanced ESP-IDF Virtual AP features.
   */
}

void loop() {
  // Monitor connectivity
  // WiFi.softAPgetStationNum() returns the count of currently connected clients.
  int clients = WiFi.softAPgetStationNum();
  
  Serial.printf("Status Check: %d stations connected\n", clients);
  
  // Wait 5 seconds before next log to avoid spamming the Serial console
  delay(5000); 
}
