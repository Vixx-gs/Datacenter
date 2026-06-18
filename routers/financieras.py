from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
from auth import verificar_token
import models, schemas

router = APIRouter(prefix="/financieras", tags=["financieras"])

@router.get("/", response_model=List[schemas.FinancieraOut])
def get_financieras(
    vehiculo_id: Optional[str] = Query(None),
    empresa_id: Optional[str] = Query(None),
    tipo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: str = Depends(verificar_token)
):
    q = db.query(models.Financiera)
    if vehiculo_id: q = q.filter(models.Financiera.vehiculo_id == vehiculo_id)
    if empresa_id:  q = q.filter(models.Financiera.empresa_id == empresa_id)
    if tipo:        q = q.filter(models.Financiera.tipo == tipo)
    return q.order_by(models.Financiera.fecha_inicio).all()