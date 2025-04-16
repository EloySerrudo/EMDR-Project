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

// Estructura para enviar los datos a través de ESP-NOW
typedef struct lightbar_command {
  char cmd;
  uint8_t data1;
  uint8_t data2;
  uint8_t data3;
} lightbar_command_t;

// Estructura para recibir confirmación
typedef struct ack_packet {
  uint8_t command;
  uint8_t device_id;
  uint8_t status;
} ack_packet_t;

// Variables de estado
volatile bool lastCommandSent = true;

// Variable para almacenar información de envío
esp_now_peer_info_t peerInfo;

// Función para verificar la conexión de todos los esclavos
void checkSlaveConnections() {
  // Reiniciar estado de conexión
  for (int i = 0; i < NUM_SLAVES; i++) {
    slaveConnected[i] = false;
  }

  // Enviar comando de verificación a cada esclavo
  for (int i = 0; i < NUM_SLAVES; i++) {
    if (i == 1) {
      // Para el lightbar
      lightbar_command_t packet;
      packet.cmd = 'a';
      packet.data1 = 0;
      packet.data2 = 0;
      packet.data3 = 0;
      esp_now_send(slaveAddresses[1], (uint8_t *)&packet, sizeof(packet));
    } else {
      // Para el sensor de pulso
      // sendCommandToSlave(i, 'A');
    }
    delay(50);
  }

  // Esperar respuestas
  delay(500);

  // Enviar resultado al PC
  Serial.write('!');
  Serial.write('C');
  Serial.write(NUM_SLAVES);

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
  // Usar un buffer para los 4 bytes (comando + datos)
  uint8_t packetBuffer[4];
  lightbar_command_t commandToSend;

  // Verificar si hay al menos 4 bytes disponibles
  if (Serial.available() >= 4) {
    // Leer el paquete completo de 4 bytes
    if (Serial.readBytes(packetBuffer, 4) == 4) {
      // Llenar la estructura para enviar
      commandToSend.cmd = packetBuffer[0];
      commandToSend.data1 = packetBuffer[1];
      commandToSend.data2 = packetBuffer[2];
      commandToSend.data3 = packetBuffer[3];

      // Si el comando es 'i', responder directamente
      if (commandToSend.cmd == 'i') {
        Serial.println("EMDR Master Controller");
      } else if (commandToSend.cmd == 'A') {
        // Reiniciar estado de conexión
        for (int i = 0; i < NUM_SLAVES; i++) {
          slaveConnected[i] = false;
        }

        esp_err_t result = esp_now_send(slaveAddresses[1], (uint8_t *)&commandToSend, sizeof(lightbar_command_t));
        delay(50);

        // Esperar respuestas
        delay(500);

        // Enviar resultado al PC
        Serial.write('!');
        Serial.write('C');

        for (int i = 0; i < NUM_SLAVES; i++) {
          Serial.write(i + 1);
          Serial.write(slaveConnected[i] ? 1 : 0);
        }
      } else {
        // Enviar el paquete mediante ESP-NOW
        esp_err_t result = esp_now_send(slaveAddresses[1], (uint8_t *)&commandToSend, sizeof(lightbar_command_t));
      }
    }
  }
}