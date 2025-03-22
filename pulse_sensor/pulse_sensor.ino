#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <Wire.h>
#include <ADS1115_WE.h>
#include "CircularBuffer.h"

#define I2C_ADDRESS 0x48
#define SAMPLE_RATE 250  // Frecuencia de muestreo en SPS (muestras por segundo)
#define BUFFER_SIZE 256  // Tamaño del buffer circular (ajustable)

// Pin para la interrupción ALERT/RDY del ADS1115
constexpr int READY_PIN = 32;

// Objeto ADS1115
ADS1115_WE ads = ADS1115_WE(I2C_ADDRESS);

// Variables compartidas entre núcleos
volatile bool capturing = false;
volatile bool dataReady = false;

// Semáforo para sincronización entre la ISR y la tarea
portMUX_TYPE dataMux = portMUX_INITIALIZER_UNLOCKED;

// Usar la clase CircularBuffer para manejar los datos del ADC
CircularBuffer adcBuffer(BUFFER_SIZE);

// Handles para las tareas
TaskHandle_t adcTaskHandle = NULL;
TaskHandle_t serialTaskHandle = NULL;

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

// Tarea para manejar comunicación serial (Núcleo 1)
void serialTask(void *parameter) {
  DataPacket packet;

  while (1) {
    // Procesar comandos seriales
    if (Serial.available() > 0) {
      char cmd = Serial.read();

      if (cmd == 'S' || cmd == 's') {
        // Reiniciar el tiempo de inicio para que los timestamps comiencen en 0
        capturing = true;
        // Configurar el ADS1115 en modo de conversión continua en el canal 0
        ads.setMeasureMode(ADS1115_CONTINUOUS);
      } else if (cmd == 'P' || cmd == 'p') {
        capturing = false;
        ads.setMeasureMode(ADS1115_SINGLE);
      }
    }

    // Enviar datos si estamos capturando
    if (capturing && adcBuffer.available() > 0) {
      // Obtener datos del buffer
      while (adcBuffer.read(&packet)) {
        // Enviar como JSON para facilitar parseo en el receptor
        Serial.print("{\"id\":");
        Serial.print(packet.id);
        Serial.print(",\"timestamp\":");
        Serial.print(packet.timestamp);
        Serial.print(",\"value\":");
        Serial.print(packet.value);
        Serial.println("}");
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

  // Inicializar I2C para comunicación con el ADS1115
  Wire.begin();

  // Configurar el pin READY como entrada para la interrupción
  pinMode(READY_PIN, INPUT_PULLUP);

  // Inicializar ADS1115
  if (!ads.init()) {
    pinMode(23, OUTPUT);
    // Si no responde el ADS1115, indicar con led
    while (1) {
      delay(500);
      digitalWrite(23, HIGH);
      delay(500);
      digitalWrite(23, LOW);
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

  // Crear tareas en cada núcleo
  xTaskCreatePinnedToCore(
    adcTask,         // Función de tarea
    "ADC_Task",      // Nombre de tarea
    4096,            // Tamaño de stack (palabras)
    NULL,            // Parámetros
    1,               // Prioridad
    &adcTaskHandle,  // Handle de tarea
    0);              // Núcleo 0

  xTaskCreatePinnedToCore(
    serialTask,         // Función de tarea
    "Serial_Task",      // Nombre de tarea
    4096,               // Tamaño de stack (palabras)
    NULL,               // Parámetros
    1,                  // Prioridad
    &serialTaskHandle,  // Handle de tarea
    1);                 // Núcleo 1
}

void loop() {
  // El loop principal queda vacío ya que todo se maneja en las tareas
  delay(1000);
}