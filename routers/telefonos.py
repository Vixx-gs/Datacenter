from fastapi import APIRouter, Depends, HTTPException, Query
from database import get_db
from typing import List, Optional
import schemas, uuid

router = APIRouter(prefix="/telefonos", tags=["telefonos"])


def _map(doc_id: str, d: dict) -> dict:
    return {
        "id":        doc_id,
        "telefono":  d.get("telefono", ""),
        "extension": d.get("extension", ""),
        "persona":   d.get("persona", ""),
        "empresa":   d.get("empresa", ""),
        "email":     d.get("email", ""),
        "pertenece": d.get("pertenece", ""),
        "area":      d.get("area", ""),
        "created_at": None,
    }


@router.get("/", response_model=List[schemas.TelefonoOut])
def get_telefonos(
    empresa: Optional[str] = Query(None),
    db = Depends(get_db),
):
    docs = db.collection("telefonos").stream()
    result = []
    for doc in docs:
        d = doc.to_dict()
        if empresa and d.get("empresa", "") != empresa:
            continue
        result.append(_map(doc.id, d))
    result.sort(key=lambda x: (x["empresa"] or "", x["extension"] or ""))
    return result


@router.post("/", response_model=schemas.TelefonoOut)
def create_telefono(telefono: schemas.TelefonoCreate, db = Depends(get_db)):
    data   = telefono.model_dump()
    doc_id = data.get("id") or str(uuid.uuid4())
    fs_data = {k: v for k, v in data.items() if k != "id" and v is not None}
    db.collection("telefonos").document(doc_id).set(fs_data)
    return _map(doc_id, fs_data)


@router.put("/{id}", response_model=schemas.TelefonoOut)
def update_telefono(id: str, telefono: schemas.TelefonoCreate, db = Depends(get_db)):
    ref = db.collection("telefonos").document(id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Teléfono no encontrado")
    data = {k: v for k, v in telefono.model_dump(exclude_unset=True).items() if k != "id"}
    ref.update(data)
    return _map(id, ref.get().to_dict())


@router.delete("/{id}")
def delete_telefono(id: str, db = Depends(get_db)):
    ref = db.collection("telefonos").document(id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Teléfono no encontrado")
    ref.delete()
    return {"ok": True}
