#include <esp_now.h>
#include <WiFi.h>

// Identificador único de este dispositivo
#define DEVICE_ID 3 // EMDR Buzzer

#define R_PIN 25
#define L_PIN 26
#define STATUS_LED 4  // LED para indicar estado

// Estructura para recibir los datos a través de ESP-NOW
typedef struct {
  char cmd;
  uint8_t data1;
  uint8_t data2;
  uint8_t data3;
} CommandPacket;

// Estructura para enviar confirmación al maestro
typedef struct ack_packet {
    uint8_t command;    // 'A': acknowledge
    uint8_t device_id;  // ID del dispositivo que responde
    uint8_t status;     // Estado del dispositivo
} ack_packet_t;

// Información del peer para ESP-NOW
esp_now_peer_info_t peerInfo;

// MAC del dispositivo maestro
uint8_t masterAddress[] = {0x78, 0x21, 0x84, 0x79, 0x66, 0xD0};  // Reemplazar con la MAC real del maestro

// Variables para el último estado de envío ESP-NOW
volatile bool lastSendStatus = true;

void buzz(uint8_t pin, uint16_t duration_ms) {
  digitalWrite(pin, HIGH);
  delay(duration_ms);
  digitalWrite(pin, LOW);
}

void test() {
  buzz(L_PIN, 50);
  delay(1000);
  buzz(R_PIN, 50);
}

// Callback cuando se envían datos
void OnDataSent(const uint8_t *mac_addr, esp_now_send_status_t status) {
  lastSendStatus = (status == ESP_NOW_SEND_SUCCESS);
  // Parpadear LED para indicar envío exitoso
  if (status == ESP_NOW_SEND_SUCCESS) {
    digitalWrite(STATUS_LED, HIGH);
    delay(10);
    digitalWrite(STATUS_LED, LOW);
  }
}

// Callback para cuando se reciben datos
void OnDataRecv(const uint8_t *mac, const uint8_t *incomingData, int data_len) {
  // Procesar el comando recibido
  if (data_len == sizeof(CommandPacket)) {
    CommandPacket cmd;
    memcpy(&cmd, incomingData, sizeof(cmd));

    // Convertir comando a minúsculas para procesar tanto mayúsculas como minúsculas
    char command = tolower(cmd.cmd);
    
    switch (command) {
      case 'l':  // Comando buzzer izquierdo
        // data1 contiene la duración
        buzz(L_PIN, cmd.data1);
        break;

      case 'r':  // Comando buzzer derecho
        // data1 contiene la duración
        buzz(R_PIN, cmd.data1);
        break;

      case 'b':  // Comando test de ambos buzzer
        buzz(L_PIN, cmd.data1);
        delay(100);
        buzz(R_PIN, cmd.data1);
        break;
        
      case 'a': // Comando acknowledge (acepta 'a' o 'A')
        // Preparar respuesta
        ack_packet_t response;
        response.command = 'A';  // Acknowledge
        response.device_id = DEVICE_ID;  // Usar el ID definido
        response.status = 1;     // 1 = OK
            
        // Enviar respuesta al maestro
        esp_err_t result = esp_now_send(masterAddress, 
                                        (uint8_t *) &response, 
                                        sizeof(response));
        if (result == ESP_OK) {
          // Parpadear LED para indicar que respondimos
          digitalWrite(STATUS_LED, HIGH);
          delay(50);
          digitalWrite(STATUS_LED, LOW);
        }
        break;
    }
  }
}

void setup() {
  // Inicializar Serial (para debugging)
  Serial.begin(115200);
  delay(1000);
  
  // Configurar pines
  pinMode(L_PIN, OUTPUT);
  pinMode(R_PIN, OUTPUT);
  pinMode(STATUS_LED, OUTPUT);
  
  digitalWrite(L_PIN, LOW);
  digitalWrite(R_PIN, LOW);
  digitalWrite(STATUS_LED, LOW);

  // Inicializar WiFi en modo estación
  WiFi.mode(WIFI_STA);

  // Inicializar ESP-NOW
  if (esp_now_init() != ESP_OK) {
    digitalWrite(STATUS_LED, HIGH);  // Indicar error
    Serial.println("Error initializing ESP-NOW");
    return;
  }

  // Registrar callback para envío y recepción de datos
  esp_now_register_recv_cb(OnDataRecv);
  esp_now_register_send_cb(OnDataSent);
  
  // Registrar maestro como peer
  memcpy(peerInfo.peer_addr, masterAddress, 6);
  peerInfo.channel = 0;  
  peerInfo.encrypt = false;
  
  // Añadir peer
  if (esp_now_add_peer(&peerInfo) != ESP_OK) {
    Serial.println("Failed to add peer");
    return;
  }
  
  // Indicar inicialización correcta
  digitalWrite(STATUS_LED, HIGH);
  delay(500);
  digitalWrite(STATUS_LED, LOW);

  // Ejecutar secuencia de prueba
  test();
  
  Serial.println("EMDR Buzzer ready with ESP-NOW");
}

void loop() {
  // El loop queda vacío porque todo se maneja mediante callbacks
  // delay(100);
}