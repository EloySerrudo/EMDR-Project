#include "driver/i2s.h"
#include "driver/adc.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#define ADC_PIN 36       // GPIO donde está conectado el HW-827
#define BUFFER_SIZE 512  // Tamaño del buffer DMA

// Configuración I2S para ADC con DMA
#define I2S_NUM I2S_NUM_0
#define I2S_SAMPLE_RATE 1000  // Frecuencia de muestreo en Hz

uint16_t adc_buffer[BUFFER_SIZE];
volatile bool capturing = false;
TaskHandle_t adcTaskHandle = NULL;

// Tarea dedicada para la captura ADC
void adcTask(void * parameter) {
  while(1) {
    if (capturing) {
      size_t bytes_read = 0;
      // Leer datos del ADC usando DMA a través de I2S
      esp_err_t result = i2s_read(I2S_NUM, adc_buffer, sizeof(adc_buffer), &bytes_read, 100 / portTICK_PERIOD_MS);
      
      if (result == ESP_OK && bytes_read > 0) {
        // Procesar y enviar solo los valores de 12 bits relevantes
        size_t samples_read = bytes_read / 2; // 16 bits (2 bytes) por muestra
        for (int i = 0; i < samples_read; i++) {
          // Tomar solo los 12 bits de datos relevantes
          uint16_t adc_value = adc_buffer[i] & 0x0FFF;
          Serial.write((uint8_t*)&adc_value, 2); // Enviar los 2 bytes de cada valor
        }
      }
    } else {
      // Si no estamos capturando, esperar
      vTaskDelay(100 / portTICK_PERIOD_MS);
    }
  }
}

// Inicializar ADC con DMA mediante I2S
void init_adc_with_dma() {
  // Configuración I2S para ADC
  i2s_config_t i2s_config = {
    .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX | I2S_MODE_ADC_BUILT_IN),
    .sample_rate = I2S_SAMPLE_RATE,
    .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
    .channel_format = I2S_CHANNEL_FMT_ONLY_RIGHT,
    .communication_format = I2S_COMM_FORMAT_STAND_I2S,
    .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
    .dma_buf_count = 4,
    .dma_buf_len = BUFFER_SIZE / 4,
    .use_apll = false,
    .tx_desc_auto_clear = false,
    .fixed_mclk = 0
  };
  
  // Instalar driver I2S
  i2s_driver_install(I2S_NUM, &i2s_config, 0, NULL);
  
  // Configurar el ADC
  adc1_config_width(ADC_WIDTH_BIT_12);  // Resolución de 12 bits
  adc1_config_channel_atten(ADC1_CHANNEL_0, ADC_ATTEN_DB_11);  // ADC1_CHANNEL_0 corresponde a GPIO36
  
  // Conectar ADC1 al bus I2S
  i2s_set_adc_mode(ADC_UNIT_1, ADC1_CHANNEL_0);
  
  // Habilitar ADC con I2S
  i2s_adc_enable(I2S_NUM);
}

void setup() {
  Serial.begin(115200);
  delay(1000);  // Tiempo para que Serial se estabilice
  
  // Inicializar ADC con DMA
  init_adc_with_dma();
  
  // Crear tarea para manejar la captura ADC
  xTaskCreate(
    adcTask,          // Función de la tarea
    "ADC Task",       // Nombre
    4096,             // Tamaño de la pila
    NULL,             // Parámetros
    1,                // Prioridad
    &adcTaskHandle    // Handle
  );
}

void loop() {
  if (Serial.available()) {
    char command = Serial.read();
    if (command == 'S') {
      capturing = true;
      // Se elimina Serial.println("OK-S")
    } else if (command == 'P') {
      capturing = false;
      // Se elimina Serial.println("OK-P")
    }
  }
  
  delay(100);
}