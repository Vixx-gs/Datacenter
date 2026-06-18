from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from database import get_db
from auth import verificar_token
import models
from datetime import datetime

router = APIRouter(prefix="/entregas", tags=["entregas"])

def parse_fecha(f: str):
    if not f or not f.strip(): return None
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try: return datetime.strptime(f.strip().split(' ')[0], fmt)
        except: pass
    return None

def enriquecer(registros, db):
    ids = list({r.conductor_id for r in registros if r.conductor_id})
    if not ids: return {}
    return {c.id: c.nombre for c in db.query(models.Conductor).filter(models.Conductor.id.in_(ids)).all()}

@router.get("/entradas")
def get_entradas(mes: int = Query(None), anio: int = Query(None), db: Session = Depends(get_db), _: str = Depends(verificar_token)):
    hoy    = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    mes_c  = mes  or hoy.month
    anio_c = anio or hoy.year

    todos = db.query(models.HistorialVehiculo).all()

    # Construir set de vehículos que tienen una entrada activa en el mes
    # (FechaInicio en el mes Y sin FechaFin o FechaFin futura)
    filtrados = []
    for r in todos:
        fi = parse_fecha(r.fecha_inicio)
        if not fi or fi.month != mes_c or fi.year != anio_c: continue
        ff = parse_fecha(r.fecha_fin)
        if ff and ff <= hoy: continue  # ya salió = no es entrada
        filtrados.append(r)

    conductores = enriquecer(filtrados, db)
    return sorted([{
        "vehiculo_id":  r.vehiculo_id,
        "conductor_id": r.conductor_id,
        "conductor":    conductores.get(r.conductor_id, "—") if r.conductor_id else "—",
        "fecha":        r.fecha_inicio,
        "accion":       r.accion,
    } for r in filtrados], key=lambda x: x["fecha"] or "", reverse=True)

@router.get("/salidas")
def get_salidas(mes: int = Query(None), anio: int = Query(None), db: Session = Depends(get_db), _: str = Depends(verificar_token)):
    hoy    = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    mes_c  = mes  or hoy.month
    anio_c = anio or hoy.year

    todos = db.query(models.HistorialVehiculo).all()

    # Construir set de vehículos que tienen una ENTRADA activa este mes
    # Si un vehículo tiene entrada activa este mes, NO aparece en salidas
    vehiculos_con_entrada_activa = set()
    for r in todos:
        fi = parse_fecha(r.fecha_inicio)
        if not fi or fi.month != mes_c or fi.year != anio_c: continue
        ff = parse_fecha(r.fecha_fin)
        if ff is None or ff > hoy:
            vehiculos_con_entrada_activa.add(r.vehiculo_id)

    filtrados = []
    for r in todos:
        ff = parse_fecha(r.fecha_fin)
        if not ff or ff.month != mes_c or ff.year != anio_c: continue
        if ff > hoy: continue
        # Si el vehículo tiene una entrada activa este mes, excluir de salidas
        if r.vehiculo_id in vehiculos_con_entrada_activa: continue
        filtrados.append(r)

    conductores = enriquecer(filtrados, db)
    return sorted([{
        "vehiculo_id":  r.vehiculo_id,
        "conductor_id": r.conductor_id,
        "conductor":    conductores.get(r.conductor_id, "—") if r.conductor_id else "—",
        "fecha":        r.fecha_fin,
        "accion":       r.accion,
    } for r in filtrados], key=lambda x: x["fecha"] or "", reverse=True)