from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
from auth import verificar_token
import models, schemas

router = APIRouter(prefix="/cambios", tags=["cambios"])

@router.get("/", response_model=List[schemas.CambioVehiculoOut])
def get_cambios(skip: int = 0, limit: int = 200, db: Session = Depends(get_db)):
    return db.query(models.CambioVehiculo).order_by(models.CambioVehiculo.fecha_inicio.desc()).offset(skip).limit(limit).all()

@router.post("/", response_model=schemas.CambioVehiculoOut)
def create_cambio(cambio: schemas.CambioVehiculoCreate, db: Session = Depends(get_db)):
    db_c = models.CambioVehiculo(**cambio.model_dump())
    db.add(db_c); db.commit(); db.refresh(db_c)
    return db_c