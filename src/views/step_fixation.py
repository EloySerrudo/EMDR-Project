"""
Módulo para el protocolo de estimulación visual Step-Fixation.

Implementa la secuencia de estimulación visual con LEDs en puntos de fijación
específicos para pruebas de movimientos sacádicos en EOG.
"""

import time
import random
from PySide6.QtCore import QThread, Signal
from typing import List, Callable

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTES DEL PROTOCOLO STEP-FIXATION
# ═══════════════════════════════════════════════════════════════════════════════

# Ángulos de estimulación laterales (sin 0°)
STIMULATION_ANGLES = [-30, -15, 15, 30]

# Tiempos del protocolo (segundos)
LED_ON_DURATION = 5.0          # Tiempo estándar para cada LED
LED_CENTER_DURATION = 15.0 # Duración inicial del LED central

# Configuración física del hardware
LED_CENTER_INDEX = 29      # LED central (0°)
ANGULAR_RESOLUTION = 1.18  # Grados por LED

# Color del estímulo visual (verde)
STIMULUS_COLOR = 0x00FF00


class StepFixationThread(QThread):
    """
    Hilo para ejecutar el protocolo de estimulación Step-Fixation.
    
    Nuevo patrón:
    Centro(10s) → Lateral₁(5s) → Centro(5s) → Lateral₂(5s) → Centro(5s) → 
    Lateral₃(5s) → Centro(5s) → Lateral₄(5s) → Centro_final(5s)
    
    Total: 55 segundos
    """
    
    # Señales Qt para comunicación con la UI
    progress_updated = Signal(int, int)  # (progreso_actual, total_pasos)
    stimulus_started = Signal(int)       # (angulo_actual)
    stimulus_ended = Signal(int)         # (angulo_actual)  
    sequence_finished = Signal()         # Secuencia completada
    
    def __init__(self, devices, mark_event_callback: Callable[[str], None], 
                 angles: List[int] = None):
        """
        Inicializa el hilo de estimulación Step-Fixation.
        
        Args:
            devices: Instancia de la clase Devices para control de hardware
            mark_event_callback: Función callback para marcar eventos en el CSV
            angles: Lista de ángulos laterales (opcional, usa STIMULATION_ANGLES por defecto)
        """
        super().__init__()
        self.devices = devices
        self.mark_event = mark_event_callback
        self.angles = angles if angles is not None else STIMULATION_ANGLES.copy()
        self.should_stop = False
        
    def angle_to_led_index(self, angle: int) -> int:
        """
        Convierte un ángulo en grados al índice del LED correspondiente.
        
        Args:
            angle: Ángulo en grados
            
        Returns:
            Índice del LED (1-58, donde 0 apaga todos los LEDs)
        """
        if angle == 0:
            return LED_CENTER_INDEX
            
        led_offset = round(angle / ANGULAR_RESOLUTION)
        led_index = LED_CENTER_INDEX + led_offset
        
        # Asegurar que el índice esté dentro del rango válido (1-58)
        return max(1, min(58, led_index))
    
    def generate_random_sequence(self) -> List[int]:
        """
        Genera una secuencia aleatoria de los 4 ángulos laterales.
        
        Returns:
            Lista de ángulos laterales en orden aleatorio
        """
        sequence = self.angles.copy()
        random.shuffle(sequence)
        return sequence
    
    def run(self):
        """Ejecuta la secuencia completa del protocolo Step-Fixation."""
        try:
            # Configurar color inicial (verde)
            self.devices.set_color(STIMULUS_COLOR)
            
            # Generar secuencia aleatoria de ángulos laterales
            lateral_sequence = self.generate_random_sequence()
            
            # Calcular total de pasos: 
            # 1 centro inicial + 4 laterales + 4 centros intermedios + 1 centro final = 10 pasos
            total_steps = 1 + len(lateral_sequence) * 2 + 1  # 10 pasos
            current_step = 0
            
            # Marcar inicio del protocolo
            self.mark_event("STEP_FIXATION_START")
            
            # === PASO 1: LED CENTRAL INICIAL (10 segundos) ===
            if self.should_stop:
                return
                
            current_step += 1
            self.progress_updated.emit(current_step, total_steps)
            self.stimulus_started.emit(0)
            
            # Encender LED central
            center_led = self.angle_to_led_index(0)
            self.devices.set_led(center_led)
            self.mark_event("STIMULUS_ANGLE_+00")
            
            # Esperar duración inicial (10 segundos)
            self._sleep_interruptible(LED_CENTER_DURATION)
            
            if self.should_stop:
                return
                
            # === SECUENCIA: LATERAL → CENTRO (4 veces) ===
            for i, angle in enumerate(lateral_sequence):
                if self.should_stop:
                    break
                
                # --- LATERAL (5 segundos) ---
                current_step += 1
                self.progress_updated.emit(current_step, total_steps)
                self.stimulus_started.emit(angle)
                
                # Encender LED lateral
                lateral_led = self.angle_to_led_index(angle)
                self.devices.set_led(lateral_led)
                self.mark_event(f"STIMULUS_ANGLE_{angle:+03d}")
                
                # Esperar duración estándar (5 segundos)
                self._sleep_interruptible(LED_ON_DURATION)
                
                if self.should_stop:
                    break
                
                # --- CENTRO DE RETORNO (5 segundos) ---
                current_step += 1
                self.progress_updated.emit(current_step, total_steps)
                self.stimulus_started.emit(0)
                
                # Encender LED central
                self.devices.set_led(center_led)
                self.mark_event("STIMULUS_ANGLE_+00")
                
                # Esperar duración estándar (5 segundos)
                self._sleep_interruptible(LED_CENTER_DURATION)
                
                if self.should_stop:
                    break
            
            # === PASO FINAL: APAGAR TODOS LOS LEDS ===
            self.devices.set_led(0)  # Apagar todos los LEDs
            
            # Marcar fin del protocolo
            self.mark_event("STEP_FIXATION_END")
            
            print(f"Protocolo Step-Fixation completado. Secuencia utilizada: {lateral_sequence}")
            
        except Exception as e:
            print(f"Error en StepFixationThread: {e}")
        
        finally:
            # Asegurar que todos los LEDs estén apagados
            self.devices.set_led(0)
            self.sequence_finished.emit()
    
    def _sleep_interruptible(self, duration: float):
        """
        Sleep que puede ser interrumpido por should_stop.
        
        Args:
            duration: Duración del sleep en segundos
        """
        start_time = time.time()
        while (time.time() - start_time) < duration and not self.should_stop:
            time.sleep(0.1)  # Sleep en chunks pequeños para permitir interrupción
    
    def stop(self):
        """Solicita la detención del hilo."""
        self.should_stop = True
        
    def get_estimated_duration(self) -> float:
        """
        Calcula la duración estimada total del protocolo.
        
        Returns:
            Duración en segundos
        """
        # Centro inicial: 15s
        # 4 laterales: 4 × 5s = 20s  
        # 4 centros: 4 × 15s = 60s
        return LED_CENTER_DURATION + len(self.angles) * LED_ON_DURATION + len(self.angles) * LED_CENTER_DURATION
