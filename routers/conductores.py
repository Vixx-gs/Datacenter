from fastapi import APIRouter, Depends, HTTPException, Query
from database import get_db
from auth import verificar_token
from typing import List, Optional
import schemas
import firestore_cache as fc

router = APIRouter(prefix="/conductores", tags=["conductores"])

# Mapeo de un doc Firestore "clients" al formato de conductor del API
# Firestore guarda las fechas en YYYY-MM-DD (cadena)
def _map(doc_id: str, d: dict, vehiculo_map: dict = None) -> dict:
    return {
        "id":              doc_id,
        "nombre":          d.get("nombre", ""),
        "nombre_propio":   d.get("nombrePropio", ""),
        "apellidos":       d.get("apellidos", ""),
        "nif":             d.get("nif", "") or doc_id,
        "movil":           d.get("movil", ""),
        "email":           d.get("email", ""),
        "fecha_nac":       d.get("fechaNacimiento", ""),
        "gestor":          d.get("gestor", ""),
        "empresa":         d.get("empresa", ""),
        # vehiculo se resuelve desde el mapa vehicles.conductorActual
        "vehiculo":        (vehiculo_map or {}).get(doc_id, ""),
        # fechaAlta = Fecha Alta del sheet = fecha real de inicio
        "fecha_inicio":    d.get("fechaAlta", ""),
        # fechaIngreso = Fecha Prevista del sheet = fecha esperada de inicio
        "fecha_prevista":  d.get("fechaIngreso", ""),
        "fecha_baja":      d.get("fechaBaja", ""),
        # situacion = DEFINITIVO / PERDIDO / BAJA (equivale a codigo_socio)
        "codigo_socio":    d.get("situacion", ""),
        # codigo = número de socio (campo CODIGO del sheet)
        "num_socio":       d.get("codigo", ""),
        "direccion":       d.get("direccion", ""),
        "poblacion":       d.get("poblacion", ""),
        "codigo_postal":   d.get("codigoP", ""),
        "provincia":       d.get("provincia", ""),
        "estado":          d.get("estado", ""),
        "created_at":      None,
        "updated_at":      None,
    }

def _build_vehiculo_map() -> dict:
    result = {}
    for mat, d in fc.get_vehicles():
        nombre = d.get("conductorActual", "")
        if nombre:
            result[nombre] = mat
    return result

@router.get("/ex-socios", response_model=List[schemas.ConductorOut2])
def get_ex_socios(
    empresa: Optional[str] = Query(None),
    skip: int = 0, limit: int = 2000,
    db = Depends(get_db),
    _: str = Depends(verificar_token)
):
    veh_map = _build_vehiculo_map()
    result = []
    for doc_id, d in fc.get_clients():
        if d.get("estado", "").lower() not in ("ex-socio", "ex socio", "exsocio"):
            continue
        if empresa and d.get("empresa", "").upper() != empresa.upper():
            continue
        result.append(_map(doc_id, d, veh_map))
    result.sort(key=lambda x: x["nombre"])
    return result[skip:skip + limit]

@router.get("/", response_model=List[schemas.ConductorOut2])
def get_conductores(
    empresa: Optional[str] = Query(None),
    gestor:  Optional[str] = Query(None),
    estado:  Optional[str] = Query(None),
    skip: int = 0, limit: int = 2000,
    db = Depends(get_db),
    _: str = Depends(verificar_token)
):
    veh_map = _build_vehiculo_map()
    result = []
    for doc_id, d in fc.get_clients():
        estado_doc = d.get("estado", "")
        situacion  = d.get("situacion", "").upper()

        if not estado:
            if estado_doc.lower() == "ex-socio":
                continue
            if situacion != "DEFINITIVO":
                continue
        else:
            if estado_doc.lower() != estado.lower():
                continue

        if empresa and d.get("empresa", "").upper() != empresa.upper():
            continue
        if gestor  and d.get("gestor", "").lower()  != gestor.lower():
            continue
        result.append(_map(doc_id, d, veh_map))
    result.sort(key=lambda x: x["nombre"])
    return result[skip:skip + limit]

@router.get("/{id}/historial-vehiculos")
def get_historial_vehiculos(
    id: str,
    db = Depends(get_db),
    _: str = Depends(verificar_token)
):
    docs = (
        db.collection("driverAssignments")
          .where("driverId", "==", id)
          .stream()
    )
    registros = [
        {
            "vehiculo_id":  doc.to_dict().get("vehicleId", ""),
            "conductor_id": doc.to_dict().get("driverId", ""),
            "fecha_inicio": doc.to_dict().get("fechaInicio", ""),
            "fecha_fin":    doc.to_dict().get("fechaFin", ""),
            "accion":       doc.to_dict().get("accion", ""),
        }
        for doc in docs
    ]
    registros.sort(key=lambda x: x["fecha_inicio"] or "", reverse=True)
    return registros

@router.get("/{id}", response_model=schemas.ConductorOut2)
def get_conductor(
    id: str,
    db = Depends(get_db),
    _: str = Depends(verificar_token)
):
    doc = db.collection("clients").document(id).get()
    if not doc.exists:
        # Intentar buscar por NIF
        matches = list(db.collection("clients").where("nif", "==", id).limit(1).stream())
        if not matches:
            raise HTTPException(status_code=404, detail="Conductor no encontrado")
        doc = matches[0]
    return _map(doc.id, doc.to_dict())

@router.put("/{id}", response_model=schemas.ConductorOut2)
def update_conductor(
    id: str,
    conductor: schemas.ConductorUpdate,
    db = Depends(get_db),
    _: str = Depends(verificar_token)
):
    doc_ref = db.collection("clients").document(id)
    if not doc_ref.get().exists:
        raise HTTPException(status_code=404, detail="Conductor no encontrado")
    campo_map = {
        "nombre": "nombre", "nombre_propio": "nombrePropio",
        "apellidos": "apellidos", "nif": "nif",
        "movil": "movil", "email": "email",
        "fecha_nac": "fechaNacimiento", "gestor": "gestor",
        "empresa": "empresa", "estado": "estado",
        "fecha_inicio": "fechaAlta", "fecha_baja": "fechaBaja",
        "codigo_socio": "situacion", "num_socio": "codigo",
        "direccion": "direccion", "poblacion": "poblacion",
        "codigo_postal": "codigoP", "provincia": "provincia",
    }
    update_data = {}
    data = conductor.model_dump(exclude_unset=True)
    for snake, camel in campo_map.items():
        if snake in data:
            update_data[camel] = data[snake]
    if update_data:
        doc_ref.update(update_data)
    return _map(id, doc_ref.get().to_dict())
