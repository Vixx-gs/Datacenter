from fastapi import APIRouter, Depends, Query
from database import get_db
from auth import verificar_token
from typing import List, Optional
import schemas

router = APIRouter(prefix="/ingresos", tags=["ingresos"])

def _fecha_es(v) -> str:
    import re
    if not v:
        return ""
    s = str(v).split("T")[0].split(" ")[0].strip()
    if re.match(r"^\d{1,2}/\d{1,2}/\d{4}$", s):
        return s
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        a, m, d = s.split("-")
        return f"{d}/{m}/{a}"
    return s

def _fecha_str(v) -> str:
    """Para ordenación, normaliza a YYYY-MM-DD."""
    import re
    if not v:
        return ""
    s = str(v).split("T")[0].split(" ")[0].strip()
    if re.match(r"^\d{1,2}/\d{1,2}/\d{4}$", s):
        parts = s.split("/")
        return f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
    return s

def _map(doc_id: str, d: dict) -> dict:
    return {
        "id":          doc_id,
        "nombre_mes":  d.get("nombreMes", ""),
        "proveedor":   d.get("proveedor", ""),
        "nif":         d.get("nif", ""),
        "codigo":      d.get("codigo", ""),
        "familia":     d.get("familia", ""),
        "num_factura": d.get("numFactura"),
        "ref_factura": d.get("refFactura", ""),
        "fecha":       _fecha_es(d.get("fecha", "")),
        "_sort_fecha": _fecha_str(d.get("fecha", "")),
        "cooperativa": d.get("cooperativa", ""),
        "created_at":  None,
    }

@router.get("/", response_model=List[schemas.IngresoOut])
def get_ingresos(
    cooperativa: Optional[str] = Query(None),
    ejercicio:   Optional[int] = Query(None),
    trimestre:   Optional[int] = Query(None),
    skip: int = 0, limit: int = 1000,
    db = Depends(get_db)
):
    docs = db.collection("ingresos").stream()
    result = []
    for doc in docs:
        d = doc.to_dict()
        if cooperativa and d.get("cooperativa", "") != cooperativa: continue
        if ejercicio   and d.get("ejercicio") != ejercicio:          continue
        if trimestre   and d.get("trimestre") != trimestre:          continue
        result.append(_map(doc.id, d))
    result.sort(key=lambda x: x["_sort_fecha"] or "", reverse=True)
    for r in result:
        r.pop("_sort_fecha", None)
    return result[skip:skip + limit]
