#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <WiFi.h>
#include <esp_now.h>
#include <esp_system.h>

// Configuración de LED y botones
#define STATUS_LED 18       // LED integrado del ESP32 (puede variar según la placa)
#define PACKET_HEADER 0xAA55  // Debe coincidir con el header en el transmisor
#define PACKET_SIZE 12        // Tamaño del paquete binario en bytes

// Información del peer para ESP-NOW
esp_now_peer_info_t peerInfo;

// Variables globales
bool forwarding = true;       // Indicador de si se reenvían los datos al PC

// Estructura para recibir datos por ESP-NOW (debe coincidir con el transmisor)
typedef struct esp_now_packet {
    uint16_t header;
    uint32_t id;
    uint32_t timestamp;
    int16_t value;
} esp_now_packet_t;

// Estructura para enviar comandos a los esclavos
typedef struct command_packet {
    uint8_t command;  // 'S': start, 'P': pause
} command_packet_t;

// Direcciones MAC de los dispositivos esclavos
uint8_t slaveAddresses[][6] = {
    {0xA0, 0xA3, 0xB3, 0xAA, 0x33, 0xA4}, // MAC del sensor de pulso
    // Añadir más dispositivos aquí cuando sea necesario
};

#define NUM_SLAVES (sizeof(slaveAddresses) / sizeof(slaveAddresses[0]))

// Buffer para reensamblar paquetes para serial
uint8_t serialPacket[PACKET_SIZE];

// Estado de envío de comandos
volatile bool lastCommandSent = true;

// Callback que se ejecuta cuando se envía un paquete por ESP-NOW
void onSentEspNowData(const uint8_t *mac_addr, esp_now_send_status_t status) {
    lastCommandSent = (status == ESP_NOW_SEND_SUCCESS);
}

// Callback que se ejecuta cuando se reciben datos por ESP-NOW
void onReceivedEspNowData(const uint8_t *mac_addr, const uint8_t *data, int data_len) {
    // Verificar que el tamaño de datos coincide con nuestra estructura
    if (data_len == sizeof(esp_now_packet_t)) {
        // Convertir datos recibidos a nuestra estructura
        esp_now_packet_t *packet = (esp_now_packet_t*)data;
        
        // Verificar header del paquete
        if (packet->header == PACKET_HEADER) {
            // Parpadear LED para indicar recepción
            // digitalWrite(STATUS_LED, HIGH);
            
            // Reenviar datos por serial en formato binario si está habilitado
            if (forwarding) {
                // Preparar paquete en el formato esperado por la aplicación Python
                // Header (2 bytes)
                serialPacket[0] = PACKET_HEADER & 0xFF;         // LSB
                serialPacket[1] = (PACKET_HEADER >> 8) & 0xFF;  // MSB
                
                // ID (4 bytes)
                serialPacket[2] = packet->id & 0xFF;
                serialPacket[3] = (packet->id >> 8) & 0xFF;
                serialPacket[4] = (packet->id >> 16) & 0xFF;
                serialPacket[5] = (packet->id >> 24) & 0xFF;
                
                // Timestamp (4 bytes)
                serialPacket[6] = packet->timestamp & 0xFF;
                serialPacket[7] = (packet->timestamp >> 8) & 0xFF;
                serialPacket[8] = (packet->timestamp >> 16) & 0xFF;
                serialPacket[9] = (packet->timestamp >> 24) & 0xFF;
                
                // Valor (2 bytes)
                serialPacket[10] = packet->value & 0xFF;
                serialPacket[11] = (packet->value >> 8) & 0xFF;
                
                // Enviar el paquete completo en una sola operación
                Serial.write(serialPacket, PACKET_SIZE);
            }
            
            // digitalWrite(STATUS_LED, LOW);
        }
    }
}

// Función para enviar comandos a todos los esclavos
void sendCommandToSlaves(uint8_t cmd) {
    command_packet_t packet;
    packet.command = cmd;
    
    for (int i = 0; i < NUM_SLAVES; i++) {
        esp_err_t result = esp_now_send(slaveAddresses[i], (uint8_t *)&packet, sizeof(packet));
        if (result == ESP_OK) {
            // Serial.print("Comando ");
            // Serial.print((char)cmd);
            // Serial.println(" enviado a esclavo");
        } else {
            // Serial.println("Error enviando comando");
        }
        // Pequeña pausa entre envíos
        delay(10);
    }
}

// Tarea para manejar comandos y reportar estado
void serialTask(void *parameter) {
    while (1) {
        // Procesar comandos seriales
        if (Serial.available() > 0) {
            char cmd = Serial.read();
            
            if (cmd == 'S' || cmd == 's') {
                forwarding = true;
                // Enviar comando de inicio a los esclavos
                sendCommandToSlaves('S');
                // Serial.println("Reenvío de datos activado y comando enviado a esclavos");
            } else if (cmd == 'P' || cmd == 'p') {
                forwarding = false;
                // Enviar comando de pausa a los esclavos
                sendCommandToSlaves('P');
                // Serial.println("Reenvío de datos desactivado y comando enviado a esclavos");
            }
        }
        
        // Esperar un poco para no saturar la CPU
        vTaskDelay(20);
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
    
    // Inicializar ESP-NOW
    if (esp_now_init() != ESP_OK) {
        // Serial.println("Error inicializando ESP-NOW");
        return;
    }
    
    // Registrar callback para recepción de datos
    esp_now_register_recv_cb(onReceivedEspNowData);
    // Registrar callback para envío de datos
    esp_now_register_send_cb(onSentEspNowData);
    
    // Registrar todos los dispositivos esclavos como peers
    for (uint8_t i = 0; i < NUM_SLAVES; i++) {
        memcpy(peerInfo.peer_addr, slaveAddresses[i], 6);
        peerInfo.channel = 0;
        peerInfo.encrypt = false;
        
        if (esp_now_add_peer(&peerInfo) != ESP_OK) {
            // Serial.print("Error al registrar esclavo #");
            // Serial.println(i);
        } else {
            // Serial.print("Esclavo #");
            // Serial.print(i);
            // Serial.println(" registrado con éxito");
            digitalWrite(STATUS_LED, HIGH);
        }
    }

    // Serial.println("Maestro listo. Envía 'S' para iniciar y 'P' para detener todos los esclavos.");
    
    // Crear tarea para manejar comandos seriales y reportar estado
    TaskHandle_t serialTaskHandle = NULL;
    xTaskCreatePinnedToCore(
        serialTask,          // Función de tarea
        "Serial_Task",       // Nombre de tarea
        4096,                // Tamaño de stack (palabras)
        NULL,                // Parámetros
        1,                   // Prioridad
        &serialTaskHandle,   // Handle de tarea
        1);                  // Núcleo 1
}

void loop() {
    // El loop principal queda vacío ya que todo se maneja en tareas
    delay(1000);
}