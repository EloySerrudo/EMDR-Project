#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <Wire.h>
#include <ADS1115_WE.h>
#include "CircularBuffer.h"
#include <esp_now.h>
#include <WiFi.h>

#define I2C_ADDRESS 0x48

#define SAMPLE_RATE 250  // Frecuencia de muestreo en SPS (muestras por segundo)
#define BUFFER_SIZE 256  // Tamaño del buffer circular (ajustable)

// Definición de protocolo binario
#define PACKET_HEADER 0xAA55  // Marker para inicio de paquete
#define PACKET_SIZE 12        // Tamaño del paquete binario en bytes

// Pin para la interrupción ALERT/RDY del ADS1115
constexpr int READY_PIN = 32;

// LED para indicar estado de la transmisión ESP-NOW
constexpr int STATUS_LED = 23;  // LED integrado del ESP32 (puede variar según la placa)

// Objeto ADS1115
ADS1115_WE ads = ADS1115_WE(I2C_ADDRESS);

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

// REPLACE WITH YOUR RECEIVER MAC Address
uint8_t broadcastAddress[] = {0xA0, 0xB7, 0x65, 0x55, 0xF3, 0x30};

// Structure example to send data
// Must match the receiver structure
typedef struct struct_message {
  uint16_t header;
  uint32_t id;
  uint32_t timestamp;
  int16_t value;
} struct_message;

// Create a struct_message called myData
struct_message myData;

esp_now_peer_info_t peerInfo;

// Variable para el último estado de envío ESP-NOW
volatile bool lastSendStatus = true;

// callback when data is sent
void OnDataSent(const uint8_t *mac_addr, esp_now_send_status_t status) {
  lastSendStatus = (status == ESP_NOW_SEND_SUCCESS);
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
        // Procesar comandos seriales
        if (Serial.available() > 0) {
            char cmd = Serial.read();

            if (cmd == 'S' || cmd == 's') {
                capturing = true;
                // Configurar el ADS1115 en modo de conversión continua en el canal 0
                ads.setMeasureMode(ADS1115_CONTINUOUS);
                // Serial.println("Captura iniciada");
            } else if (cmd == 'P' || cmd == 'p') {
                capturing = false;
                ads.setMeasureMode(ADS1115_SINGLE);
                // Serial.println("Captura detenida");
            }
        }

        // Enviar datos si estamos capturando y tenemos conexión ESP-NOW
        if (capturing && espNowConnected && adcBuffer.available() > 0) {
            // Obtener datos del buffer
            while (adcBuffer.read(&packet)) {
                // Preparar el paquete ESP-NOW
                myData.header = PACKET_HEADER;
                myData.id = packet.id;
                myData.timestamp = packet.timestamp;
                myData.value = packet.value;

                // Enviar por ESP-NOW
                esp_err_t result = esp_now_send(broadcastAddress, 
                                                (uint8_t *) &myData, 
                                                sizeof(myData));
                
                // if (result != ESP_OK) {
                //     digitalWrite(STATUS_LED, LOW);  // Indicar error
                //     // Pequeña pausa antes de reintentar
                //     vTaskDelay(1);
                // }
            }
        }

        // Pequeña espera para no saturar el CPU
        vTaskDelay(2);
    }
}

void setup() {
  // Inicializar Serial a 115200 baudios
  Serial.begin(115200);
  delay(1000);
 
  // Configurar el LED de estado
  pinMode(STATUS_LED, OUTPUT);
  digitalWrite(STATUS_LED, LOW);

  // Inicializar WiFi en modo STA para ESP-NOW
  WiFi.mode(WIFI_STA);

  // Init ESP-NOW
  if (esp_now_init() != ESP_OK) {
    Serial.println("Error initializing ESP-NOW");
    return;
  }

  // Once ESPNow is successfully Init, we will register for Send CB to
  // get the status of Trasnmitted packet
  esp_now_register_send_cb(OnDataSent);
  
  // Register peer
  memcpy(peerInfo.peer_addr, broadcastAddress, 6);
  peerInfo.channel = 0;  
  peerInfo.encrypt = false;
  
  // Add peer        
  if (esp_now_add_peer(&peerInfo) != ESP_OK){
    Serial.println("Failed to add peer");
    return;
  }

  // Indicar que ESP-NOW está listo
    espNowConnected = true;
    digitalWrite(STATUS_LED, HIGH);
    Serial.println("ESP-NOW inicializado correctamente");
    Serial.println("Dispositivo listo. Envía 'S' para iniciar y 'P' para detener la captura.");

    // Inicializar I2C para comunicación con el ADS1115
    Wire.begin();

    // Configurar el pin READY como entrada para la interrupción
    pinMode(READY_PIN, INPUT_PULLUP);

    // Inicializar ADS1115
    if (!ads.init()) {
        pinMode(18, OUTPUT);
        // Si no responde el ADS1115, indicar con led
        while (1) {
            delay(500);
            digitalWrite(18, HIGH);
            delay(500);
            digitalWrite(18, LOW);
        }
    }
    
    // Configurar el ADS1115
    ads.setVoltageRange_mV(ADS1115_RANGE_2048);  // 2x gain   +/- 2.048V  1 bit = 0.0625mV
    // ADS1115 tiene tasas predefinidas, usamos 250SPS que es lo más cercano a 250Hz
    ads.setConvRate(ADS1115_16_SPS);
    
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