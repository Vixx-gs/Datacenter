from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
from auth import verificar_token
import models, schemas
from datetime import datetime

router = APIRouter(prefix="/talleres", tags=["talleres"])

def parse_fecha(f: str):
    if not f or not f.strip():
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(f.strip(), fmt)
        except:
            continue
    return None

@router.get("/lista", response_model=List[schemas.TallerOut])
def get_talleres_lista(db: Session = Depends(get_db)):
    return db.query(models.Taller).all()

@router.get("/entradas")
def get_entradas(
    matricula: Optional[str] = Query(None),
    activos: Optional[bool] = Query(None),
    skip: int = 0, limit: int = 500,
    db: Session = Depends(get_db),
    _: str = Depends(verificar_token)
):
    q = db.query(models.TallerEntrada)
    if matricula:
        q = q.filter(models.TallerEntrada.matricula == matricula)

    registros = q.order_by(models.TallerEntrada.fecha_entrada.desc()).all()

    if activos:
        hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        resultado = []
        for r in registros:
            fecha_fin = parse_fecha(r.fecha_fin)
            # Activo = sin fecha_fin O fecha_fin >= hoy
            if fecha_fin is None or fecha_fin >= hoy:
                resultado.append(r)
        return resultado[skip:skip+limit]

    return registros[skip:skip+limit]

@router.post("/entradas", response_model=schemas.TallerEntradaOut)
def create_entrada(entrada: schemas.TallerEntradaCreate, db: Session = Depends(get_db)):
    db_e = models.TallerEntrada(**entrada.model_dump())
    db.add(db_e); db.commit(); db.refresh(db_e)
    return db_e