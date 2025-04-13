#include <esp_now.h>
#include <WiFi.h>
#include <Adafruit_NeoPixel.h>

// Identificador único de este dispositivo
#define DEVICE_ID 2     // Sensor de señales

#define PIN_LED       13    // Pin para controlar el NeoPixel strip
#define PIN_LED_ERROR 23    // LED para indicar errores
#define NUMLED        60    // Número de LEDs en la tira

// Estructura para recibir los datos a través de ESP-NOW
typedef struct {
  char cmd;
  uint8_t data1;
  uint8_t data2;
  uint8_t data3;
} CommandPacket;

// Inicialización de la tira NeoPixel
Adafruit_NeoPixel strip = Adafruit_NeoPixel(NUMLED, PIN_LED, NEO_GRB + NEO_KHZ800);

// Variables para el control de color y LED
uint8_t red = 0x0F;
uint8_t green = 0;
uint8_t blue = 0;

// Para control de estado de conexión
bool receivedCommand = false;
unsigned long lastCommandTime = 0;
const unsigned long CONNECTION_TIMEOUT = 10000; // 10 segundos sin comandos = desconexión

void setup() {
  // Inicialización de la tira NeoPixel
  strip.begin();
  strip.clear();
  strip.show();
  
  // Configuración del pin de error
  pinMode(PIN_LED_ERROR, OUTPUT);
  digitalWrite(PIN_LED_ERROR, LOW);
  
  // Inicializar WiFi en modo estación
  WiFi.mode(WIFI_STA);
  
  // Inicializar ESP-NOW
  if (esp_now_init() != ESP_OK) {
    digitalWrite(PIN_LED_ERROR, HIGH);
    return;
  }
  
  // Registrar la función de callback para cuando recibamos datos
  esp_now_register_recv_cb(OnDataRecv);
  
  // Mostrar patrón de prueba inicial
  test();
}

void loop() {
  // Verificar si estamos desconectados (timeout)
  if (receivedCommand && millis() - lastCommandTime > CONNECTION_TIMEOUT) {
    receivedCommand = false;
    // Indicar desconexión (por ejemplo, parpadear el LED de error)
    digitalWrite(PIN_LED_ERROR, HIGH);
    delay(100);
    digitalWrite(PIN_LED_ERROR, LOW);
  }
}

// Callback para cuando se reciben datos
void OnDataRecv(const uint8_t *mac, const uint8_t *incomingData, int len) {
  // Actualizar indicadores de conexión
  receivedCommand = true;
  lastCommandTime = millis();
  digitalWrite(PIN_LED_ERROR, LOW);
  
  // Procesar el comando recibido
  if (len == sizeof(CommandPacket)) {
    CommandPacket cmd;
    memcpy(&cmd, incomingData, sizeof(cmd));
    
    uint8_t ledNum;
    switch (cmd.cmd) {
      case 'c': // Comando de color
        // Los 3 bytes siguientes son para RGB
        red = cmd.data1;
        green = cmd.data2;
        blue = cmd.data3;
        break;
        
      case 'l': // Comando de LED
        // El segundo byte es para la posición
        ledNum = cmd.data1;
        
        clearLEDs();
        if (ledNum > 0 && ledNum <= NUMLED) {
          strip.setPixelColor(ledNum - 1, strip.Color(red, green, blue));
        }
        strip.show();
        break;
        
      case 't': // Comando test
        clearLEDs();
        strip.setPixelColor(0, strip.Color(red, green, blue));
        strip.setPixelColor(NUMLED - 1, strip.Color(red, green, blue));
        strip.show();
        break;
    }
  }
}

// Función para limpiar todos los LEDs
void clearLEDs() {
  strip.clear();
}

// Función para probar la tira de LEDs al inicio
void test() {
  clearLEDs();
  strip.setPixelColor(0, strip.Color(0, 0x20, 0));
  strip.setPixelColor(NUMLED - 1, strip.Color(0x20, 0, 0));
  strip.show();
  delay(500);
  clearLEDs();
  strip.show();
}