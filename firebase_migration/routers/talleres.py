from fastapi import APIRouter, Depends, Query
from database import get_db
from auth import verificar_token
from typing import List, Optional
import schemas
import firestore_cache as fc
from datetime import datetime

router = APIRouter(prefix="/talleres", tags=["talleres"])

def parse_fecha(f: str):
    if not f or not f.strip(): return None
    s = f.strip().split("T")[0]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try: return datetime.strptime(s, fmt)
        except: pass
    return None

def _map_taller(doc_id: str, d: dict) -> dict:
    return {
        "id":               doc_id,
        "nombre":           d.get("nombre", ""),
        "telefono":         d.get("telefono", ""),
        "persona_contacto": d.get("personaContacto", ""),
        "direccion":        d.get("direccion", ""),
    }

def _map_entrada(doc_id: str, d: dict) -> dict:
    return {
        "id":            doc_id,
        "matricula":     d.get("matricula", ""),
        "taller_id":     d.get("tallerId", ""),
        "taller_nombre": d.get("tallerNombre", ""),
        "fecha_entrada": d.get("fechaEntrada", ""),
        "fecha_prevista":d.get("fechaPrevistaFin", ""),
        "fecha_fin":     d.get("fechaFin", ""),
        "tipo_averia":   d.get("tipoAveria", ""),
        "notas":         d.get("notas", ""),
        "created_at":    None,
        "updated_at":    None,
    }

@router.get("/lista", response_model=List[schemas.TallerOut])
def get_talleres_lista(db = Depends(get_db)):
    docs = db.collection("workshops").stream()
    return [_map_taller(doc.id, doc.to_dict()) for doc in docs]

@router.get("/entradas")
def get_entradas(
    matricula: Optional[str] = Query(None),
    activos:   Optional[bool] = Query(None),
    skip: int = 0, limit: int = 500,
    db = Depends(get_db),
    _: str = Depends(verificar_token)
):
    registros = []
    for doc_id, d in fc.get_workshop_entries():
        if matricula and d.get("matricula", "") != matricula:
            continue
        registros.append(_map_entrada(doc_id, d))
    registros.sort(key=lambda x: x["fecha_entrada"] or "", reverse=True)

    if activos:
        hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        filtrados = []
        for r in registros:
            ff = parse_fecha(r["fecha_fin"])
            if ff is None or ff >= hoy:
                filtrados.append(r)
        return filtrados[skip:skip + limit]

    return registros[skip:skip + limit]

@router.post("/entradas", response_model=schemas.TallerEntradaOut)
def create_entrada(entrada: schemas.TallerEntradaCreate, db = Depends(get_db)):
    data = entrada.model_dump()
    doc_id = data.get("id", "")
    if not doc_id:
        import uuid
        doc_id = str(uuid.uuid4())
    # Convertir snake_case a camelCase
    fs_data = {
        "matricula":       data.get("matricula", ""),
        "tallerId":        data.get("taller_id", ""),
        "tallerNombre":    data.get("taller_nombre", ""),
        "fechaEntrada":    data.get("fecha_entrada", ""),
        "fechaPrevistaFin":data.get("fecha_prevista", ""),
        "fechaFin":        data.get("fecha_fin", ""),
        "tipoAveria":      data.get("tipo_averia", ""),
        "notas":           data.get("notas", ""),
    }
    db.collection("workshopEntries").document(doc_id).set(fs_data)
    return _map_entrada(doc_id, fs_data)
