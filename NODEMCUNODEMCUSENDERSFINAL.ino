/**
 * @file ESP8266_Satellite_Node.ino
 * @author richharrisonline
 * @brief Satellite Sensor Node for WiFi Tracking System.
 * * ROLE: 
 * This node scans the local area for the strongest WiFi Access Point to determine 
 * its own proximity to a signal source. It then packages its ID, the signal strength (RSSI), 
 * and its MAC address into a struct and transmits it to a Central Hub via ESP-NOW.
 * * SETUP INSTRUCTIONS:
 * 1. Change 'NODE_ID' to a unique number (e.g., 2, 3, 4...) for each satellite.
 * 2. Update 'collectorMAC' with the MAC address of your Central Hub ESP8266/ESP32.
 * 3. Upload to an ESP8266 (NodeMCU, Wemos D1 Mini, etc.).
 */

#include <ESP8266WiFi.h>
#include <espnow.h>

// ────────────────────────────────────────────────
// CONFIGURATION
// ────────────────────────────────────────────────

// 1. UNIQUE IDENTIFIER: Each satellite node needs a different ID (use 2 through 10)
const int NODE_ID = 9; 

// 2. HUB ADDRESS: Replace with the MAC address of your "Collector/Hub" device
// You can find the Hub's MAC by running Serial.println(WiFi.macAddress()) on it.
uint8_t collectorMAC[] = {0x00, 0x00, 0x00, 0x00, 0x00, 0x00}; 

/**
 * @brief Data structure for ESP-NOW messages.
 * MUST be identical to the struct in the Hub/Collector code.
 */
typedef struct struct_message {
    int id;           // Unique ID of this node
    int rssi;         // Measured signal strength in dBm
    char mac[18];     // This node's MAC address
} struct_message;

struct_message myData;

void setup() {
    Serial.begin(115200);
    
    // Set WiFi to Station mode but stay disconnected from any AP
    // This is crucial: the radio must be free to scan and send raw packets
    WiFi.mode(WIFI_STA);
    WiFi.disconnect(); 

    // Initialize ESP-NOW Protocol
    if (esp_now_init() != 0) {
        Serial.println("Error initializing ESP-NOW");
        return;
    }

    // Set role as Controller (Sender)
    esp_now_set_self_role(ESP_NOW_ROLE_CONTROLLER);
    
    // Add the Hub as a "peer" to communicate with it
    // Channel 1 is used here; ensure Hub and Satellites are on the same channel
    esp_now_add_peer(collectorMAC, ESP_NOW_ROLE_SLAVE, 1, NULL, 0);
    
    Serial.printf("Node %d initialized. Ready to transmit.\n", NODE_ID);
}

void loop() {
    // 1. ENVIRONMENT SCAN
    // We trigger a network scan. Even if we don't connect, this populates
    // the internal radio registers with accurate dBm (RSSI) values.
    int n = WiFi.scanNetworks(false, false);
    int strongestRSSI = -100; // Default floor value
    
    if (n > 0) {
        // We take index 0, as scanNetworks sorts results by strength by default
        strongestRSSI = WiFi.RSSI(0); 
    }

    // 2. PREPARE DATA PACKET
    myData.id = NODE_ID;
    myData.rssi = strongestRSSI;
    WiFi.macAddress().toCharArray(myData.mac, 18);

    // 3. TRANSMIT VIA ESP-NOW
    // This is significantly faster and lower power than standard WiFi TCP/UDP
    esp_now_send(collectorMAC, (uint8_t *) &myData, sizeof(myData));
    
    // Log results for local debugging
    Serial.printf("Node %d reporting RSSI: %d dBm to Hub\n", NODE_ID, strongestRSSI);
    
    // Wait 1 second before next scan. Adjust based on how "real-time" you need the heatmap.
    delay(1000); 
}
