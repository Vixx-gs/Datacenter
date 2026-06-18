from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
from auth import verificar_token
import models, schemas

router = APIRouter(prefix="/seguros", tags=["seguros"])

@router.get("/", response_model=List[schemas.SeguroOut])
def get_seguros(
    matricula: Optional[str] = Query(None),
    estado: Optional[str] = Query(None),
    tomador: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: str = Depends(verificar_token)
):
    q = db.query(models.Seguro)
    if matricula: q = q.filter(models.Seguro.matricula == matricula)
    if estado:    q = q.filter(models.Seguro.estado == estado)
    if tomador:   q = q.filter(models.Seguro.tomador == tomador)
    return q.order_by(models.Seguro.vencimiento).all()