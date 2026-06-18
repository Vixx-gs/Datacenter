from fastapi import APIRouter, Depends, Query
from database import get_db
from auth import verificar_token
from typing import List, Optional
import schemas, uuid

router = APIRouter(prefix="/registro", tags=["registro"])

def _map(doc_id: str, d: dict) -> dict:
    return {
        "id":               doc_id,
        "matricula":        d.get("matricula", ""),
        "tipo_vehiculo":    d.get("tipoVehiculo", ""),
        "fecha_mat":        d.get("fechaMat", ""),
        "autorizacion":     d.get("autorizacion", ""),
        "fecha_adscripcion":d.get("fechaAdscripcion", ""),
        "empresa":          d.get("empresa", ""),
        "flota":            d.get("flota", ""),
        "propiedad":        d.get("propiedad", ""),
        "conductor":        d.get("conductor", ""),
        "fecha_inicio":     d.get("fechaInicio", ""),
        "tipo_contrato":    d.get("tipoContrato", ""),
        "arrendatario":     d.get("arrendatario", ""),
        "cuota_socio":      d.get("cuotaSocio"),
        "financiera":       d.get("financiera", ""),
        "tipo_finan":       d.get("tipoFinan", ""),
        "cuota_finan":      d.get("cuotaFinan"),
        "created_at":       None,
    }

@router.get("/", response_model=List[schemas.RegistroEmpresaOut])
def get_registro(
    empresa: Optional[str] = Query(None),
    skip: int = 0, limit: int = 500,
    db = Depends(get_db)
):
    docs = db.collection("registroEmpresas").stream()
    result = []
    for doc in docs:
        d = doc.to_dict()
        if empresa and d.get("empresa", "") != empresa:
            continue
        result.append(_map(doc.id, d))
    return result[skip:skip + limit]

@router.post("/", response_model=schemas.RegistroEmpresaOut)
def create_registro(registro: schemas.RegistroEmpresaCreate, db = Depends(get_db)):
    data   = registro.model_dump()
    doc_id = data.get("id") or str(uuid.uuid4())
    fs_data = {
        "matricula":        data.get("matricula", ""),
        "tipoVehiculo":     data.get("tipo_vehiculo", ""),
        "fechaMat":         data.get("fecha_mat", ""),
        "autorizacion":     data.get("autorizacion", ""),
        "fechaAdscripcion": data.get("fecha_adscripcion", ""),
        "empresa":          data.get("empresa", ""),
        "flota":            data.get("flota", ""),
        "propiedad":        data.get("propiedad", ""),
        "conductor":        data.get("conductor", ""),
        "fechaInicio":      data.get("fecha_inicio", ""),
        "tipoContrato":     data.get("tipo_contrato", ""),
        "arrendatario":     data.get("arrendatario", ""),
        "cuotaSocio":       data.get("cuota_socio"),
        "financiera":       data.get("financiera", ""),
        "tipoFinan":        data.get("tipo_finan", ""),
        "cuotaFinan":       data.get("cuota_finan"),
    }
    db.collection("registroEmpresas").document(doc_id).set(fs_data)
    return _map(doc_id, fs_data)
