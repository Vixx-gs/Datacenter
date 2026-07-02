import csv
import io
import sys
import urllib.request
from datetime import datetime
from database import SessionLocal

# Forzar UTF-8 en stdout para evitar errores con caracteres especiales en Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
import models

BASE_DATACENTER  = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSryhAruJS1FpMgGVHUe6qnYfbIt3_qUWy10s3a5-vVReJpmZB5SIo_drLziXVf8PjCQyyJ1EPMjVfR/pub?single=true&output=csv"
BASE_SEGUROS     = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTLyHazuC46Ld7iKm7ehu6gwVpMuT_E1wkE6KWQv_6nRaAB5KS19bnFeRKBo2ycVcP5_TU9cOz-KLXq/pub?single=true&output=csv"
BASE_FINANCIERAS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRubGv6OUV1t1zs6Uo8ACs3xQhF_4vZLuJTNO3pLacR2iejX6oNQc6orPFMhAP2kf4kumCn_ael6qGU/pub?single=true&output=csv"

URL_VEHICULOS   = f"{BASE_DATACENTER}&gid=972014913"
URL_CLIENTES    = f"{BASE_DATACENTER}&gid=1341381949"
URL_HISTORIAL   = f"{BASE_DATACENTER}&gid=1746464690"
URL_SEGUROS      = f"{BASE_SEGUROS}&gid=702011553"
URL_ASEGURADORAS = f"{BASE_SEGUROS}&gid=1750903629"
URL_FINANCIERAS  = f"{BASE_FINANCIERAS}&gid=0"
URL_CONTRATOS    = f"{BASE_FINANCIERAS}&gid=28649955"

ESTADOS_VALIDOS  = {"definitivo"}
EMPRESAS_VALIDAS = {"ECOTRANSPORTE", "TRANSCOOP", "CENTRALCOOP"}

def fetch_csv(url: str) -> list:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        content = r.read().decode("utf-8-sig")
    return [row for row in csv.DictReader(io.StringIO(content))]

def clean(val) -> str:
    return val.strip() if val else ""

def clean_float(val) -> float | None:
    v = clean(val).replace(".", "").replace(",", ".").replace("€", "").replace(" ", "")
    try:
        return float(v) if v else None
    except:
        return None

def clean_int(val) -> int | None:
    v = clean(val)
    try:
        return int(v) if v else None
    except:
        return None

def parse_fecha(fecha_str: str):
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(fecha_str.strip(), fmt)
        except:
            pass
    return None

def sync_vehiculos(db, rows):
    print(f"  Vehiculos: {len(rows)} filas")
    for row in rows:
        matricula = clean(row.get("Matrícula", ""))
        if not matricula:
            continue
        existing = db.query(models.Vehiculo).filter(models.Vehiculo.matricula == matricula).first()
        fecha_incorporacion = clean(row.get("Fecha Incorporación", "") or row.get("FechaIncorporación", ""))
        data = {
            "matricula":           matricula,
            "marca":               clean(row.get("Marca", "")),
            "modelo":              clean(row.get("Modelo", "")),
            "bastidor":            clean(row.get("Bastidor", "")),
            "fecha_mat":           clean(row.get("FechaMat.", "")),
            "destinado_a":         clean(row.get("Destinado a", "")),
            "propiedad":           clean(row.get("Propiedad", "")),
            "situacion":           clean(row.get("Situación", "")),
            "estado":              clean(row.get("Estado", "ACTIVO")) or "ACTIVO",
            "fecha_incorporacion": fecha_incorporacion,
            "itv":                 clean(row.get("ITV", "")),
            "tacografo":           clean(row.get("Tacógrafo", "") or row.get("Tacografo", "")),
            "mantenimiento":       clean(row.get("Mantenimiento", "")),
            "fecha_fin_mto":       clean(row.get("FechaFinMto", "")),
            "km_fin_mto":          clean(row.get("KmFinMto", "")),
            "precio_mto":          clean(row.get("PrecioMto", "")),
            "garantia":            clean(row.get("Garantia", "")),
            "fecha_fin_garantia":  clean(row.get("FechaFinGarantia", "")),
            "km_fin_garantia":     clean(row.get("KmFinGarantia", "")),
            "kilometros":          clean(row.get("Kilómetros", "")),
            "equipamiento":        clean(row.get("Equipamiento", "")),
            "observaciones":       clean(row.get("Observaciones", "")),
        }
        if existing:
            for k, v in data.items():
                setattr(existing, k, v)
        else:
            db.add(models.Vehiculo(**data))
    db.commit()
    db.expire_all()
    print("  ✓ Vehículos sincronizados")

def sync_clientes(db, rows_clientes, rows_historial):
    historial_map = {}
    for row in rows_historial:
        cid = clean(row.get("ConductorID", ""))
        if not cid:
            continue
        if cid not in historial_map:
            historial_map[cid] = []
        historial_map[cid].append({
            "vehiculo_id":  clean(row.get("VehículoID", "") or row.get("VehiculoID", "")),
            "fecha_inicio": clean(row.get("FechaInicio", "")),
            "fecha_fin":    clean(row.get("FechaFin", "")),
        })

    print(f"  Clientes totales: {len(rows_clientes)}")
    importados = 0
    omitidos   = 0

    # IDs válidos del Sheets (solo los que pasarán el filtro)
    ids_validos = set()

    for row in rows_clientes:
        id_cliente = clean(row.get("ID", ""))
        if not id_cliente:
            continue

        estado_raw = clean(row.get("Estado", "")).lower()
        situacion  = clean(row.get("Situación", "")).lower()
        empresa    = clean(row.get("Empresa", "")).upper()

        if estado_raw not in ("confirmado", "ex-socio", "ex socio", "exsocio") and situacion not in ESTADOS_VALIDOS and situacion not in ("perdido", "baja"):
            omitidos += 1
            continue
        if empresa not in EMPRESAS_VALIDAS:
            omitidos += 1
            continue

        ids_validos.add(id_cliente)

        nif           = clean(row.get("NIF", "")) or id_cliente
        fecha_nac     = clean(row.get("FECHA NACIMIENTO", ""))
        direccion     = clean(row.get("DIRECCION", ""))
        poblacion     = clean(row.get("POBLACION", ""))
        cod_postal    = clean(row.get("CODIGO P.", ""))
        provincia     = clean(row.get("PROVINCIA", ""))
        apellidos     = clean(row.get("APELLIDOS", ""))
        num_socio     = clean(row.get("CODIGO", ""))
        nombre_propio = clean(row.get("NOMBRE PROPIO", "")) or clean(row.get("Nombre", ""))
        gestor        = clean(row.get("GESTOR", "")).upper()
        fecha_baja    = clean(row.get("FECHA BAJA", ""))

        # Determinar estado real del conductor
        if estado_raw == "confirmado" and situacion in ESTADOS_VALIDOS:
            estado_final = "Confirmado"
        elif estado_raw in ("ex-socio", "ex socio", "exsocio") or situacion in ("perdido", "baja"):
            estado_final = "Ex-socio"
        else:
            estado_final = clean(row.get("Estado", "")) or "Confirmado"

        registros_historial = historial_map.get(id_cliente, [])
        if fecha_baja and registros_historial:
            fecha_baja_dt = parse_fecha(fecha_baja)
            if fecha_baja_dt:
                volvio = any(
                    parse_fecha(r["fecha_inicio"]) and parse_fecha(r["fecha_inicio"]) > fecha_baja_dt
                    for r in registros_historial if r["fecha_inicio"]
                )
                if volvio:
                    fecha_baja = ""

        data = {
            "id":            id_cliente,
            "nombre":        clean(row.get("Nombre", "")),
            "nombre_propio": nombre_propio,
            "apellidos":     apellidos,
            "nif":           nif,
            "num_tarj_conductor": clean(row.get("NUM_TARJ_CONDUCTOR", "")),
            "movil":         clean(row.get("Móvil", "")),
            "email":         clean(row.get("Email", "")),
            "empresa":       clean(row.get("Empresa", "")),
            "gestor":        gestor,
            "estado":        estado_final,
            "fecha_inicio":  clean(row.get("Fecha Alta", "")),
            "fecha_prevista": clean(row.get("Fecha prevista", "")),
            "fecha_baja":    fecha_baja,
            "fecha_nac":     fecha_nac,
            "num_socio":     num_socio,
            "direccion":     direccion,
            "poblacion":     poblacion,
            "codigo_postal": cod_postal,
            "provincia":     provincia,
            "codigo_socio":  clean(row.get("Situación", "")),
        }

        existing = db.query(models.Conductor).filter(models.Conductor.id == id_cliente).first()
        if existing:
            for k, v in data.items():
                setattr(existing, k, v)
        else:
            db.add(models.Conductor(**data))
        importados += 1

    # Borrar conductores que ya no están en el Sheets
    todos_en_bd = db.query(models.Conductor.id).all()
    ids_en_bd = {r[0] for r in todos_en_bd}
    ids_a_borrar = ids_en_bd - ids_validos
    if ids_a_borrar:
        db.query(models.Conductor).filter(models.Conductor.id.in_(ids_a_borrar)).delete(synchronize_session=False)
        print(f"  🗑 Conductores eliminados del Sheets: {len(ids_a_borrar)}")

    db.commit()
    db.expire_all()
    print(f"  ✓ Clientes sincronizados — {importados} importados, {omitidos} omitidos")

def sync_seguros(db, rows, rows_aseguradoras=None):
    print(f"  Seguros: {len(rows)} filas")
    hoy = datetime.now()
    importados = 0
    omitidos   = 0
    db.query(models.Seguro).delete()
    db.commit()

    # Mapa ID → nombre de aseguradora
    aseguradoras_map = {}
    if rows_aseguradoras:
        for r in rows_aseguradoras:
            aid    = clean(r.get("ID_Aseguradora", ""))
            nombre = clean(r.get("Aseguradora", ""))
            if aid and nombre:
                aseguradoras_map[aid] = nombre

    for row in rows:
        estado = clean(row.get("Estado", "")).upper()
        if estado != "ACTIVO":
            omitidos += 1
            continue
        fecha_vencimiento_str = clean(row.get("Fecha de Vencimiento", ""))
        fecha_vencimiento     = parse_fecha(fecha_vencimiento_str)
        if fecha_vencimiento and fecha_vencimiento < hoy:
            omitidos += 1
            continue
        id_seguro = clean(row.get("ID", "")) or clean(row.get("Nº de Póliza", ""))
        if not id_seguro:
            continue
        aseguradora_id = clean(row.get("Aseguradora_ID", ""))
        aseguradora_nombre = aseguradoras_map.get(aseguradora_id, aseguradora_id)
        db.add(models.Seguro(
            id           = str(id_seguro),
            poliza       = clean(row.get("Nº de Póliza", "")),
            matricula    = clean(row.get("Matrícula", "")),
            tomador      = clean(row.get("Tomador", "")),
            tipo         = clean(row.get("Tipo de Seguro", "")),
            aseguradora  = aseguradora_nombre,
            corredor     = clean(row.get("Corredor", "")),
            vencimiento  = fecha_vencimiento_str,
            ambito       = clean(row.get("Ámbito", "")),
            garantias    = clean(row.get("Garantías", "")),
            estado       = estado,
            observaciones= clean(row.get("Observaciones", "")),
        ))
        importados += 1

    db.commit()
    db.expire_all()
    print(f"  ✓ Seguros sincronizados — {importados} importados, {omitidos} omitidos/caducados")

def sync_financieras(db, rows):
    print(f"  Financieras: {len(rows)} filas")
    db.query(models.Financiera).delete()
    db.commit()
    importados = 0
    for row in rows:
        id_fin = clean(row.get("FinAcuerdoID", ""))
        if not id_fin:
            continue
        db.add(models.Financiera(
            id                 = id_fin,
            num_contrato       = clean(row.get("NumContrato", "")),
            vehiculo_id        = clean(row.get("VehiculoID", "")),
            empresa_id         = clean(row.get("EmpresaID", "")),
            tipo               = clean(row.get("Tipo", "")),
            fecha_inicio       = clean(row.get("FechaInicio", "")),
            fecha_fin          = clean(row.get("FechaFin", "")),
            cuota_mensual      = clean_float(row.get("CuotaMensual", "")),
            num_cuotas         = clean_int(row.get("NumCuotas", "")),
            dia_pago           = clean_int(row.get("DiaPago", "")),
            importe_financiado = clean_float(row.get("ImporteFinanciado", "")),
            valor_residual     = clean_float(row.get("ValorResidual", "")),
            financiera         = clean(row.get("Financiera", "")),
            gastos_iniciales   = clean_float(row.get("GastosIniciales", "")),
            fianzas            = clean_float(row.get("Fianzas", "")),
            entrada            = clean_float(row.get("Entrada", "")),
            observaciones      = clean(row.get("Co", "") or row.get("Comentarios", "") or row.get("Observaciones", "")),
        ))
        importados += 1
    db.commit()
    db.expire_all()
    print(f"  ✓ Financieras sincronizadas — {importados} importadas")

def sync_contratos(db, rows, rows_clientes):
    print(f"  Contratos: {len(rows)} filas")
    db.query(models.Contrato).delete()
    db.commit()
    importados = 0

    # Mapa de nombres de todos los clientes del CSV (sin filtro)
    clientes_map = {}
    for r in rows_clientes:
        cid   = r.get("ID", "").strip()
        nombre = r.get("Nombre", "").strip()
        if cid and nombre:
            clientes_map[cid] = nombre

    # Completar con conductores de la BD
    for c in db.query(models.Conductor).all():
        if c.id not in clientes_map:
            clientes_map[c.id] = c.nombre

    for row in rows:
        id_contrato = clean(row.get("AlqContratoID", ""))
        if not id_contrato:
            continue
        cliente_id = clean(row.get("ClienteID", ""))
        db.add(models.Contrato(
            id               = id_contrato,
            num_contrato     = clean(row.get("NumContrato", "")),
            tipo_contrato    = clean(row.get("TipoContrato", "")),
            vehiculo_id      = clean(row.get("VehiculoID", "")),
            cliente_id       = cliente_id,
            empresa_id       = clean(row.get("EmpresaID", "")),
            fecha_inicio     = clean(row.get("FechaInicio", "")),
            fecha_fin        = clean(row.get("FechaFin", "")),
            num_cuotas       = clean_int(row.get("NumCuotas", "")),
            cuota_base       = clean_float(row.get("CuotaBase", "")),
            condiciones      = clean(row.get("Condiciones", "")),
            fianza           = clean_float(row.get("Fianza", "")),
            entrada          = clean_float(row.get("Entrada", "")),
            valor_residual   = clean_float(row.get("ValorResidual", "")),
            nombre_conductor = clientes_map.get(cliente_id, ""),
            estado           = "ACTIVO",
        ))
        importados += 1
    db.commit()
    db.expire_all()
    print(f"  ✓ Contratos sincronizados — {importados} importados")

def sync_historial(db, rows):
    print(f"  HistorialVehiculo: {len(rows)} filas")
    vehiculos_map       = {}
    conductor_vehiculos = {}

    for row in rows:
        vehiculo_id  = clean(row.get("VehículoID", "") or row.get("VehiculoID", ""))
        if not vehiculo_id:
            continue
        fecha_fin    = clean(row.get("FechaFin", ""))
        conductor_id = clean(row.get("ConductorID", ""))

        if vehiculo_id not in vehiculos_map:
            vehiculos_map[vehiculo_id] = []
        vehiculos_map[vehiculo_id].append({
            "conductor_id": conductor_id,
            "fecha_fin":    fecha_fin,
            "fecha_inicio": clean(row.get("FechaInicio", "")),
        })

        if not fecha_fin and conductor_id:
            if conductor_id not in conductor_vehiculos:
                conductor_vehiculos[conductor_id] = []
            if vehiculo_id not in conductor_vehiculos[conductor_id]:
                conductor_vehiculos[conductor_id].append(vehiculo_id)

    print(f"  Vehículos en historial: {len(vehiculos_map)}")
    actualizados = 0

    for matricula, registros in vehiculos_map.items():
        activos = [r for r in registros if not r["fecha_fin"] and r["conductor_id"]]
        if activos:
            nombres   = []
            primer_id = None
            for r in activos:
                c = db.query(models.Conductor).filter(models.Conductor.id == r["conductor_id"]).first()
                if c:
                    nombres.append(c.nombre)
                    if primer_id is None:
                        primer_id = r["conductor_id"]
            if nombres:
                db.query(models.Vehiculo).filter(models.Vehiculo.matricula == matricula).update({
                    "conductor_actual":    ", ".join(nombres),
                    "conductor_actual_id": primer_id or "",
                    "tipo_conductor":      "actual"
                }, synchronize_session=False)
                actualizados += 1
        else:
            con_fecha = [r for r in registros if r["fecha_fin"] and r["conductor_id"]]
            if con_fecha:
                ultimo = sorted(con_fecha, key=lambda x: parse_fecha(x["fecha_fin"]) or datetime.min, reverse=True)[0]
                conductor = db.query(models.Conductor).filter(models.Conductor.id == ultimo["conductor_id"]).first()
                if conductor:
                    db.query(models.Vehiculo).filter(models.Vehiculo.matricula == matricula).update({
                        "conductor_actual":    conductor.nombre,
                        "conductor_actual_id": ultimo["conductor_id"],
                        "tipo_conductor":      "ultimo"
                    }, synchronize_session=False)
                    actualizados += 1

    # Para conductores sin vehiculo activo, asignar el más reciente
    conductores_sin_activo = set()
    for matricula, registros in vehiculos_map.items():
        con_fecha = [r for r in registros if r["fecha_fin"] and r["conductor_id"]]
        if con_fecha and not any(not r["fecha_fin"] for r in registros):
            ultimo = sorted(con_fecha, key=lambda x: parse_fecha(x["fecha_fin"]) or datetime.min, reverse=True)[0]
            cid = ultimo["conductor_id"]
            if cid not in conductor_vehiculos and cid not in conductores_sin_activo:
                conductores_sin_activo.add(cid)
                conductor_vehiculos[cid] = [matricula]

    for conductor_id, matriculas in conductor_vehiculos.items():
        db.query(models.Conductor).filter(models.Conductor.id == conductor_id).update({
            "vehiculo": ",".join(matriculas)
        }, synchronize_session=False)

    db.commit()
    db.expire_all()
    print(f"  ✓ Historial sincronizado — {actualizados} vehículos actualizados")

def sync_historial_tabla(db, rows):
    print(f"  HistorialVehiculo tabla: {len(rows)} filas")
    db.query(models.HistorialVehiculo).delete()
    db.commit()
    importados = 0
    for row in rows:
        id_hist      = clean(row.get("ID", ""))
        vehiculo_id  = clean(row.get("VehículoID", "") or row.get("VehiculoID", ""))
        conductor_id = clean(row.get("ConductorID", ""))
        if not vehiculo_id or not id_hist:
            continue
        db.add(models.HistorialVehiculo(
            id           = id_hist,
            vehiculo_id  = vehiculo_id,
            conductor_id = conductor_id,
            fecha_inicio = clean(row.get("FechaInicio", "")),
            fecha_fin    = clean(row.get("FechaFin", "")),
            accion       = clean(row.get("Acción", "") or row.get("Accion", "")),
            observaciones= clean(row.get("Observaciones", "")),
        ))
        importados += 1
    db.commit()
    db.expire_all()
    print(f"  ✓ HistorialVehiculo tabla sincronizada — {importados} registros")

def sync_all():
    print(f"\n{'='*50}")
    print(f"  Sincronización: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"{'='*50}")

    print("\n[0/6] Descargando datos base...")
    rows_historial = fetch_csv(URL_HISTORIAL)
    rows_clientes  = fetch_csv(URL_CLIENTES)

    db1 = SessionLocal()
    try:
        print("\n[1/6] Vehículos...")
        sync_vehiculos(db1, fetch_csv(URL_VEHICULOS))
        print("\n[2/6] Clientes...")
        sync_clientes(db1, rows_clientes, rows_historial)
        print("\n[3/6] Seguros...")
        sync_seguros(db1, fetch_csv(URL_SEGUROS), fetch_csv(URL_ASEGURADORAS))
        print("\n[4/6] Financieras...")
        sync_financieras(db1, fetch_csv(URL_FINANCIERAS))
        print("\n[5/6] Contratos...")
        sync_contratos(db1, fetch_csv(URL_CONTRATOS), rows_clientes)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        db1.rollback()
        raise
    finally:
        db1.close()

    db2 = SessionLocal()
    try:
        print("\n[6/6] HistorialVehiculo...")
        sync_historial(db2, rows_historial)
        sync_historial_tabla(db2, rows_historial)
        print(f"\n✓ Completado: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        db2.rollback()
        raise
    finally:
        db2.close()

if __name__ == "__main__":
    sync_all()