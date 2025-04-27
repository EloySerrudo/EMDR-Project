#include <esp_now.h>
#include <WiFi.h>
#include <Adafruit_NeoPixel.h>

// Identificador único de este dispositivo
#define DEVICE_ID 2  // EMDR Lightbar

#define PIN_LED 25     // Pin para controlar el NeoPixel strip
#define STATUS_LED 33  // LED para indicar errores
#define NUMLED 60      // Número de LEDs en la tira

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

// Inicialización de la tira NeoPixel
Adafruit_NeoPixel strip = Adafruit_NeoPixel(NUMLED, PIN_LED, NEO_GRB + NEO_KHZ800);

// Variables para el control de color y LED
uint8_t red = 0x0F;
uint8_t green = 0;
uint8_t blue = 0;

// Variables para el último estado de envío ESP-NOW
volatile bool lastSendStatus = true;

// Dirección MAC del dispositivo maestro
uint8_t masterAddress[] = {0x78, 0x21, 0x84, 0x79, 0x66, 0xD0};  // Reemplazar con la MAC real del maestro

// Función para probar la tira de LEDs al inicio
void test() {
  strip.clear();  // clear LEDs: limpiar todos los LEDs
  strip.setPixelColor(0, strip.Color(0, 0x20, 0));
  strip.setPixelColor(NUMLED - 1, strip.Color(0x20, 0, 0));
  strip.show();
  delay(500);
  strip.clear();
  strip.show();
}

// Callback cuando se envían datos
void OnDataSent(const uint8_t *mac_addr, esp_now_send_status_t status) {
    lastSendStatus = (status == ESP_NOW_SEND_SUCCESS);
}

// Callback para cuando se reciben datos
void OnDataRecv(const uint8_t *mac, const uint8_t *incomingData, int data_len) {
  // Procesar el comando recibido
  if (data_len == sizeof(CommandPacket)) {
    CommandPacket cmd;
    memcpy(&cmd, incomingData, sizeof(cmd));

    uint8_t ledNum;
    // Convertir comando a minúsculas para procesar tanto mayúsculas como minúsculas
    char command = tolower(cmd.cmd);
    
    switch (command) {
      case 'c':  // Comando de color
        // Los 3 bytes siguientes son para RGB
        red = cmd.data1;
        green = cmd.data2;
        blue = cmd.data3;
        break;

      case 'l':  // Comando de LED
        // El segundo byte es para la posición
        ledNum = cmd.data1;

        strip.clear();
        if (ledNum > 0 && ledNum <= NUMLED) {
          strip.setPixelColor(ledNum - 1, strip.Color(red, green, blue));
        }
        strip.show();
        break;

      case 't':  // Comando test
        strip.clear();
        strip.setPixelColor(0, strip.Color(red, green, blue));
        strip.setPixelColor(NUMLED - 1, strip.Color(red, green, blue));
        strip.show();
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
  // Inicialización de la tira NeoPixel
  strip.begin();
  strip.clear();
  strip.show();
  delay(1000);

  // Configuración del pin de status
  pinMode(STATUS_LED, OUTPUT);
  digitalWrite(STATUS_LED, LOW);

  // Inicializar WiFi en modo estación
  WiFi.mode(WIFI_STA);

  // Inicializar ESP-NOW
  if (esp_now_init() != ESP_OK) {
    digitalWrite(STATUS_LED, HIGH);
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
    return;
  }
  // Inicialización correcta
  digitalWrite(STATUS_LED, HIGH);
  delay(500);
  digitalWrite(STATUS_LED, LOW);

  // Mostrar patrón de prueba inicial
  test();
}

void loop() {
  
}
