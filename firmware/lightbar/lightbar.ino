#include <esp_now.h>
#include <WiFi.h>
#include <Adafruit_NeoPixel.h>

// Identificador único de este dispositivo
#define DEVICE_ID 2  // EMDR Lightbar

#define STATUS_LED 16  // LED para indicar errores
#define NUMLED 58      // Número de LEDs en la tira
#define NUM_STRIPS 3   // Número de tiras LED

// Definición de pines para las tiras LED
const uint8_t LED_PINS[NUM_STRIPS] = {22, 21, 18}; // Pines para las tiras 1, 2 y 3

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

// Inicialización de las tiras NeoPixel como un arreglo
Adafruit_NeoPixel strips[NUM_STRIPS] = {
  Adafruit_NeoPixel(NUMLED, LED_PINS[0], NEO_GRB + NEO_KHZ800),
  Adafruit_NeoPixel(NUMLED, LED_PINS[1], NEO_GRB + NEO_KHZ800),
  Adafruit_NeoPixel(NUMLED, LED_PINS[2], NEO_GRB + NEO_KHZ800)
};

// Índice de la tira LED actualmente activa (0-2)
uint8_t activeStripIndex = 0;

// Variables para el control de color y LED
uint8_t red = 0x0F;
uint8_t green = 0;
uint8_t blue = 0;
uint8_t ledNum;
uint32_t color = strips[activeStripIndex].Color(red, green, blue);

// Variables para el último estado de envío ESP-NOW
volatile bool lastSendStatus = true;

// Dirección MAC del dispositivo maestro
uint8_t masterAddress[] = {0xE4, 0x65, 0xB8, 0xA3, 0x7E, 0x4C};  // Reemplazar con la MAC real del maestro

// Función para cambiar a la siguiente tira
void switchToNextStrip() {
  // Apagar la tira actual
  strips[activeStripIndex].clear();
  strips[activeStripIndex].show();
  
  // Cambiar a la siguiente tira (cíclico: 0->1->2->0...)
  activeStripIndex = (activeStripIndex + 1) % NUM_STRIPS;
  strips[activeStripIndex].setPixelColor(ledNum - 1, color);
  strips[activeStripIndex].show();
  Serial.print("Switched to strip: ");
  Serial.println(activeStripIndex + 1); // Mostrar número de tira (1-based para legibilidad)
}

// Función para probar la tira de LEDs actual
void test() {
  strips[activeStripIndex].clear();
  strips[activeStripIndex].setPixelColor(0, strips[activeStripIndex].Color(0, 0x20, 0));
  strips[activeStripIndex].setPixelColor(NUMLED - 1, strips[activeStripIndex].Color(0x20, 0, 0));
  strips[activeStripIndex].show();
  delay(500);
  strips[activeStripIndex].clear();
  strips[activeStripIndex].show();
}

// Función para probar la tira de LEDs al inicio
void initial_test() {
  for (int i = 0; i < NUM_STRIPS; i++) {
    strips[i].clear();
    strips[i].setPixelColor(0, strips[i].Color(0, 0x20, 0));
    strips[i].setPixelColor(NUMLED - 1, strips[i].Color(0x20, 0, 0));
    strips[i].show();
    delay(500);
    strips[i].clear();
    strips[i].show();
  }
  test()
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

    // Convertir comando a minúsculas para procesar tanto mayúsculas como minúsculas
    char command = tolower(cmd.cmd);
    
    switch (command) {
      case 'c':  // Comando de color
        // Los 3 bytes siguientes son para RGB
        red = cmd.data1;
        green = cmd.data2;
        blue = cmd.data3;
        color = strips[activeStripIndex].Color(red, green, blue);
        break;

      case 'l':  // Comando de LED
        // El segundo byte es para la posición
        ledNum = cmd.data1;

        strips[activeStripIndex].clear();
        if (ledNum > 0 && ledNum <= NUMLED) {
          strips[activeStripIndex].setPixelColor(ledNum - 1, color);
        }
        strips[activeStripIndex].show();
        break;

      case 't':  // Comando test
        strips[activeStripIndex].clear();
        strips[activeStripIndex].setPixelColor(0, color);
        strips[activeStripIndex].setPixelColor(NUMLED - 1, color);
        strips[activeStripIndex].show();
        break;
      
      case 'n':  // Comando para cambiar a la siguiente tira
        switchToNextStrip();
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
  
  // Inicializar todas las tiras LED
  for (int i = 0; i < NUM_STRIPS; i++) {
    strips[i].begin();
    strips[i].clear();
    strips[i].show();
    delay(300);
  }

  // Configuración del pin de status
  pinMode(STATUS_LED, OUTPUT);
  digitalWrite(STATUS_LED, LOW);

  // Inicializar WiFi en modo estación
  WiFi.mode(WIFI_STA);

  // Inicializar ESP-NOW
  if (esp_now_init() != ESP_OK) {
    digitalWrite(STATUS_LED, HIGH);
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
  // Inicialización correcta
  digitalWrite(STATUS_LED, HIGH);
  delay(500);
  digitalWrite(STATUS_LED, LOW);

  // Mostrar patrón de prueba inicial en la tira activa
  initial_test();
  
  Serial.println("EMDR Lightbar ready with ESP-NOW");
  Serial.print("Active strip: ");
  Serial.println(activeStripIndex + 1);
}

void loop() {
  // El loop queda vacío porque todo se maneja mediante callbacks
}