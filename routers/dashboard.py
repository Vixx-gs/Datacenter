from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from database import get_db
from auth import verificar_token
import models, schemas
from datetime import datetime, timedelta
from typing import Optional

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

def parse_fecha_conductor(f: str) -> Optional[datetime]:
    if not f or not f.strip():
        return None
    fecha_str = f.strip().split(' ')[0]
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(fecha_str, fmt)
        except:
            continue
    return None

def contar_en_taller(db):
    todos = db.query(models.TallerEntrada).all()
    count = 0
    hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    for t in todos:
        fecha_fin = t.fecha_fin
        if not fecha_fin or not fecha_fin.strip():
            count += 1
            continue
        try:
            fd = datetime.strptime(fecha_fin.strip(), "%d/%m/%Y")
            if fd >= hoy:
                count += 1
        except:
            pass
    return count

def get_socios_rango(db, campo: str, desde: datetime, hasta: datetime):
    """Devuelve conductores cuya fecha (campo) cae en el rango dado."""
    todos = db.query(models.Conductor).filter(
        models.Conductor.estado == "Confirmado",
        models.Conductor.codigo_socio == "DEFINITIVO",
    ).all()
    resultado = []
    for c in todos:
        valor = getattr(c, campo, None)
        fd = parse_fecha_conductor(valor)
        if fd and desde <= fd <= hasta:
            resultado.append(c)
    return resultado

def get_bajas_rango(db, desde: datetime, hasta: datetime):
    """Devuelve conductores con fecha_baja en el rango dado."""
    todos = db.query(models.Conductor).all()
    resultado = []
    for c in todos:
        fd = parse_fecha_conductor(c.fecha_baja)
        if fd and desde <= fd <= hasta:
            resultado.append(c)
    return resultado

def format_conductor(c) -> dict:
    return {
        "id":              c.id,
        "nombre":          c.nombre,
        "apellidos":       c.apellidos or "",
        "nif":             c.nif,
        "movil":           c.movil,
        "email":           c.email,
        "empresa":         c.empresa,
        "gestor":          c.gestor,
        "fecha_inicio":    c.fecha_inicio,
        "fecha_prevista":  getattr(c, 'fecha_prevista', None),
        "fecha_baja":      c.fecha_baja,
        "vehiculo":        c.vehiculo,
        "num_socio":       c.num_socio,
    }

@router.get("/stats", response_model=schemas.DashboardStats)
def get_stats(db: Session = Depends(get_db), _: str = Depends(verificar_token)):
    hoy  = datetime.now()
    hace30 = hoy - timedelta(days=30)
    altas = get_socios_rango(db, "fecha_prevista", hace30, hoy)
    bajas = get_bajas_rango(db, hace30, hoy)
    return {
        "total_vehiculos":     db.query(models.Vehiculo).count(),
        "vehiculos_activos":   db.query(models.Vehiculo).filter(models.Vehiculo.estado == "ACTIVO").count(),
        "total_conductores":   db.query(models.Conductor).filter(models.Conductor.estado == "Confirmado", models.Conductor.codigo_socio == "DEFINITIVO").count(),
        "conductores_activos": db.query(models.Conductor).filter(models.Conductor.estado == "Confirmado", models.Conductor.codigo_socio == "DEFINITIVO").count(),
        "seguros_activos":     db.query(models.Seguro).filter(models.Seguro.estado == "ACTIVO").count(),
        "vehiculos_en_taller": contar_en_taller(db),
        "socios_nuevos":       len(altas),
        "socios_bajas":        len(bajas),
        "transcoop":           db.query(models.Conductor).filter(models.Conductor.empresa == "TRANSCOOP",     models.Conductor.estado == "Confirmado", models.Conductor.codigo_socio == "DEFINITIVO").count(),
        "ecotransporte":       db.query(models.Conductor).filter(models.Conductor.empresa == "ECOTRANSPORTE", models.Conductor.estado == "Confirmado", models.Conductor.codigo_socio == "DEFINITIVO").count(),
        "centralcoop":         db.query(models.Conductor).filter(models.Conductor.empresa == "CENTRALCOOP",   models.Conductor.estado == "Confirmado", models.Conductor.codigo_socio == "DEFINITIVO").count(),
    }


@router.get("/socios-altas")
def get_socios_altas(
    rango: str = Query("mes"),
    mes: int = Query(None),
    anio: int = Query(None),
    db: Session = Depends(get_db),
    _: str = Depends(verificar_token)
):
    hoy = datetime.now()
    if rango == "semana":
        fecha_desde = hoy - timedelta(days=7)
        fecha_hasta = hoy
    elif rango == "mes_selector" and mes and anio:
        fecha_desde = datetime(anio, mes, 1)
        fecha_hasta = datetime(anio + (1 if mes == 12 else 0), (mes % 12) + 1, 1) - timedelta(seconds=1)
    elif rango == "anio_selector" and anio:
        fecha_desde = datetime(anio, 1, 1)
        fecha_hasta = datetime(anio, 12, 31, 23, 59, 59)
    else:  # mes = últimos 30 días
        fecha_desde = hoy - timedelta(days=30)
        fecha_hasta = hoy
    socios = get_socios_rango(db, "fecha_prevista", fecha_desde, fecha_hasta)
    return [format_conductor(c) for c in sorted(socios, key=lambda x: x.fecha_prevista or "", reverse=True)]

@router.get("/socios-bajas")
def get_socios_bajas(
    rango: str = Query("mes"),
    mes: int = Query(None),
    anio: int = Query(None),
    db: Session = Depends(get_db),
    _: str = Depends(verificar_token)
):
    hoy = datetime.now()
    if rango == "semana":
        fecha_desde = hoy - timedelta(days=7)
        fecha_hasta = hoy
    elif rango == "mes_selector" and mes and anio:
        fecha_desde = datetime(anio, mes, 1)
        fecha_hasta = datetime(anio + (1 if mes == 12 else 0), (mes % 12) + 1, 1) - timedelta(seconds=1)
    elif rango == "anio_selector" and anio:
        fecha_desde = datetime(anio, 1, 1)
        fecha_hasta = datetime(anio, 12, 31, 23, 59, 59)
    else:
        fecha_desde = hoy - timedelta(days=30)
        fecha_hasta = hoy
    socios = get_bajas_rango(db, fecha_desde, fecha_hasta)
    return [format_conductor(c) for c in sorted(socios, key=lambda x: x.fecha_baja or "", reverse=True)]

@router.get("/evolucion-socios")
def get_evolucion_socios(
    modo: str = Query("mes"),          # mes | anio | personalizado
    anio: int = Query(None),
    cooperativa: str = Query("TODAS"),
    desde: str = Query(None),          # dd/mm/yyyy para modo personalizado
    hasta: str = Query(None),
    db: Session = Depends(get_db),
    _: str = Depends(verificar_token)
):
    from collections import defaultdict

    hoy = datetime.now()
    anio_consulta = anio or hoy.year

    # Filtro cooperativa
    q = db.query(models.Conductor).filter(
        models.Conductor.estado == "Confirmado",
        models.Conductor.codigo_socio == "DEFINITIVO",
        models.Conductor.fecha_inicio != None,
        models.Conductor.fecha_inicio != ""
    )
    if cooperativa != "TODAS":
        q = q.filter(models.Conductor.empresa == cooperativa)

    conductores = q.all()

    if modo == "personalizado" and desde and hasta:
        # Muestra día a día entre las dos fechas (máx 366 puntos)
        fd = parse_fecha_conductor(desde)
        fh = parse_fecha_conductor(hasta)
        if not fd or not fh or fd > fh:
            return []
        resultado = []
        delta = (fh - fd).days + 1
        # Si el rango es grande, agrupar por semana
        if delta > 60:
            # Agrupar por semana
            semana = fd
            while semana <= fh:
                fin_sem = min(semana + timedelta(days=6), fh)
                count = 0
                for c in conductores:
                    fi = parse_fecha_conductor(c.fecha_inicio)
                    fb = parse_fecha_conductor(c.fecha_baja) if c.fecha_baja else None
                    if fi and fi <= fin_sem:
                        if fb is None or fb >= semana:
                            count += 1
                resultado.append({"label": semana.strftime("%d/%m"), "valor": count, "periodo": semana.strftime("%d/%m/%Y")})
                semana += timedelta(days=7)
        else:
            # Día a día
            for i in range(delta):
                dia = fd + timedelta(days=i)
                count = 0
                for c in conductores:
                    fi = parse_fecha_conductor(c.fecha_inicio)
                    fb = parse_fecha_conductor(c.fecha_baja) if c.fecha_baja else None
                    if fi and fi <= dia:
                        if fb is None or fb >= dia:
                            count += 1
                resultado.append({"label": dia.strftime("%d/%m"), "valor": count, "periodo": dia.strftime("%d/%m/%Y")})
        return resultado

    elif modo == "mes":
        # Para cada mes del año, contar cuántos socios estaban activos
        # Un socio estaba activo en un mes si: fecha_inicio <= fin_mes y (no tiene fecha_baja o fecha_baja > inicio_mes)
        resultado = []
        meses_nombres = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic']
        for m in range(1, 13):
            inicio_mes = datetime(anio_consulta, m, 1)
            if m == 12:
                fin_mes = datetime(anio_consulta + 1, 1, 1) - timedelta(seconds=1)
            else:
                fin_mes = datetime(anio_consulta, m + 1, 1) - timedelta(seconds=1)

            # No mostrar meses futuros
            if inicio_mes > hoy:
                break

            count = 0
            for c in conductores:
                fi = parse_fecha_conductor(c.fecha_inicio)
                fb = parse_fecha_conductor(c.fecha_baja) if c.fecha_baja else None
                if fi and fi <= fin_mes:
                    if fb is None or fb >= inicio_mes:
                        count += 1

            resultado.append({"label": meses_nombres[m-1], "valor": count, "periodo": f"{m:02d}/{anio_consulta}"})
        return resultado

    else:  # modo anio
        resultado = []
        for a in range(2020, hoy.year + 1):
            fin_anio = datetime(a, 12, 31, 23, 59, 59)
            inicio_anio = datetime(a, 1, 1)
            if inicio_anio > hoy:
                break
            count = 0
            for c in conductores:
                fi = parse_fecha_conductor(c.fecha_inicio)
                fb = parse_fecha_conductor(c.fecha_baja) if c.fecha_baja else None
                if fi and fi <= fin_anio:
                    if fb is None or fb >= inicio_anio:
                        count += 1
            resultado.append({"label": str(a), "valor": count, "periodo": str(a)})
        return resultado

@router.get("/socios-evolucion")
def get_socios_evolucion(
    modo: str = Query("dia"),          # dia | mes | anio
    mes: int = Query(None),
    anio: int = Query(None),
    cooperativa: str = Query("TODAS"),
    db: Session = Depends(get_db),
    _: str = Depends(verificar_token)
):
    hoy = datetime.now()
    mes_c  = mes  or hoy.month
    anio_c = anio or hoy.year

    # DEFINITIVO activos + PERDIDO que tienen fecha_baja (para reflejar bajas reales)
    q_activos = db.query(models.Conductor).filter(
        models.Conductor.codigo_socio.in_(["DEFINITIVO", "PERDIDO"])
    )
    if cooperativa != "TODAS":
        q_activos = q_activos.filter(models.Conductor.empresa == cooperativa)
    conductores = q_activos.all()

    def count_activos(hasta: datetime) -> int:
        n = 0
        for c in conductores:
            # PERDIDO sin fecha_baja = error de datos, no contar
            if c.codigo_socio == "PERDIDO" and not c.fecha_baja:
                continue
            _fechas = [d for d in [parse_fecha_conductor(c.fecha_prevista), parse_fecha_conductor(c.fecha_inicio)] if d]
            fi = min(_fechas) if _fechas else None
            fb = parse_fecha_conductor(c.fecha_baja) if c.fecha_baja else None
            if fi and fi <= hasta:
                if fb is None or fb > hasta:
                    n += 1
        return n

    if modo == "anio":
        resultado = []
        for a in range(2020, hoy.year + 1):
            hasta = datetime(a, 12, 31, 23, 59, 59)
            if datetime(a, 1, 1) > hoy: break
            resultado.append({"label": str(a), "valor": count_activos(min(hasta, hoy))})
        return resultado

    elif modo == "mes":
        meses_nombres = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic']
        resultado = []
        for m in range(1, 13):
            h = datetime(anio_c, m+1, 1) - timedelta(seconds=1) if m < 12 else datetime(anio_c, 12, 31, 23, 59, 59)
            if datetime(anio_c, m, 1) > hoy: break
            resultado.append({"label": meses_nombres[m-1], "valor": count_activos(min(h, hoy))})
        return resultado

    else:  # dia
        if mes_c == 12:
            fin_mes = datetime(anio_c + 1, 1, 1) - timedelta(days=1)
        else:
            fin_mes = datetime(anio_c, mes_c + 1, 1) - timedelta(days=1)
        resultado = []
        for dia in range(1, fin_mes.day + 1):
            fecha_dia = datetime(anio_c, mes_c, dia)
            if fecha_dia > hoy: break
            resultado.append({"label": str(dia), "valor": count_activos(fecha_dia)})
        return resultado