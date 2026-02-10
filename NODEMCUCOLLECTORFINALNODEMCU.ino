#include <ESP8266WiFi.h>
#include <espnow.h>

// ────────────────────────────────────────────────
// CONFIGURATION
// ────────────────────────────────────────────────
const char* targetSSID = "XXX"; 

typedef struct struct_message {
    int id;
    int rssi;
    char mac[18];
} struct_message;

struct_message incoming;
int nodeSignals[11];
String nodeMacs[11];

// Use u8 to match ESP8266 headers exactly
void OnDataRecv(u8 *mac_addr, u8 *incomingData, u8 len) {
    memcpy(&incoming, incomingData, sizeof(incoming));
    if (incoming.id >= 2 && incoming.id <= 10) {
        if (incoming.rssi < 0) {
            nodeSignals[incoming.id] = incoming.rssi;
            nodeMacs[incoming.id] = String(incoming.mac);
        }
    }
}

void setup() {
    Serial.begin(115200);
    
    WiFi.mode(WIFI_STA);
    WiFi.disconnect();

    if (esp_now_init() != 0) {
        Serial.println("Error initializing ESP-NOW");
        return;
    }

    esp_now_set_self_role(ESP_NOW_ROLE_COMBO);
    esp_now_register_recv_cb((esp_now_recv_cb_t)OnDataRecv);

    for(int i=0; i<=10; i++) { 
        nodeSignals[i] = -100; 
        nodeMacs[i] = "00:00:00:00:00:00"; 
    }
}

void loop() {
    // 1. SCAN FOR THE SPECIFIC SSID
    int baseRSSI = -100;
    
    // CORRECTED FOR ESP8266:
    // scanNetworks(bool async, bool show_hidden, uint8 channel, uint8* ssid)
    // We set channel to 0 (all channels) and ssid to NULL (all SSIDs)
    int n = WiFi.scanNetworks(false, false); 
    
    for (int i = 0; i < n; ++i) {
        if (WiFi.SSID(i) == targetSSID) {
            baseRSSI = WiFi.RSSI(i);
            break; 
        }
    }
    WiFi.scanDelete();

    // 2. CONSTRUCT DATA STRING
    String output = "DATA";
    for (int i = 1; i <= 10; i++) {
        output += ",";
        if (i == 1) {
            output += String(baseRSSI) + "," + WiFi.macAddress();
        } else {
            output += String(nodeSignals[i]) + "," + nodeMacs[i];
        }
    }

    // 3. SEND TO DASHBOARD
    Serial.println(output);
    
    delay(100); 
}