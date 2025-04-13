/*
 * EMDR Lightbar controller for ESP32
 * Equivalent functionality to the MicroPython main.py script
 */

 #include <Adafruit_NeoPixel.h>

 #define PIN_LED       13    // Pin para controlar el NeoPixel strip
 #define PIN_LED_ERROR 23    // LED para indicar errores
 #define NUMLED        60    // Número de LEDs en la tira
 #define PACKET_SIZE   4     // Tamaño fijo del paquete (comando + 3 bytes)
 
 // Inicialización de la tira NeoPixel
 Adafruit_NeoPixel strip = Adafruit_NeoPixel(NUMLED, PIN_LED, NEO_GRB + NEO_KHZ800);
 
 // Variables para el control de color y LED
 uint8_t red = 0x0F;
 uint8_t green = 0;
 uint8_t blue = 0;
 
 void setup() {
   // Inicialización de la comunicación serie
   Serial.begin(115200);
   
   // Inicialización de la tira NeoPixel
   strip.begin();
   strip.clear();
   strip.show();
   
   // Configuración del pin de error
   pinMode(PIN_LED_ERROR, OUTPUT);
   digitalWrite(PIN_LED_ERROR, LOW);
   
   // Mostrar patrón de prueba inicial
   test();
 }
 
 void loop() {
   // Usar un buffer para los 4 bytes (comando + datos)
   uint8_t packetBuffer[PACKET_SIZE];
   
   // Verificar si hay al menos PACKET_SIZE bytes disponibles
   if (Serial.available() >= PACKET_SIZE) {
     // Leer el paquete completo de PACKET_SIZE bytes
     if (Serial.readBytes(packetBuffer, PACKET_SIZE) == PACKET_SIZE) {
       // Extraer el comando (primer byte) y procesar
       char cmd = packetBuffer[0];
       uint8_t ledNum;
       switch (cmd) {
         case 'c': // Comando de color (0x63)
           // Los 3 bytes siguientes son para RGB
           red = packetBuffer[1];
           green = packetBuffer[2];
           blue = packetBuffer[3];
           break;
           
         case 'l': // Comando de LED (0x6C)
           // El segundo byte es para la posición, ignorar bytes 3 y 4
           ledNum = packetBuffer[1];
           
           clearLEDs();
           if (ledNum > 0 && ledNum <= NUMLED) {
             strip.setPixelColor(ledNum - 1, strip.Color(red, green, blue));
           }
           strip.show();
           break;
           
         case 't': // Comando test (0x74)
           // Ignorar los 3 bytes adicionales
           clearLEDs();
           strip.setPixelColor(0, strip.Color(red, green, blue));
           strip.setPixelColor(NUMLED - 1, strip.Color(red, green, blue));
           strip.show();
           break;
           
         case 'i': // Comando id (0x69)
           // Ignorar los 3 bytes adicionales
           Serial.println("EMDR Lightbar");
           break;
       }
     }
   }
 }
 
 // Función para limpiar todos los LEDs
 void clearLEDs() {
   strip.clear();
 }
 
 // Función para probar la tira de LEDs al inicio
 void test() {
   clearLEDs();
   strip.setPixelColor(0, strip.Color(0, 0x20, 0));
   strip.setPixelColor(NUMLED - 1, strip.Color(0x20, 0, 0));
   strip.show();
   delay(500);
   clearLEDs();
   strip.show();
 }
