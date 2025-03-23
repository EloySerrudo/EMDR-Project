#ifndef CIRCULAR_BUFFER_H
#define CIRCULAR_BUFFER_H

#include <Arduino.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

// Estructura del paquete de datos
struct DataPacket {
    uint32_t id;        // Identificador único del dato
    uint32_t timestamp; // Marca de tiempo en milisegundos
    int16_t value;      // Valor del sensor (ej. ADS1115)
};

class CircularBuffer {
private:
    DataPacket* buffer;      // Buffer para almacenar paquetes de datos
    uint16_t bufferSize;     // Tamaño del buffer (cambiado de int a uint16_t)
    volatile uint16_t head = 0;    // Índice de escritura
    volatile uint16_t tail = 0;    // Índice de lectura
    volatile uint16_t count = 0;   // Cantidad de elementos en buffer
    volatile uint32_t ID = 0;     // ID único incremental para los paquetes
    portMUX_TYPE mutex;      // Mutex para thread safety

public:
    CircularBuffer(uint16_t size);  // Cambiado de int a uint16_t
    ~CircularBuffer();

    bool write(int16_t value, uint32_t time); // Escribir valor con timestamp automático
    bool read(DataPacket* packet);     // Leer un paquete completo
    uint16_t available();              // Cantidad de elementos disponibles
};

#endif
