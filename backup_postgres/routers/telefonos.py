from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
from auth import verificar_token
import models, schemas

router = APIRouter(prefix="/telefonos", tags=["telefonos"])

@router.get("/", response_model=List[schemas.TelefonoOut])
def get_telefonos(
    empresa: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    q = db.query(models.Telefono)
    if empresa: q = q.filter(models.Telefono.empresa == empresa)
    return q.order_by(models.Telefono.empresa, models.Telefono.extension).all()

@router.post("/", response_model=schemas.TelefonoOut)
def create_telefono(telefono: schemas.TelefonoCreate, db: Session = Depends(get_db)):
    db_t = models.Telefono(**telefono.model_dump())
    db.add(db_t); db.commit(); db.refresh(db_t)
    return db_t