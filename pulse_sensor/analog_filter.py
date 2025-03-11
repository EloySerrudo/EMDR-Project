import numpy as np

DEFAULT_FREQ = 50.0
DEFAULT_RES = 2000

def calculate_capacitors(cap_const, scale):
    cap = cap_const * scale
    if cap < 0.1:
        cap = cap * 1000
        return f'{cap:.2f} n'
    else:
        return f'{cap:.2f} u'



def main(freq=DEFAULT_FREQ, resistor=DEFAULT_RES):
    """Función principal"""
    cap_const = 1 / (2 * np.pi * freq * resistor) * 10**6
    cap_A1 = calculate_capacitors(cap_const, 1.753)
    cap_A2 = calculate_capacitors(cap_const, 1.354)
    cap_A3 = calculate_capacitors(cap_const, 0.4214)
    cap_B1 = calculate_capacitors(cap_const, 3.235)
    cap_B2 = calculate_capacitors(cap_const, 0.309)
    
    if resistor < 1000:
        resistor_str = f'{resistor:.2f} ohm'
    elif resistor < 1E6:
        resistor_str = f'{resistor/1000:.2f} K ohm'
    else:
        resistor_str = f'{resistor/1E6:.2f} M ohm'
    
    print(f"\nComponentes para filtro analógico de frecuencia {freq} Hz y resistencia {resistor_str}:")
    print(f"Capacitor A1: {cap_A1}F")
    print(f"Capacitor A2: {cap_A2}F")
    print(f"Capacitor A3: {cap_A3}F")
    print(f"Capacitor B1: {cap_B1}F")
    print(f"Capacitor B2: {cap_B2}F")


if __name__ == "__main__":
    K = 1E3
    resistors = [100*K, 150*K, 200*K, 220*K, 240*K, 300*K, 360*K, 470*K, 
                 510*K, 620*K, 680*K, 750*K, 820*K, 910*K]
    # resistors = [100*K]
    
    freq = 30.0
    for resistor in resistors:
        main(freq=freq, resistor=resistor)
        print("-----------------------------------------\n")