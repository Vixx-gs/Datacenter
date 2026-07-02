from fastapi import APIRouter, Depends, Query
from database import get_db
from auth import verificar_token
from typing import List, Optional
import schemas, uuid

router = APIRouter(prefix="/cambios", tags=["cambios"])

def _map(doc_id: str, d: dict) -> dict:
    return {
        "id":              doc_id,
        "fecha_inicio":    d.get("fechaInicio", ""),
        "matricula_entra": d.get("matriculaEntra", ""),
        "conductor_entra": d.get("conductorEntra", ""),
        "fecha_fin":       d.get("fechaFin", ""),
        "matricula_sale":  d.get("matriculaSale", ""),
        "conductor_sale":  d.get("conductorSale", ""),
        "created_at":      None,
    }

@router.get("/", response_model=List[schemas.CambioVehiculoOut])
def get_cambios(skip: int = 0, limit: int = 200, db = Depends(get_db)):
    docs = db.collection("cambiosVehiculos").stream()
    result = [_map(doc.id, doc.to_dict()) for doc in docs]
    result.sort(key=lambda x: x["fecha_inicio"] or "", reverse=True)
    return result[skip:skip + limit]

@router.post("/", response_model=schemas.CambioVehiculoOut)
def create_cambio(cambio: schemas.CambioVehiculoCreate, db = Depends(get_db)):
    data  = cambio.model_dump()
    doc_id = data.get("id") or str(uuid.uuid4())
    fs_data = {
        "fechaInicio":    data.get("fecha_inicio", ""),
        "matriculaEntra": data.get("matricula_entra", ""),
        "conductorEntra": data.get("conductor_entra", ""),
        "fechaFin":       data.get("fecha_fin", ""),
        "matriculaSale":  data.get("matricula_sale", ""),
        "conductorSale":  data.get("conductor_sale", ""),
    }
    db.collection("cambiosVehiculos").document(doc_id).set(fs_data)
    return _map(doc_id, fs_data)
