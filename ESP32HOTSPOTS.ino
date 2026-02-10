#include <WiFi.h>

// Configuration for multiple hotspot "Profiles"
const char* ssid_1 = "ESP32_Secure_Zone";
const char* password_1 = "123456789";

const char* ssid_2 = "Guest_Proximity_Node";
const char* password_2 = NULL; // Open network

void setup() {
  Serial.begin(115200);
  
  // 1. Set Wi-Fi to Access Point mode
  WiFi.mode(WIFI_AP);

  // 2. Start the first Hotspot
  // softAP(ssid, password, channel, ssid_hidden, max_connection)
  bool success = WiFi.softAP(ssid_1, password_1, 1, 0, 4);
  
  if (success) {
    Serial.println("Hotspot 1 Started Successfully");
    Serial.print("IP Address: ");
    Serial.println(WiFi.softAPIP());
  } else {
    Serial.println("Hotspot 1 Failed to Start");
  }

  // Note: Standard ESP32 Arduino core supports one active SoftAP SSID at a time.
  // To "see" multiple, you would typically cycle them or use an ESP-IDF 
  // implementation for multiple VAPs (Virtual APs).
}

void loop() {
  // Print number of connected stations
  Serial.printf("Stations connected to AP: %d\n", WiFi.softAPgetStationNum());
  
  delay(5000); 
}