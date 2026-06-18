from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
from auth import verificar_token
import models, schemas

router = APIRouter(prefix="/ingresos", tags=["ingresos"])

@router.get("/", response_model=List[schemas.IngresoOut])
def get_ingresos(
    cooperativa: Optional[str] = Query(None),
    ejercicio: Optional[int] = Query(None),
    trimestre: Optional[int] = Query(None),
    skip: int = 0, limit: int = 1000,
    db: Session = Depends(get_db)
):
    q = db.query(models.Ingreso)
    if cooperativa: q = q.filter(models.Ingreso.cooperativa == cooperativa)
    if ejercicio:   q = q.filter(models.Ingreso.ejercicio == ejercicio)
    if trimestre:   q = q.filter(models.Ingreso.trimestre == trimestre)
    return q.order_by(models.Ingreso.fecha.desc()).offset(skip).limit(limit).all()