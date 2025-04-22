/*
 * ESP32 Coordinador para coordinar la comunicación entre el controlador y la lightbar
 * Y los otros dispositivos.
 */

 #include <WiFi.h>
 #include <esp_now.h>
 #include <esp_system.h>
 
 // Configuración de LED y botones
 #define STATUS_LED 22         // LED integrado del ESP32
 #define PACKET_HEADER 0xAA55  // Header para paquetes de datos
 #define PACKET_SIZE 15        // Tamaño del paquete del sensor
 
 // Variables globales
 bool forwarding = true;  // Indicador para reenviar datos al PC
 
 // Direcciones MAC de los dispositivos esclavos
 uint8_t slaveAddresses[][6] = {
   { 0xA0, 0xA3, 0xB3, 0xAA, 0x33, 0xA4 },  // MAC del ESP32 sensor de señales. DEVICE_ID: 1
   { 0xA0, 0xB7, 0x65, 0x55, 0xF3, 0x30 }   // MAC del ESP32 de la lightbar. DEVICE_ID: 2
   // Añadir más dispositivos aquí cuando sea necesario
 };
 
 #define NUM_SLAVES (sizeof(slaveAddresses) / sizeof(slaveAddresses[0]))
 
 // Control de estado de los esclavos
 bool slaveConnected[NUM_SLAVES] = { false };
 
 // Buffer para reensamblar paquetes para serial
 uint8_t serialPacket[PACKET_SIZE];
 
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
 
 // Estructura para recibir datos del sensor
 typedef struct esp_now_packet {
   uint16_t header;
   uint32_t id;
   uint32_t timestamp;
   int16_t value_0;
   int16_t value_1;
   uint8_t device_id;
 } esp_now_packet_t;
 
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
   // 1. Verificar si es un paquete del sensor de pulso
   if (data_len == sizeof(esp_now_packet_t)) {
     esp_now_packet_t *packet = (esp_now_packet_t *)data;
     if (packet->header == PACKET_HEADER && forwarding) {
       // Reenviar datos al PC en formato binario
       serialPacket[0] = PACKET_HEADER & 0xFF;
       serialPacket[1] = (PACKET_HEADER >> 8) & 0xFF;
 
       serialPacket[2] = packet->id & 0xFF;
       serialPacket[3] = (packet->id >> 8) & 0xFF;
       serialPacket[4] = (packet->id >> 16) & 0xFF;
       serialPacket[5] = (packet->id >> 24) & 0xFF;
 
       serialPacket[6] = packet->timestamp & 0xFF;
       serialPacket[7] = (packet->timestamp >> 8) & 0xFF;
       serialPacket[8] = (packet->timestamp >> 16) & 0xFF;
       serialPacket[9] = (packet->timestamp >> 24) & 0xFF;
 
       serialPacket[10] = packet->value_0 & 0xFF;
       serialPacket[11] = (packet->value_0 >> 8) & 0xFF;
 
       serialPacket[12] = packet->value_1 & 0xFF;
       serialPacket[13] = (packet->value_1 >> 8) & 0xFF;
 
       serialPacket[14] = packet->device_id;
 
       Serial.write(serialPacket, PACKET_SIZE);
     }
   }
   // 2. Verificar si es una confirmación de conexión
   else if (data_len == sizeof(ack_packet_t)) {
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
 
   // Registrar todos los dispositivos esclavos como peers
   for (uint8_t i = 0; i < NUM_SLAVES; i++) {
     memcpy(peerInfo.peer_addr, slaveAddresses[i], 6);
     peerInfo.channel = 0;
     peerInfo.encrypt = false;
     // Añadir peer
     esp_now_add_peer(&peerInfo);
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
         sendCommandToSlave(0, packetBuffer[0], packetBuffer[1], packetBuffer[2], packetBuffer[3]);
       }
     }
   }
 }