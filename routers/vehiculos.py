from fastapi import APIRouter, Depends, HTTPException, Query
from database import get_db
from auth import verificar_token
from typing import Optional, List
import schemas
import firestore_cache as fc

router = APIRouter(prefix="/vehiculos", tags=["vehiculos"])

# Convierte un doc Firestore (camelCase) al formato del API (snake_case)
def _map(doc_id: str, d: dict) -> dict:
    return {
        "matricula":           d.get("matricula") or doc_id,
        "marca":               d.get("marca", ""),
        "modelo":              d.get("modelo", ""),
        "bastidor":            d.get("bastidor", ""),
        "fecha_mat":           d.get("fechaMat", ""),
        "destinado_a":         d.get("destinadoA", ""),
        "propiedad":           d.get("propiedad", ""),
        "situacion":           d.get("situacion", ""),
        "estado":              d.get("estado", "ACTIVO"),
        "fecha_incorporacion": d.get("fechaIncorporacion", ""),
        "itv":                 d.get("itv", ""),
        "tacografo":           d.get("tacografo", ""),
        "mantenimiento":       str(d.get("mantenimiento", "")),
        "fecha_fin_mto":       d.get("fechaFinMto", ""),
        "km_fin_mto":          str(d.get("kmFinMto", "") if d.get("kmFinMto") else ""),
        "precio_mto":          str(d.get("precioMto", "") if d.get("precioMto") else ""),
        "garantia":            str(d.get("garantia", "")),
        "fecha_fin_garantia":  d.get("fechaFinGarantia", ""),
        "km_fin_garantia":     str(d.get("kmFinGarantia", "") if d.get("kmFinGarantia") else ""),
        "kilometros":          str(d.get("kilometros", "") if d.get("kilometros") else ""),
        "equipamiento":        d.get("equipamiento", ""),
        "observaciones":       d.get("observaciones", ""),
        "conductor_actual":    d.get("conductorActual", ""),
        "conductor_actual_id": "",   # no existe en Firestore; se resuelve via driverAssignments
        "tipo_conductor":      "",
        "created_at":          None,
        "updated_at":          None,
    }

def _build_conductores_activos_map() -> dict:
    mapa: dict = {}
    for _, d in fc.get_driver_assignments():
        if d.get("fechaFin"):
            continue
        vid  = d.get("vehicleId", "")
        name = d.get("driverName", "") or d.get("driverId", "")
        if vid and name:
            mapa.setdefault(vid, []).append(name)
    return {vid: ", ".join(names) for vid, names in mapa.items()}

@router.get("/", response_model=List[schemas.VehiculoOut])
def get_vehiculos(
    estado:      Optional[str] = Query(None),
    destinado_a: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 2000,
    db = Depends(get_db),
    _: str = Depends(verificar_token)
):
    conductores_map = _build_conductores_activos_map()
    result = []
    for mat, d in fc.get_vehicles():
        if estado      and d.get("estado")     != estado:      continue
        if destinado_a and d.get("destinadoA") != destinado_a: continue
        m = _map(mat, d)
        activos = conductores_map.get(mat, "")
        if activos:
            m["conductor_actual"] = activos
        result.append(m)
    result.sort(key=lambda x: x["matricula"])
    return result[skip:skip + limit]

@router.get("/{matricula}/historial")
def get_historial_vehiculo(
    matricula: str,
    db = Depends(get_db),
    _: str = Depends(verificar_token)
):
    docs = (
        db.collection("driverAssignments")
          .where("vehicleId", "==", matricula)
          .stream()
    )
    registros = [
        {
            "id":           doc.id,
            "vehiculo_id":  doc.to_dict().get("vehicleId", ""),
            "conductor_id": doc.to_dict().get("driverId", ""),
            "nombre":       doc.to_dict().get("driverName", "—"),
            "fecha_inicio": doc.to_dict().get("fechaInicio", ""),
            "fecha_fin":    doc.to_dict().get("fechaFin", ""),
            "accion":       doc.to_dict().get("accion", ""),
        }
        for doc in docs
    ]
    registros.sort(key=lambda x: x["fecha_inicio"] or "", reverse=True)
    return registros

@router.get("/{matricula}/conductor-detalle")
def get_conductor_detalle(
    matricula: str,
    db = Depends(get_db),
    _: str = Depends(verificar_token)
):
    """Devuelve datos del conductor actual del vehículo."""
    v_ref = db.collection("vehicles").document(matricula).get()
    if not v_ref.exists:
        return None
    conductor_nombre = v_ref.to_dict().get("conductorActual", "")
    if not conductor_nombre:
        return None
    # Buscar el conductor por nombre en la colección clients
    docs = list(db.collection("clients").where("nombre", "==", conductor_nombre).limit(1).stream())
    if not docs:
        return {"id": "", "nombre": conductor_nombre, "movil": "", "email": "", "gestor": ""}
    c = docs[0].to_dict()
    return {
        "id":     docs[0].id,
        "nombre": c.get("nombre", conductor_nombre),
        "movil":  c.get("movil", ""),
        "email":  c.get("email", ""),
        "gestor": c.get("gestor", ""),
    }

@router.get("/{matricula}", response_model=schemas.VehiculoOut)
def get_vehiculo(
    matricula: str,
    db = Depends(get_db),
    _: str = Depends(verificar_token)
):
    doc = db.collection("vehicles").document(matricula).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")
    return _map(doc.id, doc.to_dict())

@router.put("/{matricula}", response_model=schemas.VehiculoOut)
def update_vehiculo(
    matricula: str,
    vehiculo: schemas.VehiculoUpdate,
    db = Depends(get_db),
    _: str = Depends(verificar_token)
):
    doc_ref = db.collection("vehicles").document(matricula)
    if not doc_ref.get().exists:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")
    # Mapa snake_case → camelCase para Firestore
    campo_map = {
        "marca": "marca", "modelo": "modelo", "bastidor": "bastidor",
        "destinado_a": "destinadoA", "propiedad": "propiedad",
        "situacion": "situacion", "estado": "estado",
        "fecha_incorporacion": "fechaIncorporacion",
        "itv": "itv", "tacografo": "tacografo",
        "observaciones": "observaciones",
        "conductor_actual": "conductorActual",
        "fecha_mat": "fechaMat", "equipamiento": "equipamiento",
        "fecha_fin_mto": "fechaFinMto", "fecha_fin_garantia": "fechaFinGarantia",
    }
    update_data = {}
    data = vehiculo.model_dump(exclude_unset=True)
    for snake, camel in campo_map.items():
        if snake in data:
            update_data[camel] = data[snake]
    if update_data:
        doc_ref.update(update_data)
    return _map(matricula, doc_ref.get().to_dict())
