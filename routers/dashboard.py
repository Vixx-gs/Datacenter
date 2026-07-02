from fastapi import APIRouter, Depends, Query
from database import get_db
from auth import verificar_token
from datetime import datetime, timedelta
from typing import Optional
import sheets_cache as sc
import firestore_cache as fc

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

def parse_fecha(f: str):
    if not f or not f.strip(): return None
    s = f.strip().split("T")[0].split(" ")[0]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y"):
        try: return datetime.strptime(s, fmt)
        except: pass
    return None

def _map_conductor(doc_id: str, d: dict) -> dict:
    return {
        "id":             doc_id,
        "nombre":         d.get("nombre", ""),
        "apellidos":      d.get("apellidos", ""),
        "nif":            d.get("nif", ""),
        "movil":          d.get("movil", ""),
        "email":          d.get("email", ""),
        "empresa":        d.get("empresa", ""),
        "gestor":         d.get("gestor", ""),
        "fecha_inicio":   d.get("fechaAlta", ""),
        "fecha_prevista": d.get("fechaIngreso", ""),
        "fecha_baja":     d.get("fechaBaja", ""),
        "estado":         d.get("estado", ""),
        "codigo_socio":   d.get("situacion", ""),
        "num_socio":      d.get("codigo", ""),
        "vehiculo":       "",
    }

EMPRESAS_VALIDAS = {"ECOTRANSPORTE", "TRANSCOOP", "CENTRALCOOP"}

def _all_conductores(db=None) -> list:
    return [
        _map_conductor(doc_id, d)
        for doc_id, d in fc.get_clients()
        if d.get("empresa", "").upper() in EMPRESAS_VALIDAS
    ]

def _all_entradas_taller(db=None) -> list:
    return [d for _, d in fc.get_workshop_entries()]

def contar_en_taller(db) -> int:
    hoy  = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    count = 0
    for d in _all_entradas_taller(db):
        ff = d.get("fechaFin", "")
        if not ff or not ff.strip():
            count += 1
            continue
        fd = parse_fecha(ff)
        if fd and fd >= hoy:
            count += 1
    return count

def socios_rango(conductores: list, campo: str, desde: datetime, hasta: datetime) -> list:
    result = []
    for c in conductores:
        if c.get("estado", "").lower() != "confirmado":    continue
        if c.get("codigo_socio", "").upper() != "definitivo".upper() and c.get("codigo_socio", "").upper() != "DEFINITIVO": continue
        fd = parse_fecha(c.get(campo, ""))
        if fd and desde <= fd <= hasta:
            result.append(c)
    return result

def bajas_rango(conductores: list, desde: datetime, hasta: datetime) -> list:
    result = []
    for c in conductores:
        fd = parse_fecha(c.get("fecha_baja", ""))
        if fd and desde <= fd <= hasta:
            result.append(c)
    return result

def _count_activos_hasta(conductores: list, hasta: datetime, empresa: str = "TODAS") -> int:
    n = 0
    for c in conductores:
        if empresa != "TODAS" and c.get("empresa", "").upper() != empresa.upper():
            continue
        codigo = c.get("codigo_socio", "").upper()
        if codigo not in ("DEFINITIVO", "PERDIDO"):
            continue
        if codigo == "PERDIDO" and not c.get("fecha_baja"):
            continue
        _fechas = [d for d in [parse_fecha(c.get("fecha_prevista")), parse_fecha(c.get("fecha_inicio"))] if d]
        fi = min(_fechas) if _fechas else None
        fb = parse_fecha(c.get("fecha_baja")) if c.get("fecha_baja") else None
        if fi and fi <= hasta:
            if fb is None or fb > hasta:
                n += 1
    return n

@router.get("/stats")
def get_stats(db = Depends(get_db), _: str = Depends(verificar_token)):
    import schemas
    hoy    = datetime.now()
    hace30 = hoy - timedelta(days=30)
    conductores = _all_conductores(db)

    confirmados = [c for c in conductores
                   if c["estado"].lower() == "confirmado"
                   and c["codigo_socio"].upper() == "DEFINITIVO"]

    total_veh = sum(1 for _ in db.collection("vehicles").stream())
    activos_v = sum(1 for doc in db.collection("vehicles").stream()
                    if doc.to_dict().get("estado", "").upper() == "ACTIVO")
    # Seguros: leídos de Sheets (caché 5 min) — insurancePolicies en Firebase puede estar vacía
    hoy_dt    = datetime.now()
    seguros_a = sum(
        1 for row in sc.get_seguros()
        if sc.clean(row.get("Estado", "")).upper() == "ACTIVO"
        and (not sc.parse_fecha(sc.clean(row.get("Fecha de Vencimiento", "")))
             or sc.parse_fecha(sc.clean(row.get("Fecha de Vencimiento", ""))) >= hoy_dt)
    )

    altas = socios_rango(conductores, "fecha_prevista", hace30, hoy)
    bajas = bajas_rango(conductores, hace30, hoy)

    return {
        "total_vehiculos":     total_veh,
        "vehiculos_activos":   activos_v,
        "total_conductores":   len(confirmados),
        "conductores_activos": len(confirmados),
        "seguros_activos":     seguros_a,
        "vehiculos_en_taller": contar_en_taller(db),
        "socios_nuevos":       len(altas),
        "socios_bajas":        len(bajas),
        "transcoop":    sum(1 for c in confirmados if c["empresa"].upper() == "TRANSCOOP"),
        "ecotransporte":sum(1 for c in confirmados if c["empresa"].upper() == "ECOTRANSPORTE"),
        "centralcoop":  sum(1 for c in confirmados if c["empresa"].upper() == "CENTRALCOOP"),
    }

@router.get("/socios-altas")
def get_socios_altas(
    rango: str = Query("mes"),
    mes:  int = Query(None),
    anio: int = Query(None),
    db = Depends(get_db),
    _: str = Depends(verificar_token)
):
    hoy = datetime.now()
    if rango == "semana":
        fd, fh = hoy - timedelta(days=7), hoy
    elif rango == "mes_selector" and mes and anio:
        fd = datetime(anio, mes, 1)
        fh = datetime(anio + (1 if mes == 12 else 0), (mes % 12) + 1, 1) - timedelta(seconds=1)
    elif rango == "anio_selector" and anio:
        fd, fh = datetime(anio, 1, 1), datetime(anio, 12, 31, 23, 59, 59)
    else:
        fd, fh = hoy - timedelta(days=30), hoy
    socios = socios_rango(_all_conductores(db), "fecha_prevista", fd, fh)
    return sorted(socios, key=lambda x: x["fecha_prevista"] or "", reverse=True)

@router.get("/socios-bajas")
def get_socios_bajas(
    rango: str = Query("mes"),
    mes:  int = Query(None),
    anio: int = Query(None),
    db = Depends(get_db),
    _: str = Depends(verificar_token)
):
    hoy = datetime.now()
    if rango == "semana":
        fd, fh = hoy - timedelta(days=7), hoy
    elif rango == "mes_selector" and mes and anio:
        fd = datetime(anio, mes, 1)
        fh = datetime(anio + (1 if mes == 12 else 0), (mes % 12) + 1, 1) - timedelta(seconds=1)
    elif rango == "anio_selector" and anio:
        fd, fh = datetime(anio, 1, 1), datetime(anio, 12, 31, 23, 59, 59)
    else:
        fd, fh = hoy - timedelta(days=30), hoy
    bajas = bajas_rango(_all_conductores(db), fd, fh)
    return sorted(bajas, key=lambda x: x["fecha_baja"] or "", reverse=True)

@router.get("/evolucion-socios")
def get_evolucion_socios(
    modo: str = Query("mes"),
    anio: int = Query(None),
    cooperativa: str = Query("TODAS"),
    desde: str = Query(None),
    hasta: str = Query(None),
    db = Depends(get_db),
    _: str = Depends(verificar_token)
):
    hoy = datetime.now()
    anio_c = anio or hoy.year
    conductores = _all_conductores(db)

    def count_activos(fin: datetime) -> int:
        return _count_activos_hasta(conductores, fin, cooperativa)

    if modo == "personalizado" and desde and hasta:
        fd = parse_fecha(desde)
        fh = parse_fecha(hasta)
        if not fd or not fh or fd > fh: return []
        delta = (fh - fd).days + 1
        resultado = []
        if delta > 60:
            semana = fd
            while semana <= fh:
                fin_sem = min(semana + timedelta(days=6), fh)
                resultado.append({"label": semana.strftime("%d/%m"), "valor": count_activos(fin_sem), "periodo": semana.strftime("%d/%m/%Y")})
                semana += timedelta(days=7)
        else:
            for i in range(delta):
                dia = fd + timedelta(days=i)
                resultado.append({"label": dia.strftime("%d/%m"), "valor": count_activos(dia), "periodo": dia.strftime("%d/%m/%Y")})
        return resultado

    elif modo == "mes":
        nombres = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
        resultado = []
        for m in range(1, 13):
            inicio = datetime(anio_c, m, 1)
            if inicio > hoy: break
            fin = datetime(anio_c, m+1, 1) - timedelta(seconds=1) if m < 12 else datetime(anio_c, 12, 31, 23, 59, 59)
            resultado.append({"label": nombres[m-1], "valor": count_activos(min(fin, hoy)), "periodo": f"{m:02d}/{anio_c}"})
        return resultado

    else:  # anio
        resultado = []
        for a in range(2020, hoy.year + 1):
            if datetime(a, 1, 1) > hoy: break
            fin = datetime(a, 12, 31, 23, 59, 59)
            resultado.append({"label": str(a), "valor": count_activos(min(fin, hoy)), "periodo": str(a)})
        return resultado

@router.get("/socios-evolucion")
def get_socios_evolucion(
    modo: str = Query("dia"),
    mes:  int = Query(None),
    anio: int = Query(None),
    cooperativa: str = Query("TODAS"),
    db = Depends(get_db),
    _: str = Depends(verificar_token)
):
    hoy    = datetime.now()
    mes_c  = mes  or hoy.month
    anio_c = anio or hoy.year
    conductores = _all_conductores(db)

    def count_activos(hasta: datetime) -> int:
        return _count_activos_hasta(conductores, hasta, cooperativa)

    if modo == "anio":
        resultado = []
        for a in range(2020, hoy.year + 1):
            if datetime(a, 1, 1) > hoy: break
            hasta = datetime(a, 12, 31, 23, 59, 59)
            resultado.append({"label": str(a), "valor": count_activos(min(hasta, hoy))})
        return resultado

    elif modo == "mes":
        nombres = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
        resultado = []
        for m in range(1, 13):
            if datetime(anio_c, m, 1) > hoy: break
            h = datetime(anio_c, m+1, 1) - timedelta(seconds=1) if m < 12 else datetime(anio_c, 12, 31, 23, 59, 59)
            resultado.append({"label": nombres[m-1], "valor": count_activos(min(h, hoy))})
        return resultado

    else:  # dia
        if mes_c == 12:
            fin_mes = datetime(anio_c + 1, 1, 1) - timedelta(days=1)
        else:
            fin_mes = datetime(anio_c, mes_c + 1, 1) - timedelta(days=1)
        resultado = []
        for dia in range(1, fin_mes.day + 1):
            fd = datetime(anio_c, mes_c, dia)
            if fd > hoy: break
            resultado.append({"label": str(dia), "valor": count_activos(fd)})
        return resultado
