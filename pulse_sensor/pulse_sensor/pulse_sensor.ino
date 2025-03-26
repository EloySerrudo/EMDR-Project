#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <Wire.h>
#include <ADS1115_WE.h>
#include "CircularBuffer.h"
#include <esp_now.h>
#include <WiFi.h>

// Identificador único de este dispositivo
#define DEVICE_ID 1

#define I2C_ADDRESS 0x48

#define SAMPLE_RATE 250  // Frecuencia de muestreo en SPS (muestras por segundo)
#define BUFFER_SIZE 256  // Tamaño del buffer circular (ajustable)

// Definición de protocolo binario
#define PACKET_HEADER 0xAA55  // Marker para inicio de paquete
#define PACKET_SIZE 13        // Tamaño del paquete binario en bytes. Esta constante es sólo para información, nunca se usa.

// Pin para la interrupción ALERT/RDY del ADS1115
constexpr int READY_PIN = 32;

// LED para indicar estado de la transmisión ESP-NOW
constexpr int STATUS_LED = 23;

// LED para indicar error en el ADS1115
constexpr int ERROR_LED = 19;

// Objeto ADS1115
ADS1115_WE ads = ADS1115_WE(I2C_ADDRESS);

// Información del peer para ESP-NOW
esp_now_peer_info_t peerInfo;

// Variables compartidas entre núcleos
volatile bool capturing = false;
volatile bool dataReady = false;
volatile bool espNowConnected = false;

// Semáforo para sincronización entre la ISR y la tarea
portMUX_TYPE dataMux = portMUX_INITIALIZER_UNLOCKED;

// Usar la clase CircularBuffer para manejar los datos del ADC
CircularBuffer adcBuffer(BUFFER_SIZE);

// Handles para las tareas
TaskHandle_t adcTaskHandle = NULL;
TaskHandle_t transmitTaskHandle = NULL;

// MAC del dispositivo maestro
uint8_t masterAddress[] = {0xA0, 0xB7, 0x65, 0x55, 0xF3, 0x30};  // Reemplazar con la MAC real del maestro

// Estructura para enviar los datos de la tarea ADC
// Debe coincidir con una estructura receptora en el maestro
typedef struct struct_message {
  uint16_t header;      // 2 bytes
  uint32_t id;          // 4 bytes
  uint32_t timestamp;   // 4 bytes
  int16_t value;        // 2 bytes
  uint8_t device_id;    // 1 byte
} struct_message;       // TOTAL: 13 bytes

// Estructura para recibir comandos del maestro
typedef struct command_packet {
    uint8_t command;    // 'S': start, 'P': pause, 'C': check connection
    uint8_t device_id;  // ID del dispositivo (útil para respuestas)
} command_packet_t;

// Estructura para enviar confirmación al maestro
typedef struct ack_packet {
    uint8_t command;    // 'A': acknowledge
    uint8_t device_id;  // ID del dispositivo que responde
    uint8_t status;     // Estado del dispositivo
} ack_packet_t;

// Create a struct_message called myData
struct_message myData;

// Variable para el último estado de envío ESP-NOW
volatile bool lastSendStatus = true;

// callback when data is sent
void OnDataSent(const uint8_t *mac_addr, esp_now_send_status_t status) {
  lastSendStatus = (status == ESP_NOW_SEND_SUCCESS);
}

// callback when data is received from master
void OnDataReceived(const uint8_t *mac_addr, const uint8_t *data, int data_len) {
    // Verificar si los datos recibidos son del maestro
    if (memcmp(mac_addr, masterAddress, 6) == 0 && data_len == sizeof(command_packet_t)) {
        command_packet_t *cmd = (command_packet_t*)data;
        
        if (cmd->command == 'S' || cmd->command == 's') {
            capturing = true;
            // Configurar el ADS1115 en modo de conversión continua
            ads.setMeasureMode(ADS1115_CONTINUOUS);
            digitalWrite(STATUS_LED, HIGH);  // Indicar captura activa
        } else if (cmd->command == 'P' || cmd->command == 'p') {
            capturing = false;
            ads.setMeasureMode(ADS1115_SINGLE);
            digitalWrite(STATUS_LED, LOW);  // Indicar captura inactiva
        } else if (cmd->command == 'C') {
            // Preparar respuesta
            ack_packet_t response;
            response.command = 'A';  // Acknowledge
            response.device_id = DEVICE_ID;  // Usar el ID definido 
            response.status = 1;     // 1 = OK
            
            // Enviar respuesta al maestro
            esp_err_t result = esp_now_send(masterAddress, 
                                          (uint8_t *) &response, 
                                          sizeof(response));
            
            // Parpadear LED para indicar que respondimos
            digitalWrite(STATUS_LED, HIGH);
            delay(50);
            digitalWrite(STATUS_LED, LOW);
        }
    }
}
 
// Rutina de servicio de interrupción (ISR)
void IRAM_ATTR readyISR() {
    portENTER_CRITICAL_ISR(&dataMux);
    dataReady = true;
    portEXIT_CRITICAL_ISR(&dataMux);
}

// Tarea para leer el ADS1115 (Núcleo 1)
void adcTask(void *parameter) {
    int16_t adcValue = 0;
    uint32_t time = 0;
    uint32_t startTime = 0;
    while (1) {
        // Esperar a que los datos estén listos (indicado por la ISR)
        if (dataReady && capturing) {
            portENTER_CRITICAL(&dataMux);
            dataReady = false;
            portEXIT_CRITICAL(&dataMux);

            // Leer el valor del ADS1115
            adcValue = ads.getRawResult();

            if (startTime == 0) startTime = millis();
            time = millis() - startTime;

            // Almacenar en el buffer circular
            adcBuffer.write(adcValue, time);
        }
        // Pequeña espera para no saturar el CPU
        vTaskDelay(1);
    }
}

// Tarea para transmitir datos por ESP-NOW (Núcleo 0)
void transmitTask(void *parameter) {
    DataPacket packet;

    while (1) {
        // Enviar datos si estamos capturando y tenemos conexión ESP-NOW
        if (capturing && espNowConnected && adcBuffer.available() > 0) {
            // Obtener datos del buffer
            while (adcBuffer.read(&packet)) {
                // Preparar el paquete ESP-NOW
                myData.header = PACKET_HEADER;
                myData.id = packet.id;
                myData.timestamp = packet.timestamp;
                myData.value = packet.value;
                myData.device_id = DEVICE_ID;  // Añadir el ID del dispositivo

                // Enviar por ESP-NOW al maestro
                esp_err_t result = esp_now_send(masterAddress, 
                                                (uint8_t *) &myData, 
                                                sizeof(myData));
                
                if (result != ESP_OK) {
                    
                }
            }
        }

        // Pequeña espera para no saturar el CPU
        vTaskDelay(2);
    }
}

void setup() {
  // Configurar los LEDs
  pinMode(STATUS_LED, OUTPUT);
  pinMode(ERROR_LED, OUTPUT);
  digitalWrite(STATUS_LED, LOW);
  digitalWrite(ERROR_LED, LOW);

  // Inicializar WiFi en modo STA para ESP-NOW
  WiFi.mode(WIFI_STA);

  // Init ESP-NOW
  if (esp_now_init() != ESP_OK) {
    return;
  }

  // Registrar callback para envío y recepción de datos
  esp_now_register_send_cb(OnDataSent);
  esp_now_register_recv_cb(OnDataReceived);
  
  // Registrar maestro como peer
  memcpy(peerInfo.peer_addr, masterAddress, 6);
  peerInfo.channel = 0;  
  peerInfo.encrypt = false;
  
  // Add peer        
  if (esp_now_add_peer(&peerInfo) != ESP_OK){
    return;
  }

  // Indicar que ESP-NOW está listo
  espNowConnected = true;
  digitalWrite(STATUS_LED, HIGH);
  delay(500);
  digitalWrite(STATUS_LED, LOW);
  
  // Inicializar I2C para comunicación con el ADS1115
  Wire.begin();

  // Configurar el pin READY como entrada para la interrupción
  pinMode(READY_PIN, INPUT_PULLUP);

  // Inicializar ADS1115
  if (!ads.init()) {
      // Si no responde el ADS1115, indicar con led
      while (1) {
          delay(500);
          digitalWrite(ERROR_LED, HIGH);
          delay(500);
          digitalWrite(ERROR_LED, LOW);
      }
  }
  
  // Configurar el ADS1115
  ads.setVoltageRange_mV(ADS1115_RANGE_2048);  // 2x gain   +/- 2.048V  1 bit = 0.0625mV
  ads.setConvRate(ADS1115_16_SPS);  // Usar 250SPS para mejor frecuencia de muestreo
  
  ads.setCompareChannels(ADS1115_COMP_0_1);

  ads.setAlertPinMode(ADS1115_ASSERT_AFTER_1);
  ads.setAlertPinToConversionReady();
  
  // Adjuntar la interrupción al pin READY
  attachInterrupt(digitalPinToInterrupt(READY_PIN), readyISR, FALLING);

  // Crear tareas en cada núcleo
  xTaskCreatePinnedToCore(
      transmitTask,          // Función de tarea
      "Transmit_Task",       // Nombre de tarea
      4096,                  // Tamaño de stack (palabras)
      NULL,                  // Parámetros
      1,                     // Prioridad
      &transmitTaskHandle,   // Handle de tarea
      0);                    // Núcleo 0 (donde suele ejecutarse el controlador WiFi)

  xTaskCreatePinnedToCore(
      adcTask,             // Función de tarea
      "ADC_Task",          // Nombre de tarea
      4096,                // Tamaño de stack (palabras)
      NULL,                // Parámetros
      1,                   // Prioridad
      &adcTaskHandle,      // Handle de tarea
      1);                  // Núcleo 1
}
 
void loop() {
  // El loop principal queda vacío ya que todo se maneja en las tareas
  delay(1000);
}