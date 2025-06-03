# Lista de 16 colores desde fríos a cálidos con sus temperaturas en Kelvin
colores = [
    {"nombre": "Rojo Profundo",       "hex": "#8B0000", "kelvin": 1500},
    {"nombre": "Rojo",                "hex": "#FF0000", "kelvin": 2000},
    {"nombre": "Vela",                "hex": "#FF4500", "kelvin": 1500},
    {"nombre": "Incandescente baja",  "hex": "#FF6B00", "kelvin": 2000},
    {"nombre": "Incandescente alta",  "hex": "#FF8C00", "kelvin": 2500},
    {"nombre": "Amarillo",            "hex": "#FFFF00", "kelvin": 4000},
    {"nombre": "Dorado",              "hex": "#FFD700", "kelvin": 5000},
    {"nombre": "Ámbar",               "hex": "#FFBF00", "kelvin": 5500},
    {"nombre": "Azul Cielo",          "hex": "#87CEEB", "kelvin": 6000},
    {"nombre": "Azul Acero",          "hex": "#4682B4", "kelvin": 6500},
    {"nombre": "Azul Real",           "hex": "#4169E1", "kelvin": 8000},
    {"nombre": "Azul Profundo",       "hex": "#0000FF", "kelvin": 10000},
    {"nombre": "Azul Púrpura",        "hex": "#6A5ACD", "kelvin": 12000},
    {"nombre": "Índigo",              "hex": "#4B00CD", "kelvin": 14000},
    {"nombre": "Violeta",             "hex": "#8A2BE2", "kelvin": 16000},
    {"nombre": "Púrpura Profundo",    "hex": "#4B0082", "kelvin": 18000}
]


# Imprimir la lista de colores con sus temperaturas
print("=== COLORES DE FRÍOS A CÁLIDOS ===\n")
for i, color in enumerate(colores, 1):
    print(f"{i:2d}. {color['nombre']:<15} | {color['hex']:<7} | {color['kelvin']:,} K")

print(f"\nTotal de colores: {len(colores)}")