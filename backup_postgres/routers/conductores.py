from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
from auth import verificar_token
import models, schemas

router = APIRouter(prefix="/conductores", tags=["conductores"])

@router.get("/ex-socios", response_model=List[schemas.ConductorOut2])
def get_ex_socios(
    empresa: Optional[str] = Query(None),
    skip: int = 0, limit: int = 2000,
    db: Session = Depends(get_db),
    _: str = Depends(verificar_token)
):
    q = db.query(models.Conductor).filter(models.Conductor.estado == "Ex-socio")
    if empresa: q = q.filter(models.Conductor.empresa == empresa)
    return q.order_by(models.Conductor.nombre).offset(skip).limit(limit).all()

@router.get("/", response_model=List[schemas.ConductorOut2])
def get_conductores(
    empresa: Optional[str] = Query(None),
    gestor: Optional[str] = Query(None),
    estado: Optional[str] = Query(None),
    skip: int = 0, limit: int = 2000,
    db: Session = Depends(get_db),
    _: str = Depends(verificar_token)
):
    q = db.query(models.Conductor)
    # Por defecto excluir ex-socios
    if not estado:
        q = q.filter(
            models.Conductor.estado != "Ex-socio",
            models.Conductor.codigo_socio == "DEFINITIVO"
        )
    else:
        q = q.filter(models.Conductor.estado == estado)
    if empresa: q = q.filter(models.Conductor.empresa == empresa)
    if gestor:  q = q.filter(models.Conductor.gestor == gestor)
    return q.order_by(models.Conductor.nombre).offset(skip).limit(limit).all()

@router.get("/{id}/historial-vehiculos")
def get_historial_vehiculos(
    id: str,
    db: Session = Depends(get_db),
    _: str = Depends(verificar_token)
):
    registros = db.query(models.HistorialVehiculo).filter(
        models.HistorialVehiculo.conductor_id == id
    ).order_by(models.HistorialVehiculo.fecha_inicio.desc()).all()
    return [
        {
            "vehiculo_id":  r.vehiculo_id,
            "conductor_id": r.conductor_id,
            "fecha_inicio": r.fecha_inicio,
            "fecha_fin":    r.fecha_fin,
            "accion":       r.accion,
        }
        for r in registros
    ]

@router.get("/{id}", response_model=schemas.ConductorOut2)
def get_conductor(
    id: str,
    db: Session = Depends(get_db),
    _: str = Depends(verificar_token)
):
    c = db.query(models.Conductor).filter(models.Conductor.id == id).first()
    if not c:
        c = db.query(models.Conductor).filter(models.Conductor.nif == id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Conductor no encontrado")
    return c

@router.put("/{id}", response_model=schemas.ConductorOut2)
def update_conductor(
    id: str,
    conductor: schemas.ConductorUpdate,
    db: Session = Depends(get_db),
    _: str = Depends(verificar_token)
):
    db_c = db.query(models.Conductor).filter(models.Conductor.id == id).first()
    if not db_c:
        raise HTTPException(status_code=404, detail="Conductor no encontrado")
    for k, v in conductor.model_dump(exclude_unset=True).items():
        setattr(db_c, k, v)
    db.commit(); db.refresh(db_c)
    return db_c

@router.get("/{id}/historial-vehiculos")
def get_historial_vehiculos(
    id: str,
    db: Session = Depends(get_db),
    _: str = Depends(verificar_token)
):
    registros = db.query(models.HistorialVehiculo).filter(
        models.HistorialVehiculo.conductor_id == id
    ).order_by(models.HistorialVehiculo.fecha_inicio.desc()).all()
    return [
        {
            "vehiculo_id":  r.vehiculo_id,
            "conductor_id": r.conductor_id,
            "fecha_inicio": r.fecha_inicio,
            "fecha_fin":    r.fecha_fin,
            "accion":       r.accion,
        }
        for r in registros
    ]

@router.get("/{id}", response_model=schemas.ConductorOut2)
def get_conductor(
    id: str,
    db: Session = Depends(get_db),
    _: str = Depends(verificar_token)
):
    c = db.query(models.Conductor).filter(models.Conductor.id == id).first()
    if not c:
        c = db.query(models.Conductor).filter(models.Conductor.nif == id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Conductor no encontrado")
    return c

@router.put("/{id}", response_model=schemas.ConductorOut2)
def update_conductor(
    id: str,
    conductor: schemas.ConductorUpdate,
    db: Session = Depends(get_db),
    _: str = Depends(verificar_token)
):
    db_c = db.query(models.Conductor).filter(models.Conductor.id == id).first()
    if not db_c:
        raise HTTPException(status_code=404, detail="Conductor no encontrado")
    for k, v in conductor.model_dump(exclude_unset=True).items():
        setattr(db_c, k, v)
    db.commit(); db.refresh(db_c)
    return db_c