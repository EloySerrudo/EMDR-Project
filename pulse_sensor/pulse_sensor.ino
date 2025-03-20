#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <Wire.h>
#include <Adafruit_ADS1X15.h>

#define SAMPLE_RATE 250   // Frecuencia de muestreo en Hz (cambiado a 250Hz)

// Objeto ADS1115
Adafruit_ADS1115 ads;

// Variables compartidas entre núcleos
volatile bool capturing = false;
TaskHandle_t adcTaskHandle = NULL;
TaskHandle_t serialTaskHandle = NULL;

// Tarea para el Core 1: Lectura del ADS1115 y envío por Serial
void adcTask(void * parameter) {
  const TickType_t xDelay = 1000 / SAMPLE_RATE / portTICK_PERIOD_MS; // Para 250Hz
  int16_t adc_value = 0;
  while(1) {
    if (capturing) {
      // Leer valor del ADS1115 en modo diferencial entre canales 0 y 1
      adc_value = ads.readADC_Differential_0_1();
      
      // Enviar los 2 bytes del valor leído
      Serial.write((uint8_t*)&adc_value, 2);
      
      // Esperar para mantener la frecuencia de muestreo precisa
      vTaskDelay(xDelay);
    } else {
      // Si no estamos capturando, esperar más tiempo para ahorrar CPU
      vTaskDelay(100 / portTICK_PERIOD_MS);
    }
  }
}

// Tarea para el Core 0: Lectura de comandos por Serial
void serialTask(void * parameter) {
  while(1) {
    if (Serial.available()) {
      char command = Serial.read();
      
      if (command == 'S') {
        capturing = true;
      } else if (command == 'P') {
        capturing = false;
      }
    }
    
    // Pequeña espera para no saturar la CPU
    vTaskDelay(100 / portTICK_PERIOD_MS);
  }
}

void setup() {
  // Inicializar Serial a 115200 baudios
  Serial.begin(115200);
  delay(1000);  // Tiempo para que Serial se estabilice
  
  // Inicializar I2C para comunicación con el ADS1115
  Wire.begin();
  
  // Inicializar ADS1115
  if (!ads.begin()) {
    Serial.println("Error al inicializar el ADS1115!");
    while (1);
  }
  
  // Configurar el ADS1115
  ads.setGain(GAIN_ONE);        // Ganancia de 1
  ads.setDataRate(RATE_ADS1115_475SPS); // 250 muestras por segundo
  
  // Crear tarea para manejar la captura ADC en el Core 1
  xTaskCreatePinnedToCore(
    adcTask,          // Función de la tarea
    "ADC Task",       // Nombre
    2048,             // Tamaño de la pila
    NULL,             // Parámetros
    1,                // Prioridad
    &adcTaskHandle,   // Handle
    1                 // Core 1
  );
  
  // Crear tarea para manejar la lectura Serial en el Core 0
  xTaskCreatePinnedToCore(
    serialTask,       // Función de la tarea
    "Serial Task",    // Nombre
    2048,             // Tamaño de la pila
    NULL,             // Parámetros
    1,                // Prioridad
    &serialTaskHandle,// Handle
    0                 // Core 0
  );
}

void loop() {
  // El loop principal queda vacío ya que todo se maneja en las tareas
  delay(1000);
}