#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convertidor simple de JSON a CSV para datos de frecuencia cardíaca
"""

import json
import csv
import os
from datetime import datetime

def convert_heart_rate_json_to_csv():
    """Convierte el archivo JSON específico a CSV"""
    
    # Rutas de archivos
    json_file = r"C:\Users\Eloy\Documents\PythonProjects\EMDR-Project\src\data\watch-6-2\9a2c728b-48b3-4ea4-863b-147820173df8.com.samsung.health.exercise.live_data.json"
    csv_file = r"c:\Users\Eloy\Documents\PythonProjects\EMDR-Project\src\pipeline\heart_rate_data.csv"
    
    print("🔄 Iniciando conversión de JSON a CSV...")
    
    # Cargar datos JSON
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"📊 Datos cargados: {len(data)} registros")
    
    # Crear archivo CSV
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Escribir encabezados
        writer.writerow([
            'Fecha',
            'Hora',
            'Frecuencia_Cardiaca_BPM',
            'Timestamp_Original_ms'
        ])
        
        # Procesar cada registro
        for i, record in enumerate(data):
            if 'start_time' in record and 'heart_rate' in record:
                # Convertir timestamp de milisegundos a datetime
                timestamp_ms = record['start_time']
                timestamp_s = timestamp_ms / 1000
                dt = datetime.fromtimestamp(timestamp_s)
                
                # Formatear fecha y hora
                fecha = dt.strftime('%Y-%m-%d')        # 2025-06-30
                hora = dt.strftime('%H:%M:%S')         # 14:30:45
                
                # Escribir fila
                writer.writerow([
                    fecha,
                    hora,
                    record['heart_rate'],
                    timestamp_ms
                ])
            
            # Mostrar progreso
            if (i + 1) % 100 == 0:
                print(f"   Procesados {i + 1} registros...")
    
    print(f"✅ Conversión completada!")
    print(f"📄 Archivo CSV creado: {csv_file}")
    
    # Mostrar primeras líneas como vista previa
    print(f"\n📋 Vista previa del archivo CSV:")
    print("-" * 70)
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for i, row in enumerate(reader):
            if i < 6:  # Mostrar encabezado + 5 filas
                print(" | ".join(f"{cell:>15}" for cell in row))
                if i == 0:
                    print("-" * 70)
            else:
                break
    print("-" * 70)
    
    # Estadísticas básicas
    total_records = len(data)
    heart_rates = [float(record['heart_rate']) for record in data if 'heart_rate' in record]
    
    if heart_rates:
        avg_hr = sum(heart_rates) / len(heart_rates)
        min_hr = min(heart_rates)
        max_hr = max(heart_rates)
        
        first_time = datetime.fromtimestamp(data[0]['start_time'] / 1000)
        last_time = datetime.fromtimestamp(data[-1]['start_time'] / 1000)
        duration_min = (data[-1]['start_time'] - data[0]['start_time']) / (1000 * 60)
        
        print(f"\n📈 ESTADÍSTICAS:")
        print(f"   📊 Total de registros: {total_records}")
        print(f"   🕒 Tiempo inicial: {first_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   🕒 Tiempo final: {last_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   ⏱️  Duración: {duration_min:.1f} minutos")
        print(f"   💓 FC Promedio: {avg_hr:.1f} BPM")
        print(f"   💓 FC Mínima: {min_hr:.0f} BPM")
        print(f"   💓 FC Máxima: {max_hr:.0f} BPM")

if __name__ == '__main__':
    convert_heart_rate_json_to_csv()
