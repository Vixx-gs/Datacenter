from fastapi import APIRouter, Query
from typing import List, Optional
import schemas
import sheets_cache as sc
import firestore_cache as fc

router = APIRouter(prefix="/contratos", tags=["contratos"])

def _build_clients_name_map() -> dict:
    m: dict = {}
    for doc_id, d in fc.get_clients():
        nombre = d.get("nombre", "")
        if nombre:
            m[doc_id] = nombre
    return m

def _parece_id(s: str) -> bool:
    if not s or s == "—":
        return True
    return " " not in s.strip() and s.replace("-", "").isalnum() and len(s) < 30


@router.get("/", response_model=List[schemas.ContratoOut])
def get_contratos(
    vehiculo_id: Optional[str] = Query(None),
    empresa_id:  Optional[str] = Query(None),
    estado:      Optional[str] = Query(None),
):
    """
    Lee los contratos de alquiler directamente de Google Sheets (caché 5 min).
    """
    rows   = sc.get_contratos()
    names_by_id = _build_clients_name_map()
    result = []

    for row in rows:
        id_contrato = sc.clean(row.get("AlqContratoID", ""))
        if not id_contrato:
            continue

        cliente_id = sc.clean(row.get("ClienteID", ""))

        m = {
            "id":                    id_contrato,
            "num_contrato":          sc.clean(row.get("NumContrato", "")),
            "tipo_contrato":         sc.clean(row.get("TipoContrato", "")),
            "vehiculo_id":           sc.clean(row.get("VehiculoID", "")),
            "cliente_id":            cliente_id,
            "empresa_id":            sc.clean(row.get("EmpresaID", "")),
            "fecha_inicio":          sc.clean(row.get("FechaInicio", "")),
            "fecha_fin":             sc.clean(row.get("FechaFin", "")),
            "num_cuotas":            sc.clean_int(row.get("NumCuotas", "")),
            "cuota_base":            sc.clean_float(row.get("CuotaBase", "")),
            "incluye_mantenimiento": None,
            "incluye_neumaticos":    None,
            "condiciones":           sc.clean(row.get("Condiciones", "")),
            "fianza":                sc.clean_float(row.get("Fianza", "")),
            "entrada":               sc.clean_float(row.get("Entrada", "")),
            "valor_residual":        sc.clean_float(row.get("ValorResidual", "")),
            "nombre_conductor":      (lambda raw: names_by_id.get(raw, raw) if _parece_id(raw) else raw)(
                sc.clean(row.get("NombreConductor", "") or row.get("Conductor", "") or row.get("ClienteID", ""))
            ),
            "estado":                "ACTIVO",
            "created_at":            None,
        }

        if vehiculo_id and m["vehiculo_id"] != vehiculo_id:
            continue
        if empresa_id  and m["empresa_id"]  != empresa_id:
            continue
        if estado      and m["estado"]       != estado:
            continue

        result.append(m)

    result.sort(key=lambda x: x["fecha_inicio"] or "", reverse=True)
    return result
