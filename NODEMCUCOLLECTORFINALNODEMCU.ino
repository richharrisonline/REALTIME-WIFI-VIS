/**
 * @file ESP8266_Hub_Collector.ino
 * @author richharrisonline
 * @brief Central Data Collector using ESP-NOW and WiFi Scanning.
 * * This sketch performs two main roles:
 * 1. Listening: Receives RSSI and MAC data from peripheral nodes via ESP-NOW.
 * 2. Scanning: Locally scans for a specific "targetSSID" to measure its own proximity.
 * 3. Reporting: Aggregates all data into a CSV-formatted string sent over Serial 
 * to a Python dashboard or processing unit.
 */

#include <ESP8266WiFi.h>
#include <espnow.h>

// ────────────────────────────────────────────────
// CONFIGURATION
// ────────────────────────────────────────────────

// The SSID this hub will specifically look for to measure its own distance
const char* targetSSID = "XXX"; 

/**
 * @brief Data structure for incoming ESP-NOW messages.
 * Must match the structure used by transmitter nodes exactly.
 */
typedef struct struct_message {
    int id;           // Node Identifier (e.g., 2 through 10)
    int rssi;         // Signal strength recorded by the remote node
    char mac[18];     // MAC address of the remote node
} struct_message;

struct_message incoming;
int nodeSignals[11];  // Stores signal strengths for up to 10 nodes
String nodeMacs[11];   // Stores MAC addresses for up to 10 nodes

/**
 * @brief Callback function triggered when data is received via ESP-NOW.
 * * @param mac_addr MAC address of the sender
 * @param incomingData Pointer to the received data buffer
 * @param len Length of received data
 */
void OnDataRecv(u8 *mac_addr, u8 *incomingData, u8 len) {
    memcpy(&incoming, incomingData, sizeof(incoming));
    
    // Filter for valid node IDs (IDs 2-10 are reserved for remote nodes)
    if (incoming.id >= 2 && incoming.id <= 10) {
        if (incoming.rssi < 0) {
            nodeSignals[incoming.id] = incoming.rssi;
            nodeMacs[incoming.id] = String(incoming.mac);
        }
    }
}

void setup() {
    Serial.begin(115200);
    
    // Initialize WiFi in Station mode and disconnect from AP to allow scanning
    WiFi.mode(WIFI_STA);
    WiFi.disconnect();

    // Initialize ESP-NOW protocol
    if (esp_now_init() != 0) {
        Serial.println("Error initializing ESP-NOW");
        return;
    }

    // Set role to COMBO (Receiver + potential Transmitter)
    esp_now_set_self_role(ESP_NOW_ROLE_COMBO);
    
    // Register the receive callback function
    esp_now_register_recv_cb((esp_now_recv_cb_t)OnDataRecv);

    // Initialize data arrays with default "offline" values
    for(int i=0; i<=10; i++) { 
        nodeSignals[i] = -100; 
        nodeMacs[i] = "00:00:00:00:00:00"; 
    }
    
    Serial.println("Hub Setup Complete. Awaiting Node Data...");
}

void loop() {
    // 1. SCAN FOR THE SPECIFIC TARGET SSID
    // This measures the Hub's own distance to the target network
    int baseRSSI = -100;
    
    // Scan locally available networks (Blocking scan)
    int n = WiFi.scanNetworks(false, false); 
    
    for (int i = 0; i < n; ++i) {
        if (WiFi.SSID(i) == targetSSID) {
            baseRSSI = WiFi.RSSI(i);
            break; 
        }
    }
    // Clean up scan results from memory
    WiFi.scanDelete();

    // 2. CONSTRUCT DATA STRING (CSV Format)
    // Format: DATA,Node1_RSSI,Node1_MAC,Node2_RSSI,Node2_MAC...
    String output = "DATA";
    for (int i = 1; i <= 10; i++) {
        output += ",";
        if (i == 1) {
            // Node 1 is the Hub itself
            output += String(baseRSSI) + "," + WiFi.macAddress();
        } else {
            // Nodes 2-10 are the remote ESP-NOW units
            output += String(nodeSignals[i]) + "," + nodeMacs[i];
        }
    }

    // 3. PUSH TO SERIAL BUS
    // The Python dashboard reads this line to update the heatmap
    Serial.println(output);
    
    // Small delay to prevent Serial buffer overflow and allow radio breathing room
    delay(100); 
}
