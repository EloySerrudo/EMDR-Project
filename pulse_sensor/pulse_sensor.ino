#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <Wire.h>
#include <ADS1115_WE.h>
#include "CircularBuffer.h"
#include <esp_now.h>
#include <WiFi.h>

#define I2C_ADDRESS 0x48
#define I2C_SDA 23
#define I2C_SCL 19

#define SAMPLE_RATE 250  // Frecuencia de muestreo en SPS (muestras por segundo)
#define BUFFER_SIZE 256  // Tamaño del buffer circular (ajustable)

// Definición de protocolo binario
#define PACKET_HEADER 0xAA55  // Marker para inicio de paquete
#define PACKET_SIZE 12        // Tamaño del paquete binario en bytes

// Pin para la interrupción ALERT/RDY del ADS1115
constexpr int READY_PIN = 32;

// LED para indicar estado de la transmisión ESP-NOW
constexpr int STATUS_LED = 22;  // LED integrado del ESP32 (puede variar según la placa)

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

// MAC Address del ESP32 receptor (MODIFICAR CON LA DIRECCIÓN MAC DE TU RECEPTOR)
uint8_t receiverMacAddress[] = {0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC};

// Estructura para enviar datos por ESP-NOW (debe coincidir con el receptor)
typedef struct esp_now_packet {
    uint16_t header;
    uint32_t id;
    uint32_t timestamp;
    int16_t value;
} esp_now_packet_t;

// Variable para el último estado de envío ESP-NOW
volatile bool lastSendStatus = true;

// Callback cuando se envía un paquete ESP-NOW
void onSentEspNowData(const uint8_t *mac_addr, esp_now_send_status_t status) {
    lastSendStatus = (status == ESP_NOW_SEND_SUCCESS);
    digitalWrite(STATUS_LED, lastSendStatus ? HIGH : LOW);  // LED encendido = éxito, apagado = error
}

// Rutina de servicio de interrupción (ISR)
void IRAM_ATTR readyISR() {
    portENTER_CRITICAL_ISR(&dataMux);
    dataReady = true;
    portEXIT_CRITICAL_ISR(&dataMux);
}

// Tarea para leer el ADS1115 (Núcleo 0)
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

// Tarea para transmitir datos por ESP-NOW (Núcleo 1)
void transmitTask(void *parameter) {
    DataPacket packet;
    esp_now_packet_t espPacket;

    while (1) {
        // Procesar comandos seriales
        if (Serial.available() > 0) {
            char cmd = Serial.read();

            if (cmd == 'S' || cmd == 's') {
                capturing = true;
                // Configurar el ADS1115 en modo de conversión continua en el canal 0
                ads.setMeasureMode(ADS1115_CONTINUOUS);
                Serial.println("Captura iniciada");
            } else if (cmd == 'P' || cmd == 'p') {
                capturing = false;
                ads.setMeasureMode(ADS1115_SINGLE);
                Serial.println("Captura detenida");
            }
        }

        // Enviar datos si estamos capturando y tenemos conexión ESP-NOW
        if (capturing && espNowConnected && adcBuffer.available() > 0) {
            // Obtener datos del buffer
            while (adcBuffer.read(&packet)) {
                // Preparar el paquete ESP-NOW
                espPacket.header = PACKET_HEADER;
                espPacket.id = packet.id;
                espPacket.timestamp = packet.timestamp;
                espPacket.value = packet.value;
                
                // Enviar por ESP-NOW
                esp_err_t result = esp_now_send(receiverMacAddress, 
                                               (uint8_t *)&espPacket, 
                                               sizeof(esp_now_packet_t));
                
                if (result != ESP_OK) {
                    digitalWrite(STATUS_LED, LOW);  // Indicar error
                    // Pequeña pausa antes de reintentar
                    vTaskDelay(1);
                }
            }
        }

        // Pequeña espera para no saturar el CPU
        vTaskDelay(5);
    }
}

void setup() {
    // Inicializar Serial a 115200 baudios
    Serial.begin(115200);
    delay(1000);
    
    // Configurar el LED de estado
    pinMode(STATUS_LED, OUTPUT);
    digitalWrite(STATUS_LED, LOW);

    // Inicializar I2C para comunicación con el ADS1115
    Wire.begin(I2C_SDA, I2C_SCL);

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
    ads.setVoltageRange_mV(ADS1115_RANGE_1024);  // 4x gain   +/- 1.024V  1 bit = 0.03125mV
    // ADS1115 tiene tasas predefinidas, usamos 250SPS que es lo más cercano a 250Hz
    ads.setConvRate(ADS1115_16_SPS);
    
    ads.setCompareChannels(ADS1115_COMP_0_1);

    ads.setAlertPinMode(ADS1115_ASSERT_AFTER_1);
    ads.setAlertPinToConversionReady();
    
    // Adjuntar la interrupción al pin READY
    attachInterrupt(digitalPinToInterrupt(READY_PIN), readyISR, FALLING);

    // Inicializar WiFi en modo STA para ESP-NOW
    WiFi.mode(WIFI_STA);
    
    // Imprimir MAC Address para configuración
    Serial.print("MAC Address: ");
    Serial.println(WiFi.macAddress());

    // Inicializar ESP-NOW
    if (esp_now_init() != ESP_OK) {
        Serial.println("Error inicializando ESP-NOW");
        return;
    }

    // Registrar callback de envío
    esp_now_register_send_cb(onSentEspNowData);
    
    // Registrar el dispositivo receptor
    esp_now_peer_info_t peerInfo;
    memcpy(peerInfo.peer_addr, receiverMacAddress, 6);
    peerInfo.channel = 0;  
    peerInfo.encrypt = false;
    
    // Agregar peer        
    if (esp_now_add_peer(&peerInfo) != ESP_OK) {
        Serial.println("Error al agregar peer");
        return;
    }
    
    // Indicar que ESP-NOW está listo
    espNowConnected = true;
    digitalWrite(STATUS_LED, HIGH);
    Serial.println("ESP-NOW inicializado correctamente");
    Serial.println("Dispositivo listo. Envía 'S' para iniciar y 'P' para detener la captura.");

    // Crear tareas en cada núcleo
    xTaskCreatePinnedToCore(
        adcTask,             // Función de tarea
        "ADC_Task",          // Nombre de tarea
        4096,                // Tamaño de stack (palabras)
        NULL,                // Parámetros
        1,                   // Prioridad
        &adcTaskHandle,      // Handle de tarea
        0);                  // Núcleo 0

    xTaskCreatePinnedToCore(
        transmitTask,          // Función de tarea
        "Transmit_Task",       // Nombre de tarea
        4096,                  // Tamaño de stack (palabras)
        NULL,                  // Parámetros
        1,                     // Prioridad
        &transmitTaskHandle,   // Handle de tarea
        1);                    // Núcleo 1
}

void loop() {
    // El loop principal queda vacío ya que todo se maneja en las tareas
    delay(1000);
}