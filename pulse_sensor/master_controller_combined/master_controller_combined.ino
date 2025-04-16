#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <WiFi.h>
#include <esp_now.h>
#include <esp_system.h>

// Configuración de LED y botones
#define STATUS_LED 22       // LED integrado del ESP32
#define PACKET_HEADER 0xAA55  // Header para paquetes de datos
#define PACKET_SIZE 15        // Tamaño del paquete del sensor

// Variables globales
bool forwarding = true;       // Indicador para reenviar datos al PC

// Direcciones MAC de los dispositivos esclavos
uint8_t slaveAddresses[][6] = {
    {0xA0, 0xB7, 0x65, 0x55, 0xF3, 0x30}, // MAC del sensor de pulso (ID 1)
    {0xA0, 0xA3, 0xB3, 0xAA, 0x33, 0xA4}  // MAC de la lightbar (ID 2)
    // Puedes añadir más dispositivos aquí
};

#define NUM_SLAVES (sizeof(slaveAddresses) / sizeof(slaveAddresses[0]))

// Control de estado de los esclavos
bool slaveConnected[NUM_SLAVES] = {false};

// Estructura para recibir datos del sensor
typedef struct esp_now_packet {
    uint16_t header;
    uint32_t id;
    uint32_t timestamp;
    int16_t value_0;
    int16_t value_1;
    uint8_t device_id;
} esp_now_packet_t;

// Estructura para enviar comandos a los esclavos
typedef struct command_packet {
    uint8_t command;
    uint8_t device_id;
} command_packet_t;

// Estructura para enviar comandos al lightbar
typedef struct lightbar_command {
    char cmd;
    uint8_t data1;
    uint8_t data2;
    uint8_t data3;
} lightbar_command_t;

// Estructura para recibir confirmación
typedef struct ack_packet {
    uint8_t command;
    uint8_t device_id;
    uint8_t status;
} ack_packet_t;

// Buffer para reensamblar paquetes para serial
uint8_t serialPacket[PACKET_SIZE];

// Variables de estado
volatile bool lastCommandSent = true;

// Información del peer para ESP-NOW
esp_now_peer_info_t peerInfo;

// Callback cuando se envía un paquete
void onSentEspNowData(const uint8_t *mac_addr, esp_now_send_status_t status) {
    lastCommandSent = (status == ESP_NOW_SEND_SUCCESS);
}

// Callback cuando se reciben datos
void onReceivedEspNowData(const uint8_t *mac_addr, const uint8_t *data, int data_len) {
    // 1. Verificar si es un paquete del sensor de pulso
    if (data_len == sizeof(esp_now_packet_t)) {
        esp_now_packet_t *packet = (esp_now_packet_t*)data;
        
        if (packet->header == PACKET_HEADER && forwarding) {
            // Reenviar datos al PC en formato binario
            serialPacket[0] = PACKET_HEADER & 0xFF;
            serialPacket[1] = (PACKET_HEADER >> 8) & 0xFF;
            
            serialPacket[2] = packet->id & 0xFF;
            serialPacket[3] = (packet->id >> 8) & 0xFF;
            serialPacket[4] = (packet->id >> 16) & 0xFF;
            serialPacket[5] = (packet->id >> 24) & 0xFF;
            
            serialPacket[6] = packet->timestamp & 0xFF;
            serialPacket[7] = (packet->timestamp >> 8) & 0xFF;
            serialPacket[8] = (packet->timestamp >> 16) & 0xFF;
            serialPacket[9] = (packet->timestamp >> 24) & 0xFF;
            
            serialPacket[10] = packet->value_0 & 0xFF;
            serialPacket[11] = (packet->value_0 >> 8) & 0xFF;
            
            serialPacket[12] = packet->value_1 & 0xFF;
            serialPacket[13] = (packet->value_1 >> 8) & 0xFF;
            
            serialPacket[14] = packet->device_id;
            
            Serial.write(serialPacket, PACKET_SIZE);
        }
    }
    // 2. Verificar si es una confirmación de conexión
    else if (data_len == sizeof(ack_packet_t)) {
        ack_packet_t *ackPacket = (ack_packet_t*)data;
        if (ackPacket->command == 'A') {
            uint8_t deviceId = ackPacket->device_id;
            
            // Buscar a qué dispositivo pertenece esta confirmación
            for (int i = 0; i < NUM_SLAVES; i++) {
                if (memcmp(mac_addr, slaveAddresses[i], 6) == 0) {
                    slaveConnected[i] = true;
                    // Indicar visualmente que recibimos respuesta
                    // digitalWrite(STATUS_LED, HIGH);
                    // delay(50);
                    // digitalWrite(STATUS_LED, LOW);
                    break;
                }
            }
        }
    }
}

// Función para enviar comando al sensor (start, pause, check)
void sendCommandToSlave(uint8_t slaveIndex, uint8_t cmd) {
    if (slaveIndex >= NUM_SLAVES) return;
    
    command_packet_t packet;
    packet.command = cmd;
    packet.device_id = slaveIndex + 1; // Convertir índice a ID de dispositivo
    
    esp_now_send(slaveAddresses[slaveIndex], (uint8_t *)&packet, sizeof(packet));
}

// Función para enviar comando específico al lightbar
void sendCommandToLightbar(char cmd, uint8_t data1, uint8_t data2, uint8_t data3) {
    lightbar_command_t packet;
    packet.cmd = cmd;
    packet.data1 = data1;
    packet.data2 = data2;
    packet.data3 = data3;
    
    esp_now_send(slaveAddresses[1], (uint8_t *)&packet, sizeof(packet));
}

// Función para verificar la conexión de todos los esclavos
void checkSlaveConnections() {
    // Reiniciar estado de conexión
    for (int i = 0; i < NUM_SLAVES; i++) {
        slaveConnected[i] = false;
    }
    
    // Enviar comando de verificación a cada esclavo
    for (int i = 0; i < NUM_SLAVES; i++) {
        if (i == 1) {
            // Para el lightbar
            lightbar_command_t packet;
            packet.cmd = 'a';
            packet.data1 = 0;
            packet.data2 = 0;
            packet.data3 = 0;
            esp_now_send(slaveAddresses[1], (uint8_t *)&packet, sizeof(packet));
        } else {
            // Para el sensor de pulso
            sendCommandToSlave(i, 'A');
        }
        delay(50);
    }
    
    // Esperar respuestas
    delay(500);
    digitalWrite(STATUS_LED, LOW);
    
    // Enviar resultado al PC
    Serial.write('!');
    Serial.write('C');
    Serial.write(NUM_SLAVES);
    
    for (int i = 0; i < NUM_SLAVES; i++) {
        Serial.write(i + 1);
        Serial.write(slaveConnected[i] ? 1 : 0);
    }
}

// Tarea para manejar comandos seriales
void serialTask(void *parameter) {
    uint8_t packetBuffer[4];
    
    while (1) {
        // Procesar comandos recibidos del PC
        // Comandos para el lightbar (requieren 4 bytes)
        if (Serial.available() >= 4) {
            // Procesar como comando de lightbar
            if (Serial.readBytes(packetBuffer, 4) == 4) {
                // Si es comando de identificación, responder directamente sin enviar por ESP-NOW
                if (packetBuffer[0] == 'i') {
                    // Responder con los dispositivos disponibles
                    Serial.println("EMDR Master Controller");
                    // for (int i = 0; i < NUM_SLAVES; i++) {
                    //     Serial.print("Device ");
                    //     Serial.print(i+1);
                    //     Serial.print(": ");
                    //     Serial.println(slaveConnected[i] ? "Connected" : "Disconnected");
                    // }
                } else if (packetBuffer[0] == 'A') {
                  checkSlaveConnections();
                } else {
                    // Enviar cualquier otro comando al lightbar
                    sendCommandToLightbar(packetBuffer[0], 
                                          packetBuffer[1], 
                                          packetBuffer[2], 
                                          packetBuffer[3]);
                }
            }
        }
        else if (Serial.available() > 0) {
            char cmd = Serial.peek(); // Ver el comando sin consumirlo
            
            // Comandos de control para el sensor
            if (cmd == 'S' || cmd == 's') {
                Serial.read(); // Consumir el comando
                forwarding = true;
                sendCommandToSlave(0, 'S');
            } 
            else if (cmd == 'P' || cmd == 'p') {
                Serial.read(); // Consumir el comando
                forwarding = false;
                sendCommandToSlave(0, 'P');
            } 
            // else if (cmd == 'A' || cmd == 'a') {
            //     Serial.read(); // Consumir el comando
            //     checkSlaveConnections();
            // }
        }
        // Esperar un poco para no saturar la CPU
        vTaskDelay(10);
    }
}

void setup() {
    // Inicializar Serial
    Serial.begin(115200);
    delay(1000);
    
    // Configurar LED
    pinMode(STATUS_LED, OUTPUT);
    digitalWrite(STATUS_LED, HIGH); // En el WEMOS LOLIN32 Lite este led actua con lógica inversa
    
    // Inicializar WiFi en modo STA
    WiFi.mode(WIFI_STA);
    
    // Inicializar ESP-NOW
    if (esp_now_init() != ESP_OK) {
        return;
    }
    
    // Registrar callbacks
    esp_now_register_recv_cb(onReceivedEspNowData);
    esp_now_register_send_cb(onSentEspNowData);
    
    // Registrar todos los dispositivos esclavos como peers
    for (uint8_t i = 0; i < NUM_SLAVES; i++) {
        memcpy(peerInfo.peer_addr, slaveAddresses[i], 6);
        peerInfo.channel = 0;
        peerInfo.encrypt = false;
        
        esp_now_add_peer(&peerInfo);
    }

    // Crear tarea para manejar comandos seriales
    TaskHandle_t serialTaskHandle = NULL;
    xTaskCreatePinnedToCore(
        serialTask,
        "Serial_Task",
        4096,
        NULL,
        1,
        &serialTaskHandle,
        1);
}

void loop() {
    // Todo se maneja en tareas
    delay(1000);
}