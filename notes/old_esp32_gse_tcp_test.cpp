#include <ETH.h>
#include <WiFiClient.h>
#include <WiFiServer.h>

// Olimex ESP32-PoE-ISO Ethernet hardware definitions
// Based on LAN8710A PHY operating in RMII mode  with SMI address 0x00.
#define ETH_PHY_ADDR 0
#define ETH_PHY_POWER 12
#define ETH_PHY_MDC 23
#define ETH_PHY_MDIO 18
#define ETH_PHY_TYPE \
  ETH_PHY_LAN8720  // The LAN8710A is perfectly compatible with the standard
                   // LAN8720 driver
#define ETH_CLK_MODE ETH_CLOCK_GPIO17_OUT

#define SERIAL_BAUD 115200

const int TCP_PORT = 5000;
WiFiServer server(TCP_PORT);

// --- Static IP Configuration ---
IPAddress local_IP(192, 168, 0,
                   150);            // The static IP for this specific HIVE node
IPAddress gateway(192, 168, 0, 1);  // Your network router/gateway
IPAddress subnet(255, 255, 255, 0);  // Subnet mask
IPAddress primaryDNS(8, 8, 8, 8);    // Optional: Primary DNS (Google)
IPAddress secondaryDNS(1, 1, 1, 1);  // Optional: Secondary DNS (Cloudflare)

void setup() {
  Serial.begin(SERIAL_BAUD);

  // Wait for serial to connect
  while (!Serial) {
  }

  Serial.println("\n--- Project Horizon: Ethernet TCP Hex Dumper ---");
  Serial.println("Initializing Ethernet PHY...");

  // Start the Ethernet interface using the specific Olimex pinout
  if (!ETH.begin(ETH_PHY_ADDR, ETH_PHY_POWER, ETH_PHY_MDC, ETH_PHY_MDIO,
                 ETH_PHY_TYPE, ETH_CLK_MODE)) {
    Serial.println("Failed to initialize Ethernet!");
    return;
  }

  // Apply the Static IP settings
  if (!ETH.config(local_IP, gateway, subnet, primaryDNS, secondaryDNS)) {
    Serial.println(
        "Warning: Failed to configure Static IP! Falling back to DHCP.");
  } else {
    Serial.println("Static IP configuration applied.");
  }

  // Wait until the board confirms the IP address
  while (ETH.localIP()[0] == 0) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.print("HIVE Telemetry Node IP: ");
  Serial.println(ETH.localIP());

  Serial.println("Ethernet Started. Waiting for DHCP IP address...");

  // Wait until the board gets a valid IP address
  while (ETH.localIP()[0] == 0) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.print("HIVE Telemetry Node IP: ");
  Serial.println(ETH.localIP());

  // Start the TCP Server
  server.begin();
  Serial.printf("Listening for TCP packets on port %d...\n", TCP_PORT);
}

void loop() {
  // Check if a client has connected
  WiFiClient client = server.available();

  if (client) {
    Serial.print("\n[New Connection from ");
    Serial.print(client.remoteIP());
    Serial.println("]");

    // Read and process data while the client remains connected
    while (client.connected()) {
      if (client.available()) {
        int bytesAvailable = client.available();
        uint8_t buffer[128];

        // Read up to 128 bytes at a time
        int bytesRead = client.read(buffer, min(bytesAvailable, 128));

        // Print the payload in HEX format
        for (int i = 0; i < bytesRead; i++) {
          Serial.printf("%02X ", buffer[i]);
        }
      }
    }

    // Formatting break when the connection drops
    Serial.println("\n[Connection Closed]");
    client.stop();
  }
}
