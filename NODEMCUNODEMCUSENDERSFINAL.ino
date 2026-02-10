#include <ESP8266WiFi.h>
#include <espnow.h>

// ────────────────────────────────────────────────
// CONFIGURATION
// ────────────────────────────────────────────────
const int NODE_ID = 9; // <--- CHANGE TO 2, 3, 4, etc.
uint8_t collectorMAC[] = {0x00, 0x00, 0x00, 0x00, 0x00, 0x00};  // <--- PUT ESP32 MAC HERE

typedef struct struct_message {
    int id;
    int rssi;
    char mac[18];
} struct_message;

struct_message myData;

void setup() {
    Serial.begin(115200);
    WiFi.mode(WIFI_STA);
    WiFi.disconnect(); // Must be disconnected for clean RSSI scanning

    if (esp_now_init() != 0) return;

    esp_now_set_self_role(ESP_NOW_ROLE_CONTROLLER);
    esp_now_add_peer(collectorMAC, ESP_NOW_ROLE_SLAVE, 1, NULL, 0);
}

void loop() {
    // Force a scan to get a real dBm value instead of "31"
    int n = WiFi.scanNetworks(false, false);
    int strongestRSSI = -100;
    
    if (n > 0) {
        strongestRSSI = WiFi.RSSI(0); // Get strongest nearby AP
    }

    myData.id = NODE_ID;
    myData.rssi = strongestRSSI;
    WiFi.macAddress().toCharArray(myData.mac, 18);

    esp_now_send(collectorMAC, (uint8_t *) &myData, sizeof(myData));
    
    Serial.printf("Node %d sending RSSI: % d\n", NODE_ID, strongestRSSI);
    delay(1000); 
}