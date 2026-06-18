from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
from auth import verificar_token
import models, schemas

router = APIRouter(prefix="/vehiculos", tags=["vehiculos"])

@router.get("/", response_model=List[schemas.VehiculoOut])
def get_vehiculos(
    estado: Optional[str] = Query(None),
    destinado_a: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 2000,
    db: Session = Depends(get_db),
    _: str = Depends(verificar_token)
):
    q = db.query(models.Vehiculo)
    if estado:      q = q.filter(models.Vehiculo.estado == estado)
    if destinado_a: q = q.filter(models.Vehiculo.destinado_a == destinado_a)
    return q.order_by(models.Vehiculo.matricula).offset(skip).limit(limit).all()

@router.get("/{matricula}/historial")
def get_historial_vehiculo(
    matricula: str,
    db: Session = Depends(get_db),
    _: str = Depends(verificar_token)
):
    registros = db.query(models.HistorialVehiculo).filter(
        models.HistorialVehiculo.vehiculo_id == matricula
    ).order_by(models.HistorialVehiculo.fecha_inicio.desc()).all()
    resultado = []
    for r in registros:
        conductor = db.query(models.Conductor).filter(models.Conductor.id == r.conductor_id).first() if r.conductor_id else None
        resultado.append({
            "id":           r.id,
            "vehiculo_id":  r.vehiculo_id,
            "conductor_id": r.conductor_id,
            "nombre":       conductor.nombre if conductor else "—",
            "fecha_inicio": r.fecha_inicio,
            "fecha_fin":    r.fecha_fin,
            "accion":       r.accion,
        })
    return resultado

@router.get("/{matricula}/conductor-detalle")
def get_conductor_detalle(
    matricula: str,
    db: Session = Depends(get_db),
    _: str = Depends(verificar_token)
):
    """Devuelve datos completos del conductor actual del vehículo."""
    v = db.query(models.Vehiculo).filter(models.Vehiculo.matricula == matricula).first()
    if not v or not v.conductor_actual_id:
        return None
    c = db.query(models.Conductor).filter(models.Conductor.id == v.conductor_actual_id).first()
    if not c:
        return None
    return {
        "id":     c.id,
        "nombre": c.nombre,
        "movil":  c.movil,
        "email":  c.email,
        "gestor": c.gestor,
    }

@router.get("/{matricula}", response_model=schemas.VehiculoOut)
def get_vehiculo(
    matricula: str,
    db: Session = Depends(get_db),
    _: str = Depends(verificar_token)
):
    v = db.query(models.Vehiculo).filter(models.Vehiculo.matricula == matricula).first()
    if not v: raise HTTPException(status_code=404, detail="Vehículo no encontrado")
    return v

@router.put("/{matricula}", response_model=schemas.VehiculoOut)
def update_vehiculo(
    matricula: str,
    vehiculo: schemas.VehiculoUpdate,
    db: Session = Depends(get_db),
    _: str = Depends(verificar_token)
):
    db_v = db.query(models.Vehiculo).filter(models.Vehiculo.matricula == matricula).first()
    if not db_v: raise HTTPException(status_code=404, detail="Vehículo no encontrado")
    for k, v in vehiculo.model_dump(exclude_unset=True).items():
        setattr(db_v, k, v)
    db.commit(); db.refresh(db_v)
    return db_v