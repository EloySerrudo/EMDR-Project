/*
 * ESP32 Coordinador para coordinar la comunicación entre el controlador y la lightbar
 * Y los otros dispositivos.
 */

#include <WiFi.h>
#include <esp_now.h>
#include <esp_system.h>

// Configuración de LED y botones
#define STATUS_LED 22  // LED integrado del ESP32

// Direcciones MAC de los dispositivos esclavos
uint8_t slaveAddresses[][6] = {
  { 0xA0, 0xB7, 0x65, 0x55, 0xF3, 0x30 },  // MAC del ESP32 sensor de señales. DEVICE_ID: 1
  { 0xA0, 0xA3, 0xB3, 0xAA, 0x33, 0xA4 }   // MAC del ESP32 de la lightbar. DEVICE_ID: 2
  // Añadir más dispositivos aquí cuando sea necesario
};

#define NUM_SLAVES (sizeof(slaveAddresses) / sizeof(slaveAddresses[0]))

// Control de estado de los esclavos
bool slaveConnected[NUM_SLAVES] = { false };

// Variables de estado
volatile bool lastCommandSent = true;

// Variable para almacenar información de envío
esp_now_peer_info_t peerInfo;

// Estructura para enviar los datos a través de ESP-NOW
typedef struct slave_command {
  char cmd;
  uint8_t data1;
  uint8_t data2;
  uint8_t data3;
} slave_command_t;

// Estructura para recibir confirmación
typedef struct ack_packet {
  uint8_t command;
  uint8_t device_id;
  uint8_t status;
} ack_packet_t;

// Función para enviar comandos a los esclavos
void sendCommandToSlave(uint8_t slaveIndex, char cmd, uint8_t data1, uint8_t data2, uint8_t data3) {
  // Verificar que el índice del esclavo sea válido
  if (slaveIndex >= NUM_SLAVES) return;
  // Llenar la estructura para enviar
  slave_command_t commandToSend;
  commandToSend.cmd = cmd;
  commandToSend.data1 = data1;
  commandToSend.data2 = data2;
  commandToSend.data3 = data3;
  
  esp_now_send(slaveAddresses[slaveIndex], (uint8_t *)&commandToSend, sizeof(slave_command_t));
}

// Función para verificar la conexión de todos los esclavos
void checkSlaveConnections() {
  // Reiniciar estado de conexión
  for (int i = 0; i < NUM_SLAVES; i++) {
    slaveConnected[i] = false;
  }

  // Enviar comando de verificación a cada esclavo
  for (int i = 0; i < NUM_SLAVES; i++) {
    sendCommandToSlave(i, 'a', 0, 0, 0);
    delay(50);
  }

  // Esperar respuestas
  delay(500);

  // Enviar resultado al PC
  Serial.write('!');
  Serial.write('C');

  for (int i = 0; i < NUM_SLAVES; i++) {
    Serial.write(i + 1);
    Serial.write(slaveConnected[i] ? 1 : 0);
  }
}

// Callback cuando los datos son enviados
void onSentEspNowData(const uint8_t *mac_addr, esp_now_send_status_t status) {
  // Podríamos monitorear el estado de envío si fuera necesario
  lastCommandSent = (status == ESP_NOW_SEND_SUCCESS);
}

// Callback cuando se reciben datos
void onReceivedEspNowData(const uint8_t *mac_addr, const uint8_t *data, int data_len) {
  // 2. Verificar si es una confirmación de conexión
  if (data_len == sizeof(ack_packet_t)) {
    ack_packet_t *ackPacket = (ack_packet_t *)data;
    if (ackPacket->command == 'A') {
      uint8_t deviceId = ackPacket->device_id;

      // Buscar a qué dispositivo pertenece esta confirmación
      for (int i = 0; i < NUM_SLAVES; i++) {
        if (memcmp(mac_addr, slaveAddresses[i], 6) == 0) {
          slaveConnected[i] = true;
          break;
        }
      }
    }
  }
}

void setup() {
  // Iniciar comunicación serial con la computadora
  Serial.begin(115200);
  delay(1000);

  // Configurar LED
  pinMode(STATUS_LED, OUTPUT);
  digitalWrite(STATUS_LED, HIGH);  // En el WEMOS LOLIN32 Lite este led actua con lógica inversa

  // Inicializar WiFi en modo estación
  WiFi.mode(WIFI_STA);

  // Inicializar ESP-NOW
  if (esp_now_init() != ESP_OK) {
    Serial.println("Error initializing ESP-NOW");
    return;
  }

  // Registrar el receptor
  memcpy(peerInfo.peer_addr, slaveAddresses[1], 6);
  peerInfo.channel = 0;
  peerInfo.encrypt = false;

  // Añadir peer
  if (esp_now_add_peer(&peerInfo) != ESP_OK) {
    Serial.println("Failed to add peer");
    return;
  }

  // Registrar la función de callback para saber el estado del envío
  esp_now_register_recv_cb(onReceivedEspNowData);
  esp_now_register_send_cb(onSentEspNowData);

  // Identificación del dispositivo
  Serial.println("EMDR Master Controller");
}

void loop() {
  // Verificar si hay al menos 4 bytes disponibles
  if (Serial.available() >= 4) {
    // Usar un buffer para los 4 bytes (comando + datos)
    uint8_t packetBuffer[4];
    // Leer el paquete completo de 4 bytes
    if (Serial.readBytes(packetBuffer, 4) == 4) {
      // Si el comando es 'i', responder directamente
      if (packetBuffer[0] == 'i') {
        Serial.println("EMDR Master Controller");
      } else if (packetBuffer[0] == 'A') {
        checkSlaveConnections();
      } else {
        // Enviar el paquete mediante ESP-NOW
        sendCommandToSlave(1, packetBuffer[0], packetBuffer[1], packetBuffer[2], packetBuffer[3]);
      }
    }
  }
}