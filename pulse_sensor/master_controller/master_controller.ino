#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <WiFi.h>
#include <esp_now.h>
#include <esp_system.h>

// Configuración de LED y botones
#define STATUS_LED 18       // LED integrado del ESP32 (puede variar según la placa)
#define PACKET_HEADER 0xAA55  // Debe coincidir con el header en el transmisor
#define PACKET_SIZE 15        // Tamaño del paquete binario en bytes

// Información del peer para ESP-NOW
esp_now_peer_info_t peerInfo;

// Variables globales
bool forwarding = true;       // Indicador de si se reenvían los datos al PC

// Estructura para recibir datos por ESP-NOW (debe coincidir con el transmisor)
typedef struct esp_now_packet {
    uint16_t header;
    uint32_t id;
    uint32_t timestamp;
    int16_t value_0;
    int16_t value_1;
    uint8_t device_id;  // Añadido para identificar el origen del mensaje
} esp_now_packet_t;

// Estructura para enviar comandos a los esclavos
typedef struct command_packet {
    uint8_t command;  // 'S': start, 'P': pause, 'A': check connection
    uint8_t device_id; // ID del dispositivo (útil para respuestas)
} command_packet_t;

// Estructura para recibir confirmación de los esclavos
typedef struct ack_packet {
    uint8_t command;  // 'A': acknowledge
    uint8_t device_id; // ID del dispositivo que responde
    uint8_t status;    // Estado del dispositivo
} ack_packet_t;

// Direcciones MAC de los dispositivos esclavos
uint8_t slaveAddresses[][6] = {
    {0xA0, 0xB7, 0x65, 0x55, 0xF3, 0x30}, // MAC del ESP32 sensor de señales. DEVICE_ID: 1
    // Añadir más dispositivos aquí cuando sea necesario
};

#define NUM_SLAVES (sizeof(slaveAddresses) / sizeof(slaveAddresses[0]))

// Buffer para reensamblar paquetes para serial
uint8_t serialPacket[PACKET_SIZE];

// Estado de envío de comandos
volatile bool lastCommandSent = true;

// Control de estado de los esclavos
bool slaveConnected[NUM_SLAVES] = {false};

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
                
                // Valor A0 (2 bytes)
                serialPacket[10] = packet->value_0 & 0xFF;
                serialPacket[11] = (packet->value_0 >> 8) & 0xFF;
                
                // Valor A1 (2 bytes)
                serialPacket[12] = packet->value_1 & 0xFF;
                serialPacket[13] = (packet->value_1 >> 8) & 0xFF;
                
                // Añadir device_id (1 byte)
                serialPacket[14] = packet->device_id;
                
                // Enviar el paquete completo en una sola operación
                Serial.write(serialPacket, PACKET_SIZE);
            }
        }
    }
    
    // Verificar si es una confirmación de conexión
    else if (data_len == sizeof(ack_packet_t)) {
        ack_packet_t *ackPacket = (ack_packet_t*)data;
        if (ackPacket->command == 'A') {
            uint8_t deviceId = ackPacket->device_id;
            // Buscar índice en slaveAddresses basado en deviceId
            for (int i = 0; i < NUM_SLAVES; i++) {
                // Si la MAC coincide o el índice es el mismo que el deviceId-1
                if (memcmp(mac_addr, slaveAddresses[i], 6) == 0) {
                    // Marcar el esclavo como conectado
                    slaveConnected[i] = true;
                    digitalWrite(STATUS_LED, HIGH);
                    delay(50);
                    digitalWrite(STATUS_LED, LOW);
                    break;
                }
            }
            return;
        }
    }
}

// Función para enviar comando a un esclavo específico
void sendCommandToSlave(uint8_t slaveIndex, uint8_t cmd) {
    if (slaveIndex >= NUM_SLAVES) return;
    
    command_packet_t packet;
    packet.command = cmd;
    packet.device_id = slaveIndex;
    
    esp_err_t result = esp_now_send(slaveAddresses[slaveIndex], (uint8_t *)&packet, sizeof(packet));
    
    if (result == ESP_OK) {
        
    } else {
        
    }
}

// Función para enviar comandos a todos los esclavos
void sendCommandToSlaves(uint8_t cmd) {
    for (int i = 0; i < NUM_SLAVES; i++) {
        sendCommandToSlave(i, cmd);
        delay(10); // Pequeña pausa entre envíos
    }
}

// Función para verificar la conexión de todos los esclavos
void checkSlaveConnections() {
    // Reiniciar estado de conexión
    for (int i = 0; i < NUM_SLAVES; i++) {
        slaveConnected[i] = false;
    }
    
    // Enviar comando de verificación a todos los esclavos
    for (int i = 0; i < NUM_SLAVES; i++) {
        sendCommandToSlave(i, 'A');
        delay(50); // Dar tiempo para respuesta
    }
    
    // Esperar respuestas (las respuestas se procesan en el callback)
    delay(500);
    
    // Calcular cuántos esclavos están conectados
    uint8_t slaveCount = sizeof(slaveConnected) / sizeof(slaveConnected[0]);

    // Enviar resultado al script Python
    Serial.write('!'); // Marcador de inicio para mensaje especial
    Serial.write('C'); // Tipo: Connection status
    Serial.write(slaveCount); // Número de esclavos
    
    for (int i = 0; i < NUM_SLAVES; i++) {
        // Enviar el ID del dispositivo
        Serial.write(i + 1);
        // Enviar estado de cada esclavo
        Serial.write(slaveConnected[i] ? 1 : 0);
    }
}

// Tarea para manejar comandos y reportar estado
void serialTask(void *parameter) {
    while (1) {
        // Procesar comandos seriales
        if (Serial.available() > 0) {
            char cmd = Serial.read();
            
            if (cmd == 'S' || cmd == 's') {
                // Iniciar todos los esclavos
                forwarding = true;
                sendCommandToSlaves('S');
            } else if (cmd == 'P' || cmd == 'p') {
                // Detener todos los esclavos
                forwarding = false;
                sendCommandToSlaves('P');
            } else if (cmd == 'A' || cmd == 'a') {
                // Nuevo comando para verificar conexiones
                checkSlaveConnections();
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
            
        } else {
            digitalWrite(STATUS_LED, HIGH);
            delay(500);
            digitalWrite(STATUS_LED, LOW);
        }
    }

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