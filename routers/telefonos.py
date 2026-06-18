from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
from auth import verificar_token
import models, schemas, uuid

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
    data = telefono.model_dump()
    if not data.get("id"):
        data["id"] = str(uuid.uuid4())
    db_t = models.Telefono(**data)
    db.add(db_t); db.commit(); db.refresh(db_t)
    return db_t

@router.put("/{id}", response_model=schemas.TelefonoOut)
def update_telefono(id: str, telefono: schemas.TelefonoCreate, db: Session = Depends(get_db)):
    db_t = db.query(models.Telefono).filter(models.Telefono.id == id).first()
    if not db_t:
        raise HTTPException(status_code=404, detail="Teléfono no encontrado")
    data = telefono.model_dump(exclude_unset=True)
    data.pop("id", None)
    for k, v in data.items():
        setattr(db_t, k, v)
    db.commit(); db.refresh(db_t)
    return db_t

@router.delete("/{id}")
def delete_telefono(id: str, db: Session = Depends(get_db)):
    db_t = db.query(models.Telefono).filter(models.Telefono.id == id).first()
    if not db_t:
        raise HTTPException(status_code=404, detail="Teléfono no encontrado")
    db.delete(db_t); db.commit()
    return {"ok": True}
