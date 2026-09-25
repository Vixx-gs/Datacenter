"""
Script para importar el CSV de garantías a Firestore.
Uso: python import_garantias.py <ruta_csv>
"""
import sys
import csv
import re
import os
from google.cloud import firestore

def limpiar_euros(valor: str) -> str:
    if not valor:
        return ""
    limpio = re.sub(r'[€\s]', '', valor).replace(',', '.').strip()
    try:
        return str(round(float(limpio), 2))
    except ValueError:
        return limpio

def limpiar_km(valor: str) -> str:
    if not valor:
        return ""
    return valor.replace('.', '').replace(' ', '').strip()

def normalizar_fecha(valor: str) -> str:
    if not valor:
        return ""
    partes = valor.strip().split('/')
    if len(partes) == 3:
        d, m, a = partes
        return f"{a}-{m.zfill(2)}-{d.zfill(2)}"
    return valor.strip()

def main():
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "GESTION_DE_GARANTIAS.csv"
    if not os.path.exists(csv_path):
        print(f"Archivo no encontrado: {csv_path}")
        sys.exit(1)

    db = firestore.Client()
    col = db.collection("garantias")

    # Agrupar filas por matrícula (puede haber varias por vehículo)
    por_matricula: dict = {}
    with open(csv_path, newline='', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 3:
                continue
            matricula = row[0].strip().upper()
            if not matricula or matricula in ('MATRÍCULA', 'GARANTÍAS VEHÍCULOS'):
                continue

            registro = {
                "marca":              row[1].strip() if len(row) > 1 else "",
                "fecha_matriculacion": normalizar_fecha(row[2]) if len(row) > 2 else "",
                "tipo_garantia":      row[3].strip() if len(row) > 3 else "",
                "fecha_fin_garantia": normalizar_fecha(row[4]) if len(row) > 4 else "",
                "km_fin_garantia":    limpiar_km(row[5]) if len(row) > 5 else "",
                "mantto":             row[6].strip() if len(row) > 6 else "",
                "fecha_fin_mto":      normalizar_fecha(row[7]) if len(row) > 7 else "",
                "km_fin_mto":         limpiar_km(row[8]) if len(row) > 8 else "",
                "precio_mto":         limpiar_euros(row[9]) if len(row) > 9 else "",
                "observaciones":      row[10].strip() if len(row) > 10 else "",
            }
            por_matricula.setdefault(matricula, []).append(registro)

    # Subir a Firestore — un documento por matrícula
    batch = db.batch()
    count = 0
    for matricula, registros in por_matricula.items():
        # Datos del primer registro como campos raíz (el más relevante)
        primero = registros[0]
        doc_data = {**primero, "matricula": matricula, "registros": registros}
        batch.set(col.document(matricula), doc_data)
        count += 1
        if count % 400 == 0:
            batch.commit()
            batch = db.batch()
            print(f"  {count} vehículos procesados...")

    batch.commit()
    print(f"✓ {count} documentos importados a Firestore (colección 'garantias')")

if __name__ == "__main__":
    main()
