#include "CircularBuffer.h"

CircularBuffer::CircularBuffer(uint16_t size) : bufferSize(size) {  // Cambiado de int a uint16_t
    buffer = new DataPacket[bufferSize];
    mutex = portMUX_INITIALIZER_UNLOCKED; // Inicializar el mutex
}

CircularBuffer::~CircularBuffer() {
    delete[] buffer;
}

bool CircularBuffer::write(int16_t value, uint32_t time) {
    bool overflow = false;
    portENTER_CRITICAL(&mutex);
    
    // Crear un nuevo paquete de datos con ID y timestamp relativo
    buffer[head].id = ID;
    buffer[head].timestamp = time;  // Timestamp relativo al inicio de captura
    buffer[head].value = value;
    
    // Actualizar índice de escritura
    head = (head + 1) % bufferSize;
    ID++;
    
    // Si el buffer no está lleno, incrementar contador
    if (count < bufferSize) {
        count++;
    } else {
        // El buffer está lleno, sobrescribir el dato más antiguo
        // y mover el índice de lectura
        tail = (tail + 1) % bufferSize;
        overflow = true;  // Indicar que hubo sobrescritura
    }

    portEXIT_CRITICAL(&mutex);
    return overflow;  // Devolver si hubo sobrescritura
}

bool CircularBuffer::read(DataPacket* packet) {
    bool result = false;
    portENTER_CRITICAL(&mutex);
    if (count > 0) {
        // Copiar todo el paquete de datos
        *packet = buffer[tail];
        tail = (tail + 1) % bufferSize;
        count--;
        result = true;
    }
    portEXIT_CRITICAL(&mutex);
    return result;
}

uint16_t CircularBuffer::available() {
    portENTER_CRITICAL(&mutex);
    uint16_t available = count;
    portEXIT_CRITICAL(&mutex);
    return available;
}
