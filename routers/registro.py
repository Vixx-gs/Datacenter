from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
from auth import verificar_token
import models, schemas

router = APIRouter(prefix="/registro", tags=["registro"])

@router.get("/", response_model=List[schemas.RegistroEmpresaOut])
def get_registro(
    empresa: Optional[str] = Query(None),
    skip: int = 0, limit: int = 500,
    db: Session = Depends(get_db)
):
    q = db.query(models.RegistroEmpresa)
    if empresa: q = q.filter(models.RegistroEmpresa.empresa == empresa)
    return q.offset(skip).limit(limit).all()

@router.post("/", response_model=schemas.RegistroEmpresaOut)
def create_registro(registro: schemas.RegistroEmpresaCreate, db: Session = Depends(get_db)):
    db_r = models.RegistroEmpresa(**registro.model_dump())
    db.add(db_r); db.commit(); db.refresh(db_r)
    return db_r