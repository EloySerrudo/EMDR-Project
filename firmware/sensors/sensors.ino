#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <Wire.h>
#include <Adafruit_ADS1X15.h>
#include "CircularBuffer.h"
#include <esp_now.h>
#include <WiFi.h>
#include "esp_timer.h"  // Incluir para el timer

// Identificador único de este dispositivo
#define DEVICE_ID 1     // Sensor de señales

#define I2C_ADDRESS 0x48

#define SAMPLE_RATE 125  // Frecuencia de muestreo en SPS (muestras por segundo)
#define BUFFER_SIZE 256  // Tamaño del buffer circular (ajustable)

// Definición de protocolo binario
#define PACKET_HEADER 0xAA55  // Marker para inicio de paquete
#define PACKET_SIZE 15        // Tamaño del paquete binario en bytes. Esta constante es sólo para información, nunca se usa.

// LED para indicar estado de la transmisión ESP-NOW
constexpr int STATUS_LED = 16;

// LED para indicar error en el ADS1115
constexpr int ERROR_LED = 4;

// Objeto ADS1115
Adafruit_ADS1115 ads;

// Handle para el timer
esp_timer_handle_t timer_handle;

// Información del peer para ESP-NOW
esp_now_peer_info_t peerInfo;

// Variables compartidas entre núcleos
volatile bool capturing = false;
volatile bool dataReady = false;
volatile bool espNowConnected = false;
volatile uint8_t channel = 1;
volatile uint32_t startTime = 0;

// Semáforo para sincronización entre la ISR y la tarea
portMUX_TYPE dataMux = portMUX_INITIALIZER_UNLOCKED;

// Usar la clase CircularBuffer para manejar los datos del ADC
CircularBuffer adcBuffer(BUFFER_SIZE);

// Handles para las tareas
TaskHandle_t adcTaskHandle = NULL;
TaskHandle_t transmitTaskHandle = NULL;

// MAC del dispositivo maestro
uint8_t masterAddress[] = {0xE4, 0x65, 0xB8, 0xA3, 0x7E, 0x4C};  // Reemplazar con la MAC actual del maestro

// Estructura para enviar los datos de la tarea ADC
// Debe coincidir con una estructura receptora en el maestro
typedef struct struct_message {
  uint16_t header;      // 2 bytes
  uint32_t id;          // 4 bytes
  uint32_t timestamp;   // 4 bytes
  int16_t value_0;      // 2 bytes
  int16_t value_1;      // 2 bytes
  uint8_t device_id;    // 1 byte
} struct_message;       // TOTAL: 15 bytes

// Estructura para recibir los datos a través de ESP-NOW
typedef struct {
    char cmd;       // 'S': start, 'P': pause, 'A': acknowledge
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

// Estructura de envío de datos (myData)
struct_message myData;

// Variable para el último estado de envío ESP-NOW
volatile bool lastSendStatus = true;

// Callback cuando los datos son enviados
void OnDataSent(const uint8_t *mac_addr, esp_now_send_status_t status) {
  // Indica si el último comando fue enviado con éxito
  lastSendStatus = (status == ESP_NOW_SEND_SUCCESS);
}

// Callback cuando se reciben datos del maestro
void OnDataReceived(const uint8_t *mac_addr, const uint8_t *incomingData, int data_len) {
    // Verificar si los datos recibidos son del maestro
    if (data_len == sizeof(CommandPacket)) {
        CommandPacket cmd;
        memcpy(&cmd, incomingData, sizeof(cmd));
        // Convertir comando a minúsculas para procesar tanto mayúsculas como minúsculas
        char command = tolower(cmd.cmd);
        Serial.println(cmd.cmd);
        switch (command) {
            case 's':  // Comando de inicio de captura
                ads.startADCReading(ADS1X15_REG_CONFIG_MUX_DIFF_0_3, /*continuous=*/false);
                digitalWrite(STATUS_LED, HIGH);  // Indicar captura activa
                capturing = true;
                // Iniciar el timer para muestreo periódico cada 4ms (250Hz), 4ms = 4000us
                if (!esp_timer_is_active(timer_handle)) {
                    ESP_ERROR_CHECK(esp_timer_start_periodic(timer_handle, 4000));
                }
                break;
            case 'p':  // Comando de stop de captura
                capturing = false;
                portENTER_CRITICAL(&dataMux);
                startTime = 0;  // Reset startTime when ending capture
                channel = 1;
                portEXIT_CRITICAL(&dataMux);
                ads.setGain(GAIN_FOUR);
                digitalWrite(STATUS_LED, LOW);  // Indicar captura inactiva
                // Detener el timer
                if (esp_timer_is_active(timer_handle)) {
                    ESP_ERROR_CHECK(esp_timer_stop(timer_handle));
                }
                break;
            case 'a':  // Comando de verificación de conexión
                // Enviar respuesta al maestro
                ack_packet_t response;
                response.command = 'A';  // Confirmación de conexión
                response.device_id = DEVICE_ID;  // Usar el ID definido 
                response.status = 1;  // 1 = OK
                
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
 
// Rutina de servicio de interrupción (ISR) para el timer
void IRAM_ATTR timerCallback(void *arg) {
    portENTER_CRITICAL_ISR(&dataMux);
    dataReady = true;
    portEXIT_CRITICAL_ISR(&dataMux);
}

// Tarea para leer el ADS1115 (Núcleo 1)
void adcTask(void *parameter) {
    int16_t adcValue_A0 = 0, adcValue_A1 = 0;
    uint32_t time = 0;
    while (1) {
        // Esperar a que los datos estén listos (indicado por la interrupción del timer)
        if (dataReady && capturing) {
            portENTER_CRITICAL(&dataMux);
            dataReady = false;
            channel ^= 1;  // Alternar entre canales A0 y A1
            portEXIT_CRITICAL(&dataMux);

            // Con la librería Adafruit, usando lecturas diferenciales
            if (channel == 0) {   // Canal A0 (Pulso)
                adcValue_A0 = ads.getLastConversionResults();
                if (startTime == 0) startTime = millis();
                time = millis() - startTime;
                // Aumentar la ganancia para la lectura del sensor de EOG
                ads.setGain(GAIN_SIXTEEN);       // 16x gain  +/- 0.256V  1 bit = 0.0078125mV
                ads.startADCReading(ADS1X15_REG_CONFIG_MUX_DIFF_1_3, /*continuous=*/false);
            } else {
                adcValue_A1 = ads.getLastConversionResults();
                // Almacenar en el buffer circular
                adcBuffer.write(time, adcValue_A0, adcValue_A1);
                // Cambiar el canal para la lectura del sensor de PPG
                ads.setGain(GAIN_FOUR);       // 4x gain   +/- 1.024V  1 bit = 0.03125mV
                ads.startADCReading(ADS1X15_REG_CONFIG_MUX_DIFF_0_3, /*continuous=*/false);
            }
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
            if (adcBuffer.read(&packet)) {
                // Preparar el paquete ESP-NOW
                myData.header = PACKET_HEADER;
                myData.id = packet.id;
                myData.timestamp = packet.timestamp;
                myData.value_0 = packet.value_0;
                myData.value_1 = packet.value_1;
                myData.device_id = DEVICE_ID;  // Añadir el ID del dispositivo

                // Enviar por ESP-NOW al maestro
                esp_err_t result = esp_now_send(masterAddress, 
                                                (uint8_t *) &myData, 
                                                sizeof(myData));
            }
        }
        // Pequeña espera para no saturar el CPU
        vTaskDelay(2);
    }
}

void setup() {
  Serial.begin(115200);
  delay(1000);

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
  if (esp_now_add_peer(&peerInfo) != ESP_OK) {
    return;
  }

  // Indicar que ESP-NOW está listo
  espNowConnected = true;
  
  // Inicializar I2C para comunicación con el ADS1115
  Wire.begin();

  // Inicializar ADS1115 con la librería Adafruit
  if (!ads.begin(I2C_ADDRESS)) {
      // Si no responde el ADS1115, indicar con led
      while (1) {
          delay(500);
          digitalWrite(ERROR_LED, HIGH);
          delay(500);
          digitalWrite(ERROR_LED, LOW);
      }
  }
  
  // Configurar el ADS1115: Canal A0 (Pulso)
  ads.setDataRate(RATE_ADS1115_475SPS); // Usar 475 SPS (similar al original)
  ads.setGain(GAIN_FOUR);              // 4x gain   +/- 1.024V  1 bit = 0.03125mV
  // Inicialización correcta
  digitalWrite(STATUS_LED, HIGH);
  delay(500);
  digitalWrite(STATUS_LED, LOW);
  
  // Configurar el timer pero no iniciarlo todavía
  const esp_timer_create_args_t timer_args = {
      .callback = &timerCallback,
      .arg = NULL,
      .dispatch_method = ESP_TIMER_TASK,
      .name = "adc_timer"
  };
  ESP_ERROR_CHECK(esp_timer_create(&timer_args, &timer_handle));
  // El timer se iniciará cuando se reciba el comando 'S'

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