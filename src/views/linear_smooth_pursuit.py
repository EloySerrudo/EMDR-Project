"""
Módulo para el protocolo de estimulación visual Smooth-Pursuit (lineal).

Implementa el paradigma de seguimiento suave con movimiento lineal constante
de LEDs para pruebas de seguimiento ocular continuo en EOG.

Algoritmo de fading para suavizado:
- Cada LED_n se mezcla con LED_{n+1} durante la transición
- 5 sub-frames de 14ms c/u: 80/20, 60/40, 40/60, 20/80, 0/100
- Velocidad objetivo: 17°/s → paso LED cada ~70ms
- Mapeo: LED_idx = 29 + round(angle / DEG_PER_LED), DEG_PER_LED ≈ 1.18°
"""

import time
from PySide6.QtCore import QThread, Signal
from typing import Callable

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTES DEL PROTOCOLO SMOOTH-PURSUIT
# ═══════════════════════════════════════════════════════════════════════════════

# Parámetros geométricos y de hardware
DEG_PER_LED = 1.18           # Grados por LED (1.65cm / 80cm distancia)
LED_CENTER_INDEX = 29        # LED central (0°)
TOTAL_LEDS = 58             # LEDs 0-57

# Parámetros temporales del protocolo
DEFAULT_BASELINE_DURATION = 10.0    # Duración LED central inicial (s)
DEFAULT_SPEED_DEG_S = 17.0          # Velocidad angular objetivo (°/s)
DEFAULT_CYCLES = 3                  # Número de ciclos completos
DEFAULT_PAUSE_DURATION = 0.5        # Pausa entre ciclos (s)

# Parámetros de suavizado (fading)
FADE_SUBFRAMES = 5          # Sub-frames para transición suave
SUBFRAME_DURATION = 0.014   # Duración de cada sub-frame (14ms)

# Rango angular por defecto
DEFAULT_ANGLE_MIN = -20.0   # LED 12 aproximadamente
DEFAULT_ANGLE_MAX = +20.0   # LED 46 aproximadamente

# Color del estímulo (verde)
STIMULUS_COLOR = 0x00FF00


class LinealSmoothPursuitThread(QThread):
    """
    Hilo para ejecutar el protocolo de estimulación Smooth-Pursuit lineal.
    
    Secuencia del protocolo:
    1. LED central 10s (baseline)
    2. 3 ciclos de barrido lineal: derecha → izquierda → derecha...
    3. Velocidad constante 17°/s con fading suave entre LEDs
    4. Pausas de 0.5s entre ciclos
    
    Duración total: ~18 segundos
    """
    
    # Señales Qt para comunicación con la UI
    progress_updated = Signal(int)       # Progreso en porcentaje (0-100)
    sequence_finished = Signal()         # Protocolo completado
    
    def __init__(self, devices, mark_event_callback: Callable[[str], None],
                 angle_min_deg: float = DEFAULT_ANGLE_MIN,
                 angle_max_deg: float = DEFAULT_ANGLE_MAX,
                 speed_deg_s: float = DEFAULT_SPEED_DEG_S,
                 cycles: int = DEFAULT_CYCLES,
                 baseline_s: float = DEFAULT_BASELINE_DURATION,
                 fade_subframes: int = FADE_SUBFRAMES):
        """
        Inicializa el hilo de estimulación Smooth-Pursuit.
        
        Args:
            devices: Instancia de la clase Devices para control de hardware
            mark_event_callback: Función callback para marcar eventos en el CSV
            angle_min_deg: Ángulo mínimo del barrido (°)
            angle_max_deg: Ángulo máximo del barrido (°)
            speed_deg_s: Velocidad angular del barrido (°/s)
            cycles: Número de ciclos completos de barrido
            baseline_s: Duración del LED central inicial (s)
            fade_subframes: Número de sub-frames para fading suave
        """
        super().__init__()
        self.devices = devices
        self.mark_event = mark_event_callback
        
        # Parámetros del protocolo
        self.angle_min = angle_min_deg
        self.angle_max = angle_max_deg
        self.speed_deg_s = speed_deg_s
        self.cycles = cycles
        self.baseline_duration = baseline_s
        self.fade_subframes = fade_subframes
        
        # Estado de control
        self.should_stop = False
        
        # Calcular parámetros derivados
        self.led_min = self.angle_to_led_index(angle_min_deg)
        self.led_max = self.angle_to_led_index(angle_max_deg)
        self.step_duration = DEG_PER_LED / speed_deg_s  # Tiempo por LED (~70ms)
        
        print(f"Smooth-Pursuit configurado:")
        print(f"  Rango angular: {angle_min_deg}° - {angle_max_deg}°")
        print(f"  Rango LEDs: {self.led_min} - {self.led_max}")
        print(f"  Velocidad: {speed_deg_s}°/s → {self.step_duration*1000:.1f}ms/LED")
        print(f"  Ciclos: {cycles}, Baseline: {baseline_s}s")
        
    def angle_to_led_index(self, angle: float) -> int:
        """
        Convierte un ángulo en grados al índice del LED correspondiente.
        
        Args:
            angle: Ángulo en grados (negativo = izquierda, positivo = derecha)
            
        Returns:
            Índice del LED (0-57)
        """
        led_offset = round(angle / DEG_PER_LED)
        led_index = LED_CENTER_INDEX + led_offset
        
        # Asegurar que el índice esté dentro del rango válido
        return max(0, min(TOTAL_LEDS - 1, led_index))
    
    def led_index_to_angle(self, led_index: int) -> float:
        """
        Convierte un índice de LED al ángulo correspondiente.
        
        Args:
            led_index: Índice del LED (0-57)
            
        Returns:
            Ángulo en grados
        """
        led_offset = led_index - LED_CENTER_INDEX
        return led_offset * DEG_PER_LED
    
    def set_led_with_brightness(self, led_index: int, brightness_percent: float):
        """
        Enciende un LED con un porcentaje de brillo específico.
        
        Args:
            led_index: Índice del LED (0-57)
            brightness_percent: Brillo como porcentaje (0-100)
        """
        if 0 <= led_index < TOTAL_LEDS:
            # Calcular color con brillo ajustado
            brightness_factor = brightness_percent / 100.0
            adjusted_color = int(STIMULUS_COLOR * brightness_factor) & 0xFFFFFF
            
            # Encender solo este LED con el brillo especificado
            self.devices.set_led(led_index + 1)  # +1 porque set_led usa 1-58
            if brightness_percent > 0:
                self.devices.set_color(adjusted_color)
            else:
                self.devices.set_color(0x000000)
    
    def fade_transition(self, led_from: int, led_to: int):
        """
        Realiza transición suave con fading entre dos LEDs adyacentes.
        
        Args:
            led_from: LED de origen
            led_to: LED de destino
        """
        # Secuencia de fading: [80/20, 60/40, 40/60, 20/80, 0/100]
        fade_steps = [
            (80, 20),   # 80% LED_from, 20% LED_to
            (60, 40),
            (40, 60),
            (20, 80),
            (0, 100)    # 100% LED_to
        ]
        
        for from_brightness, to_brightness in fade_steps:
            if self.should_stop:
                break
                
            # Apagar todos los LEDs primero
            self.devices.set_led(0)
            
            # Encender LED origen con su brillo
            if from_brightness > 0:
                self.set_led_with_brightness(led_from, from_brightness)
            
            # Encender LED destino con su brillo (si es diferente)
            if to_brightness > 0 and led_to != led_from:
                self.set_led_with_brightness(led_to, to_brightness)
            
            # Esperar sub-frame
            time.sleep(SUBFRAME_DURATION)
    
    def run_baseline(self):
        """Ejecutar fase de baseline con LED central."""
        if self.should_stop:
            return
            
        print(f"Iniciando baseline: LED central por {self.baseline_duration}s")
        
        # Marcar inicio de baseline
        self.mark_event("PURSUIT_BASELINE_ON")
        
        # Encender LED central
        center_led = self.angle_to_led_index(0)
        self.devices.set_led(center_led + 1)  # +1 para API set_led
        
        # Esperar duración de baseline
        start_time = time.time()
        while (time.time() - start_time) < self.baseline_duration and not self.should_stop:
            time.sleep(0.1)  # Check every 100ms
        
        # Marcar fin de baseline
        self.mark_event("PURSUIT_BASELINE_OFF")
        
        print("Baseline completado")
    
    def run_sweep_cycle(self, cycle_num: int):
        """
        Ejecutar un ciclo completo de barrido (derecha → izquierda).
        
        Args:
            cycle_num: Número del ciclo (1-based)
        """
        if self.should_stop:
            return
            
        print(f"Iniciando ciclo {cycle_num}/{self.cycles}")
        
        # Marcar inicio del ciclo
        self.mark_event(f"PURSUIT_CYCLE_START_{cycle_num}")
        
        # === BARRIDO HACIA LA DERECHA (LED_min → LED_max) ===
        for led_idx in range(self.led_min, self.led_max):
            if self.should_stop:
                break
                
            next_led = led_idx + 1
            
            # Marcar eventos en los extremos
            if led_idx == self.led_min:
                angle = self.led_index_to_angle(led_idx)
                self.mark_event("PURSUIT_EDGE_LEFT")
                print(f"  Alcanzado extremo izquierdo: LED {led_idx} ({angle:.1f}°)")
            elif next_led == self.led_max:
                angle = self.led_index_to_angle(next_led)
                self.mark_event("PURSUIT_EDGE_RIGHT")
                print(f"  Alcanzado extremo derecho: LED {next_led} ({angle:.1f}°)")
            
            # Transición suave con fading
            self.fade_transition(led_idx, next_led)
        
        if self.should_stop:
            return
            
        # === BARRIDO HACIA LA IZQUIERDA (LED_max → LED_min) ===
        for led_idx in range(self.led_max, self.led_min, -1):
            if self.should_stop:
                break
                
            next_led = led_idx - 1
            
            # Marcar eventos en los extremos
            if next_led == self.led_min:
                angle = self.led_index_to_angle(next_led)
                self.mark_event("PURSUIT_EDGE_LEFT")
                print(f"  Regreso al extremo izquierdo: LED {next_led} ({angle:.1f}°)")
            
            # Transición suave con fading
            self.fade_transition(led_idx, next_led)
        
        print(f"Ciclo {cycle_num} completado")
    
    def run_pause(self):
        """Ejecutar pausa entre ciclos."""
        if self.should_stop:
            return
            
        print(f"Pausa entre ciclos: {DEFAULT_PAUSE_DURATION}s")
        
        # Apagar todos los LEDs
        self.devices.set_led(0)
        
        # Marcar pausa
        self.mark_event("PURSUIT_PAUSE")
        
        # Esperar duración de pausa
        start_time = time.time()
        while (time.time() - start_time) < DEFAULT_PAUSE_DURATION and not self.should_stop:
            time.sleep(0.1)
    
    def run(self):
        """Ejecuta la secuencia completa del protocolo Smooth-Pursuit."""
        try:
            print("Iniciando protocolo Smooth-Pursuit lineal")
            
            # Configurar color del estímulo
            self.devices.set_color(STIMULUS_COLOR)
            
            # Calcular progreso total
            total_steps = 1 + self.cycles * 2  # baseline + cycles + pausas
            current_step = 0
            
            # === FASE 1: BASELINE ===
            self.run_baseline()
            current_step += 1
            progress = int((current_step / total_steps) * 100)
            self.progress_updated.emit(progress)
            
            if self.should_stop:
                return
                
            # === FASE 2: CICLOS DE BARRIDO ===
            for cycle in range(1, self.cycles + 1):
                if self.should_stop:
                    break
                    
                # Ejecutar ciclo de barrido
                self.run_sweep_cycle(cycle)
                current_step += 1
                progress = int((current_step / total_steps) * 100)
                self.progress_updated.emit(progress)
                
                # Pausa entre ciclos (excepto después del último)
                if cycle < self.cycles and not self.should_stop:
                    self.run_pause()
                    current_step += 1
                    progress = int((current_step / total_steps) * 100)
                    self.progress_updated.emit(progress)
            
            # === FINALIZACIÓN ===
            if not self.should_stop:
                self.mark_event("PURSUIT_FINISHED")
                print("Protocolo Smooth-Pursuit completado exitosamente")
                self.progress_updated.emit(100)
            else:
                print("Protocolo Smooth-Pursuit interrumpido")
                
        except Exception as e:
            print(f"Error en SmoothPursuitThread: {e}")
            
        finally:
            # Asegurar que todos los LEDs estén apagados
            self.devices.set_led(0)
            self.sequence_finished.emit()
    
    def stop(self):
        """Solicita la detención del protocolo."""
        print("Solicitando detención del protocolo Smooth-Pursuit")
        self.should_stop = True
    
    def get_estimated_duration(self) -> float:
        """
        Calcula la duración estimada total del protocolo.
        
        Returns:
            Duración en segundos
        """
        # Baseline
        baseline_time = self.baseline_duration
        
        # Tiempo por ciclo: 2 barridos × (número de LEDs) × tiempo por LED
        leds_per_direction = abs(self.led_max - self.led_min)
        time_per_cycle = 2 * leds_per_direction * self.step_duration
        
        # Tiempo total de barridos
        sweep_time = self.cycles * time_per_cycle
        
        # Pausas entre ciclos
        pause_time = (self.cycles - 1) * DEFAULT_PAUSE_DURATION
        
        total_duration = baseline_time + sweep_time + pause_time
        
        print(f"Duración estimada: {total_duration:.1f}s")
        print(f"  - Baseline: {baseline_time:.1f}s")
        print(f"  - Barridos: {sweep_time:.1f}s ({self.cycles} ciclos)")
        print(f"  - Pausas: {pause_time:.1f}s")
        
        return total_duration
