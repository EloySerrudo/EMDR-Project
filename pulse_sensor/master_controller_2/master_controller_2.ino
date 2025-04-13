/*
 * ESP32 Coordinador para coordinar la comunicación entre el controlador y la lightbar
 * Y los otros dispositivos.
 */

 #include <esp_now.h>
 #include <WiFi.h>
 
 // Direcciones MAC de los dispositivos esclavos
 uint8_t slaveAddresses[][6] = {
     {0xA0, 0xB7, 0x65, 0x55, 0xF3, 0x30}, // MAC del ESP32 sensor de señales. DEVICE_ID: 1
     {0xA0, 0xA3, 0xB3, 0xAA, 0x33, 0xA4}  // MAC del ESP32 de la lightbar. DEVICE_ID: 2
     // Añadir más dispositivos aquí cuando sea necesario
 };
 
 // Estructura para enviar los datos a través de ESP-NOW
 typedef struct {
   char cmd;
   uint8_t data1;
   uint8_t data2;
   uint8_t data3;
 } CommandPacket;
 
 // Variable para almacenar información de envío
 esp_now_peer_info_t peerInfo;
 
 void setup() {
   // Iniciar comunicación serial con la computadora
   Serial.begin(115200);
   
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
   esp_now_register_send_cb(OnDataSent);
   
   // Identificación del dispositivo
   Serial.println("EMDR Master Controller");
 }
 
 // Callback cuando los datos son enviados
 void OnDataSent(const uint8_t *mac_addr, esp_now_send_status_t status) {
   // Podríamos monitorear el estado de envío si fuera necesario
 }
 
 void loop() {
   // Usar un buffer para los 4 bytes (comando + datos)
   uint8_t packetBuffer[4];
   CommandPacket commandToSend;
   
   // Verificar si hay al menos 4 bytes disponibles
   if (Serial.available() >= 4) {
     // Leer el paquete completo de 4 bytes
     if (Serial.readBytes(packetBuffer, 4) == 4) {
       // Llenar la estructura para enviar
       commandToSend.cmd = packetBuffer[0];
       commandToSend.data1 = packetBuffer[1];
       commandToSend.data2 = packetBuffer[2];
       commandToSend.data3 = packetBuffer[3];
       
       // Enviar el paquete mediante ESP-NOW
       esp_err_t result = esp_now_send(slaveAddresses[1], (uint8_t *)&commandToSend, sizeof(CommandPacket));
       
       // Si el comando es 'i', responder directamente
       if (commandToSend.cmd == 'i') {
         Serial.println("EMDR Lightbar");
       }
     }
   }
 }