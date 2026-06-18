"""
sync_sheets.py  –  Sincroniza Google Sheets → Firebase Firestore
Ejecutar con: python sync_sheets.py
Sustituye al antiguo sync_sheets.py que escribía en PostgreSQL.
"""
import csv, io, sys, urllib.request, uuid
from datetime import datetime
from pathlib import Path

# Forzar UTF-8 en stdout
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from google.cloud import firestore
from google.oauth2.service_account import Credentials

_BASE  = Path(__file__).parent
_SA    = _BASE / "ai-studio-applet-webapp-55a1a-firebase-adminsdk-fbsvc-67d511e6d4.json"
_creds = Credentials.from_service_account_file(str(_SA))
db     = firestore.Client(
    project     = "ai-studio-applet-webapp-55a1a",
    credentials = _creds,
    database    = "ai-studio-7801edee-96c4-47bb-8194-68abcf65e834",
)

# ─── URLs Google Sheets ───────────────────────────────────────────────────────
_DC  = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSryhAruJS1FpMgGVHUe6qnYfbIt3_qUWy10s3a5-vVReJpmZB5SIo_drLziXVf8PjCQyyJ1EPMjVfR/pub?single=true&output=csv"
_SEG = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTLyHazuC46Ld7iKm7ehu6gwVpMuT_E1wkE6KWQv_6nRaAB5KS19bnFeRKBo2ycVcP5_TU9cOz-KLXq/pub?single=true&output=csv"
_FIN = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRubGv6OUV1t1zs6Uo8ACs3xQhF_4vZLuJTNO3pLacR2iejX6oNQc6orPFMhAP2kf4kumCn_ael6qGU/pub?single=true&output=csv"

URL_VEHICULOS    = f"{_DC}&gid=972014913"
URL_CLIENTES     = f"{_DC}&gid=1341381949"
URL_HISTORIAL    = f"{_DC}&gid=1746464690"
URL_SEGUROS      = f"{_SEG}&gid=702011553"
URL_ASEGURADORAS = f"{_SEG}&gid=1750903629"
URL_FINANCIERAS  = f"{_FIN}&gid=0"
URL_CONTRATOS    = f"{_FIN}&gid=28649955"

EMPRESAS_VALIDAS = {"ECOTRANSPORTE", "TRANSCOOP", "CENTRALCOOP"}
BATCH_SIZE       = 400  # Firestore: máx 500 ops por batch

# ─── Utilidades ───────────────────────────────────────────────────────────────

def fetch_csv(url: str) -> list:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        content = r.read().decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(content)))

def clean(val) -> str:
    return val.strip() if val else ""

def clean_float(val):
    v = clean(val).replace(".", "").replace(",", ".").replace("€", "").replace(" ", "")
    try: return float(v) if v else None
    except: return None

def clean_int(val):
    v = clean(val)
    try: return int(v) if v else None
    except: return None

def normalize_date(val: str) -> str:
    """Convierte cualquier formato de fecha a YYYY-MM-DD."""
    if not val or not val.strip(): return ""
    s = val.strip()
    if "T" in s: s = s.split("T")[0]
    parts = s.replace("-", "/").split("/")
    if len(parts) == 3:
        if len(parts[0]) == 4:   # YYYY-MM-DD
            return f"{parts[0]}-{parts[1].zfill(2)}-{parts[2].zfill(2)}"
        else:                     # DD/MM/YYYY
            y = parts[2]
            if len(y) == 2: y = ("19" + y) if int(y) > 30 else ("20" + y)
            return f"{y}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
    return s

def normalize_mat(m: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFD", m or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return "".join(c for c in s.upper() if c.isalnum())

def upsert_batch(collection: str, docs: list):
    """Escribe docs en Firestore en batches. Cada doc debe tener '_id'."""
    total = 0
    for i in range(0, len(docs), BATCH_SIZE):
        batch = db.batch()
        for doc in docs[i:i + BATCH_SIZE]:
            doc_id = doc.pop("_id", "")
            if not doc_id: continue
            batch.set(db.collection(collection).document(doc_id), doc, merge=True)
            total += 1
        batch.commit()
    return total

# ─── Funciones de sincronización ──────────────────────────────────────────────

def sync_vehiculos(rows: list):
    print(f"  Vehículos: {len(rows)} filas")
    docs = []
    for row in rows:
        mat = normalize_mat(clean(row.get("Matrícula", "")))
        if not mat: continue
        docs.append({
            "_id":                mat,
            "matricula":          mat,
            "marca":              clean(row.get("Marca", "")),
            "modelo":             clean(row.get("Modelo", "")),
            "bastidor":           clean(row.get("Bastidor", "")),
            "fechaMat":           normalize_date(clean(row.get("FechaMat.", ""))),
            "destinadoA":         clean(row.get("Destinado a", "")),
            "propiedad":          clean(row.get("Propiedad", "")),
            "situacion":          clean(row.get("Situación", "")),
            "estado":             clean(row.get("Estado", "ACTIVO")) or "ACTIVO",
            "fechaIncorporacion": normalize_date(clean(row.get("Fecha Incorporación", "") or row.get("FechaIncorporación", ""))),
            "itv":                normalize_date(clean(row.get("ITV", ""))),
            "tacografo":          normalize_date(clean(row.get("Tacógrafo", "") or row.get("Tacografo", ""))),
            "mantenimiento":      clean(row.get("Mantenimiento", "")).upper() in ("SI", "S", "1", "TRUE", "YES"),
            "fechaFinMto":        normalize_date(clean(row.get("FechaFinMto", ""))),
            "kmFinMto":           clean_float(row.get("KmFinMto", "")) or 0,
            "precioMto":          clean_float(row.get("PrecioMto", "")) or 0,
            "garantia":           clean(row.get("Garantia", "")).upper() in ("SI", "S", "1", "TRUE", "YES"),
            "fechaFinGarantia":   normalize_date(clean(row.get("FechaFinGarantia", ""))),
            "kmFinGarantia":      clean_float(row.get("KmFinGarantia", "")) or 0,
            "kilometros":         clean_float(row.get("Kilómetros", "")) or 0,
            "equipamiento":       clean(row.get("Equipamiento", "")),
            "observaciones":      clean(row.get("Observaciones", "")),
        })
    n = upsert_batch("vehicles", docs)
    print(f"  ✓ {n} vehículos actualizados en Firestore")

def sync_clientes(rows_clientes: list, rows_historial: list):
    print(f"  Clientes: {len(rows_clientes)} filas")

    # Mapa de historial: conductor_id → lista de asignaciones
    hist_map: dict = {}
    for row in rows_historial:
        cid = clean(row.get("ConductorID", ""))
        if not cid: continue
        hist_map.setdefault(cid, []).append({
            "vehiculo_id":  clean(row.get("VehículoID", "") or row.get("VehiculoID", "")),
            "fecha_inicio": clean(row.get("FechaInicio", "")),
            "fecha_fin":    clean(row.get("FechaFin", "")),
        })

    def parse_fecha(f: str):
        if not f: return None
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
            try: return datetime.strptime(f.strip(), fmt)
            except: pass
        return None

    docs = []
    omitidos = 0
    ids_validos = set()

    for row in rows_clientes:
        id_c = clean(row.get("ID", ""))
        if not id_c: continue

        estado_raw = clean(row.get("Estado", "")).lower()
        situacion  = clean(row.get("Situación", "")).lower()
        empresa    = clean(row.get("Empresa", "")).upper()

        if estado_raw not in ("confirmado", "ex-socio", "ex socio", "exsocio") \
           and situacion not in ("definitivo", "perdido", "baja"):
            omitidos += 1
            continue
        if empresa not in EMPRESAS_VALIDAS:
            omitidos += 1
            continue

        ids_validos.add(id_c)

        if estado_raw == "confirmado" and situacion == "definitivo":
            estado_final = "Confirmado"
        elif estado_raw in ("ex-socio", "ex socio", "exsocio") or situacion in ("perdido", "baja"):
            estado_final = "Ex-socio"
        else:
            estado_final = clean(row.get("Estado", "")) or "Confirmado"

        fecha_baja = clean(row.get("FECHA BAJA", ""))
        if fecha_baja:
            fb_dt = parse_fecha(fecha_baja)
            if fb_dt:
                for r in hist_map.get(id_c, []):
                    fi = parse_fecha(r["fecha_inicio"])
                    if fi and fi > fb_dt:
                        fecha_baja = ""
                        break

        docs.append({
            "_id":             id_c,
            "nombre":          clean(row.get("Nombre", "")),
            "nombrePropio":    clean(row.get("NOMBRE PROPIO", "")),
            "apellidos":       clean(row.get("APELLIDOS", "")),
            "nif":             clean(row.get("NIF", "")) or id_c,
            "numTarjConductor":clean(row.get("NUM_TARJ_CONDUCTOR", "")),
            "movil":           clean(row.get("Móvil", "")),
            "email":           clean(row.get("Email", "")),
            "empresa":         clean(row.get("Empresa", "")),
            "gestor":          clean(row.get("GESTOR", "") or row.get("Comercial", "")),
            "estado":          estado_final,
            "fechaAlta":       normalize_date(clean(row.get("Fecha Alta", ""))),
            "fechaIngreso":    normalize_date(clean(row.get("Fecha prevista", ""))),
            "fechaBaja":       normalize_date(fecha_baja),
            "fechaNacimiento": normalize_date(clean(row.get("FECHA NACIMIENTO", ""))),
            "codigo":          clean(row.get("CODIGO", "")),
            "situacion":       clean(row.get("Situación", "")),
            "direccion":       clean(row.get("DIRECCION", "")),
            "poblacion":       clean(row.get("POBLACION", "")),
            "codigoP":         clean(row.get("CODIGO P.", "")),
            "provincia":       clean(row.get("PROVINCIA", "")),
        })

    n = upsert_batch("clients", docs)
    print(f"  ✓ {n} clientes actualizados, {omitidos} omitidos")

def sync_historial(rows: list):
    """Sincroniza driverAssignments y actualiza conductorActual en vehicles."""
    print(f"  HistorialVehiculo: {len(rows)} filas")
    docs = []
    vehiculo_map: dict = {}  # vehiculo_id → lista de asignaciones

    for row in rows:
        id_hist     = clean(row.get("ID", ""))
        vehiculo_id = normalize_mat(clean(row.get("VehículoID", "") or row.get("VehiculoID", "")))
        conductor_id= clean(row.get("ConductorID", ""))
        if not vehiculo_id or not id_hist: continue

        fecha_fin = clean(row.get("FechaFin", ""))
        docs.append({
            "_id":         id_hist,
            "vehicleId":   vehiculo_id,
            "driverId":    conductor_id,
            "driverName":  conductor_id,
            "fechaInicio": normalize_date(clean(row.get("FechaInicio", ""))),
            "fechaFin":    normalize_date(fecha_fin),
            "accion":      clean(row.get("Acción", "") or row.get("Accion", "")),
            "observaciones": clean(row.get("Observaciones", "")),
        })
        vehiculo_map.setdefault(vehiculo_id, []).append({
            "conductor_id": conductor_id,
            "fecha_fin":    fecha_fin,
            "fecha_inicio": clean(row.get("FechaInicio", "")),
        })

    n = upsert_batch("driverAssignments", docs)
    print(f"  ✓ {n} asignaciones actualizadas")

    # Actualizar conductorActual en vehicles basado en el historial
    actualizados = 0
    for mat, registros in vehiculo_map.items():
        activo = next((r for r in registros if not r["fecha_fin"] and r["conductor_id"]), None)
        if activo:
            conductor_nombre = activo["conductor_id"]
        else:
            con_fecha = [r for r in registros if r["fecha_fin"] and r["conductor_id"]]
            if not con_fecha: continue
            ultimo = sorted(con_fecha, key=lambda x: x["fecha_fin"], reverse=True)[0]
            conductor_nombre = ultimo["conductor_id"]
        try:
            db.collection("vehicles").document(mat).update({"conductorActual": conductor_nombre})
            actualizados += 1
        except Exception:
            pass
    print(f"  ✓ conductorActual actualizado en {actualizados} vehículos")

def sync_seguros(rows_seguros: list, rows_aseguradoras: list):
    print(f"  Seguros: {len(rows_seguros)} filas")
    aseg_map = {
        clean(r.get("ID_Aseguradora", "")): clean(r.get("Aseguradora", ""))
        for r in rows_aseguradoras
        if clean(r.get("ID_Aseguradora", ""))
    }
    docs = []
    omitidos = 0
    for row in rows_seguros:
        estado = clean(row.get("Estado", "")).upper()
        if estado != "ACTIVO":
            omitidos += 1
            continue
        doc_id = clean(row.get("ID", "")) or clean(row.get("Nº de Póliza", ""))
        if not doc_id: continue
        aseg_id = clean(row.get("Aseguradora_ID", ""))
        doc_data = dict(row)  # guardar campos en español tal cual vienen del sheet
        doc_data["_id"]        = doc_id
        doc_data["Aseguradora"] = aseg_map.get(aseg_id, aseg_id)
        docs.append(doc_data)
    n = upsert_batch("insurancePolicies", docs)
    print(f"  ✓ {n} seguros actualizados, {omitidos} omitidos")

def sync_financieras(rows: list):
    print(f"  Financieras: {len(rows)} filas")
    docs = []
    for row in rows:
        doc_id = clean(row.get("FinAcuerdoID", ""))
        if not doc_id: continue
        doc_data = dict(row)
        doc_data["_id"] = doc_id
        docs.append(doc_data)
    n = upsert_batch("financialAgreements", docs)
    print(f"  ✓ {n} financieras actualizadas")

def sync_contratos(rows: list):
    print(f"  Contratos: {len(rows)} filas")
    docs = []
    for row in rows:
        doc_id = clean(row.get("AlqContratoID", ""))
        if not doc_id: continue
        doc_data = dict(row)
        doc_data["_id"] = doc_id
        docs.append(doc_data)
    n = upsert_batch("rentalContracts", docs)
    print(f"  ✓ {n} contratos actualizados")

# ─── Main ─────────────────────────────────────────────────────────────────────

def sync_all():
    sep = "=" * 52
    print(f"\n{sep}")
    print(f"  Sync Firestore: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"{sep}")

    print("\n[0/6] Descargando historial y clientes...")
    rows_historial = fetch_csv(URL_HISTORIAL)
    rows_clientes  = fetch_csv(URL_CLIENTES)

    print("\n[1/6] Vehículos...")
    sync_vehiculos(fetch_csv(URL_VEHICULOS))

    print("\n[2/6] Clientes...")
    sync_clientes(rows_clientes, rows_historial)

    print("\n[3/6] Seguros...")
    sync_seguros(fetch_csv(URL_SEGUROS), fetch_csv(URL_ASEGURADORAS))

    print("\n[4/6] Financieras...")
    sync_financieras(fetch_csv(URL_FINANCIERAS))

    print("\n[5/6] Contratos...")
    sync_contratos(fetch_csv(URL_CONTRATOS))

    print("\n[6/6] Historial / driverAssignments...")
    sync_historial(rows_historial)

    print(f"\n✓ Completado: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")

if __name__ == "__main__":
    sync_all()
