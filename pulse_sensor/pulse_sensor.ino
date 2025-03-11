#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#define ADC_PIN 36        // GPIO donde está conectado el HW-827
#define SAMPLE_RATE 256   // Frecuencia de muestreo en Hz (modificado de 100 a 256)

// Variables compartidas entre núcleos
volatile bool capturing = false;
TaskHandle_t adcTaskHandle = NULL;
TaskHandle_t serialTaskHandle = NULL;

// Tarea para el Core 1: Lectura del ADC y envío por Serial
void adcTask(void * parameter) {
  const TickType_t xDelay = 1000 / SAMPLE_RATE / portTICK_PERIOD_MS; // Para 256Hz
  
  while(1) {
    if (capturing) {
      // Leer valor del ADC
      uint16_t adc_value = analogRead(ADC_PIN);
      
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
    vTaskDelay(20 / portTICK_PERIOD_MS);
  }
}

void setup() {
  // Inicializar Serial a 9600 baudios
  Serial.begin(115200);
  delay(1000);  // Tiempo para que Serial se estabilice
  
  // Configurar resolución del ADC (12 bits)
  analogReadResolution(12);
  
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