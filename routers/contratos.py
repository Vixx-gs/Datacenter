from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
from auth import verificar_token
import models, schemas

router = APIRouter(prefix="/contratos", tags=["contratos"])

@router.get("/", response_model=List[schemas.ContratoOut])
def get_contratos(
    vehiculo_id: Optional[str] = Query(None),
    empresa_id: Optional[str] = Query(None),
    estado: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: str = Depends(verificar_token)
):
    q = db.query(models.Contrato)
    if vehiculo_id: q = q.filter(models.Contrato.vehiculo_id == vehiculo_id)
    if empresa_id:  q = q.filter(models.Contrato.empresa_id == empresa_id)
    if estado:      q = q.filter(models.Contrato.estado == estado)
    return q.order_by(models.Contrato.fecha_inicio.desc()).all()