from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from auth import verificar_token
import models
from datetime import datetime

router = APIRouter(prefix="/tacografo", tags=["tacografo"])

def parse_fecha(f: str):
    if not f or not f.strip(): return None
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try: return datetime.strptime(f.strip().split(' ')[0], fmt)
        except: pass
    return None


@router.get("/caducadas")
def get_tacografo_caducadas(
    db: Session = Depends(get_db),
    _: str = Depends(verificar_token)
):
    hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    vehiculos = db.query(models.Vehiculo).filter(
        models.Vehiculo.estado != "BAJA"
    ).all()

    resultado = []
    for v in vehiculos:
        if (v.matricula or "").upper().startswith("R"):
            continue
        fi = parse_fecha(v.tacografo) if v.tacografo else None
        if fi is None or fi <= hoy:
            resultado.append({
                "matricula":           v.matricula,
                "marca":               v.marca,
                "modelo":              v.modelo,
                "destinado_a":         v.destinado_a,
                "conductor_actual":    v.conductor_actual,
                "conductor_actual_id": v.conductor_actual_id,
                "tacografo":           v.tacografo or "",
                "dias_caducada":       (hoy - fi).days if fi else None,
            })

    resultado.sort(key=lambda x: (
        1 if x["dias_caducada"] is None else 0,
        -(x["dias_caducada"] or 0)
    ))
    return resultado


@router.get("/proximas")
def get_tacografo_proximas(
    dias: int = 30,
    db: Session = Depends(get_db),
    _: str = Depends(verificar_token)
):
    hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    vehiculos = db.query(models.Vehiculo).filter(
        models.Vehiculo.estado != "BAJA"
    ).all()

    resultado = []
    for v in vehiculos:
        if (v.matricula or "").upper().startswith("R"):
            continue
        fi = parse_fecha(v.tacografo) if v.tacografo else None
        if fi is None:
            continue
        dias_restantes = (fi - hoy).days
        if 0 < dias_restantes <= dias:
            resultado.append({
                "matricula":           v.matricula,
                "marca":               v.marca,
                "modelo":              v.modelo,
                "destinado_a":         v.destinado_a,
                "conductor_actual":    v.conductor_actual,
                "conductor_actual_id": v.conductor_actual_id,
                "tacografo":           v.tacografo or "",
                "dias_restantes":      dias_restantes,
            })

    resultado.sort(key=lambda x: x["dias_restantes"])
    return resultado
