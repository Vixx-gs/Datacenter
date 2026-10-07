from fastapi import APIRouter, Depends, HTTPException, Query
from database import get_db
from auth import verificar_token
from typing import Optional, List
import schemas
import firestore_cache as fc

router = APIRouter(prefix="/vehiculos", tags=["vehiculos"])

def _fecha_str(v) -> str:
    """Convierte cualquier valor de fecha Firestore a 'YYYY-MM-DD' o ''."""
    if not v:
        return ""
    if isinstance(v, str):
        s = v.split("T")[0].split(" ")[0].strip()
        import re
        if re.match(r"^\d{1,2}/\d{1,2}/\d{4}$", s):
            parts = s.split("/")
            return f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
        return s
    if hasattr(v, "strftime"):
        try:
            return v.strftime("%Y-%m-%d")
        except Exception:
            return str(v).split("T")[0].split(" ")[0]
    return str(v).split("T")[0].split(" ")[0]

def _fecha_es(v) -> str:
    """Devuelve la fecha en formato DD/MM/YYYY para mostrar en el frontend."""
    s = _fecha_str(v)
    if not s:
        return ""
    import re
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        a, m, d = s.split("-")
        return f"{d}/{m}/{a}"
    return s

# Convierte un doc Firestore (camelCase) al formato del API (snake_case)
def _map(doc_id: str, d: dict) -> dict:
    return {
        "matricula":           d.get("matricula") or doc_id,
        "marca":               d.get("marca", ""),
        "modelo":              d.get("modelo", ""),
        "bastidor":            d.get("bastidor", ""),
        "fecha_mat":           _fecha_es(d.get("fechaMat")),
        "destinado_a":         d.get("destinadoA", ""),
        "propiedad":           d.get("propiedad", ""),
        "situacion":           d.get("situacion", ""),
        "estado":              d.get("estado", "ACTIVO"),
        "fecha_incorporacion": _fecha_es(d.get("fechaIncorporacion")),
        "itv":                 _fecha_es(d.get("itv")),
        "tacografo":           _fecha_es(d.get("tacografo")),
        "mantenimiento":       str(d.get("mantenimiento", "")),
        "fecha_fin_mto":       _fecha_es(d.get("fechaFinMto")),
        "km_fin_mto":          str(d.get("kmFinMto", "") if d.get("kmFinMto") else ""),
        "precio_mto":          str(d.get("precioMto", "") if d.get("precioMto") else ""),
        "garantia":            str(d.get("garantia", "")),
        "fecha_fin_garantia":  _fecha_es(d.get("fechaFinGarantia")),
        "km_fin_garantia":     str(d.get("kmFinGarantia", "") if d.get("kmFinGarantia") else ""),
        "kilometros":          str(d.get("kilometros", "") if d.get("kilometros") else ""),
        "gps":                 d.get("gps", ""),
        "origen":              d.get("origen", ""),
        "equipamiento":        d.get("equipamiento", ""),
        "observaciones":       d.get("observaciones", ""),
        "conductor_actual":    d.get("conductorActual", ""),
        "conductor_actual_id": "",   # no existe en Firestore; se resuelve via driverAssignments
        "tipo_conductor":      "",
        "created_at":          None,
        "updated_at":          None,
    }

def _parece_id(s: str) -> bool:
    if not s or s == "—":
        return True
    return " " not in s.strip() and s.replace("-", "").isalnum() and len(s) < 30

def _build_clients_name_map() -> dict:
    """Devuelve {doc_id: nombre} para todos los clientes en caché."""
    m: dict = {}
    for doc_id, d in fc.get_clients():
        nombre = d.get("nombre", "")
        if nombre:
            m[doc_id] = nombre
    return m

def _build_conductores_activos_map() -> dict:
    """Devuelve {vehiculo_id: nombre_conductor} para conductores activos."""
    names_by_id = _build_clients_name_map()
    mapa: dict = {}
    for _, d in fc.get_driver_assignments():
        if d.get("fechaFin"):
            continue
        vid       = d.get("vehicleId", "")
        raw_name  = d.get("driverName", "") or ""
        driver_id = d.get("driverId", "") or ""
        if _parece_id(raw_name) and driver_id:
            name = names_by_id.get(driver_id, raw_name or driver_id)
        else:
            name = raw_name or driver_id
        if vid and name:
            mapa.setdefault(vid, []).append(name)
    return {vid: ", ".join(dict.fromkeys(names)) for vid, names in mapa.items()}

def _build_conductor_id_map() -> dict:
    """Devuelve {vehiculo_id: driver_id} para el conductor activo más reciente."""
    ids: dict = {}
    for _, d in fc.get_driver_assignments():
        if d.get("fechaFin"):
            continue
        vid       = d.get("vehicleId", "")
        driver_id = d.get("driverId", "") or ""
        if vid and driver_id and vid not in ids:
            ids[vid] = driver_id
    return ids

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
    docs = list(
        db.collection("driverAssignments")
          .where("vehicleId", "==", matricula)
          .stream()
    )

    def parece_id(s: str) -> bool:
        """True si el string parece un ID técnico en vez de un nombre real."""
        if not s or s == "—":
            return True
        # Sin espacios y todo alfanumérico → probablemente un ID
        return " " not in s.strip() and s.replace("-", "").isalnum() and len(s) < 30

    # Recoger driver_ids que necesitan resolución
    driver_ids_a_resolver = set()
    raw = []
    for doc in docs:
        d = doc.to_dict()
        driver_name = d.get("driverName", "") or ""
        driver_id   = d.get("driverId", "") or ""
        raw.append({
            "id":           doc.id,
            "vehiculo_id":  d.get("vehicleId", ""),
            "conductor_id": driver_id,
            "cliente_id":   driver_id,   # alias para el routerLink del frontend
            "nombre":       driver_name,
            "_sort_inicio": _fecha_str(d.get("fechaInicio")),
            "fecha_inicio": _fecha_str(d.get("fechaInicio")),  # YYYY-MM-DD; pipe fechaEs lo muestra
            "fecha_fin":    _fecha_str(d.get("fechaFin")),      # YYYY-MM-DD; pipe fechaEs lo muestra
            "accion":       d.get("accion", ""),
        })
        if parece_id(driver_name) and driver_id:
            driver_ids_a_resolver.add(driver_id)

    # Resolver nombres en batch
    nombres_por_id: dict = {}
    for driver_id in driver_ids_a_resolver:
        client_doc = db.collection("clients").document(driver_id).get()
        if client_doc.exists:
            nombres_por_id[driver_id] = client_doc.to_dict().get("nombre", driver_id)
        else:
            # Buscar por campo driverId dentro de clients
            hits = list(db.collection("clients").where("driverId", "==", driver_id).limit(1).stream())
            if hits:
                nombres_por_id[driver_id] = hits[0].to_dict().get("nombre", driver_id)

    # Aplicar nombres resueltos
    for r in raw:
        if parece_id(r["nombre"]) and r["conductor_id"] in nombres_por_id:
            r["nombre"] = nombres_por_id[r["conductor_id"]]
        if not r["nombre"] or r["nombre"] == "—":
            r["nombre"] = "—"

    raw.sort(key=lambda x: x["_sort_inicio"] or "", reverse=True)
    for r in raw:
        r.pop("_sort_inicio", None)
    return raw

@router.get("/{matricula}/conductor-detalle")
def get_conductor_detalle(
    matricula: str,
    db = Depends(get_db),
    _: str = Depends(verificar_token)
):
    """Devuelve datos del conductor actual del vehículo."""
    # Obtener conductor actual desde driverAssignments (ya resuelto)
    conductores_map = _build_conductores_activos_map()
    conductor_nombre = conductores_map.get(matricula, "")

    if not conductor_nombre:
        # Fallback: campo conductorActual de Firestore
        v_ref = db.collection("vehicles").document(matricula).get()
        if not v_ref.exists:
            return None
        conductor_nombre = v_ref.to_dict().get("conductorActual", "")
    if not conductor_nombre:
        return None

    # Buscar por nombre
    docs = list(db.collection("clients").where("nombre", "==", conductor_nombre).limit(1).stream())
    if docs:
        c = docs[0].to_dict()
        return {
            "id":     docs[0].id,
            "nombre": c.get("nombre", conductor_nombre),
            "movil":  c.get("movil", ""),
            "email":  c.get("email", ""),
            "gestor": c.get("gestor", ""),
        }

    # Buscar por ID si el nombre parece un ID
    if _parece_id(conductor_nombre):
        client_doc = db.collection("clients").document(conductor_nombre).get()
        if client_doc.exists:
            c = client_doc.to_dict()
            return {
                "id":     client_doc.id,
                "nombre": c.get("nombre", conductor_nombre),
                "movil":  c.get("movil", ""),
                "email":  c.get("email", ""),
                "gestor": c.get("gestor", ""),
            }

    return {"id": "", "nombre": conductor_nombre, "movil": "", "email": "", "gestor": ""}

@router.get("/garantias/todas")
def get_todas_garantias(
    db = Depends(get_db),
    _: str = Depends(verificar_token)
):
    docs = db.collection("garantias").stream()
    return [{"matricula": d.id, **d.to_dict()} for d in docs]

@router.get("/{matricula}/garantias")
def get_garantias_vehiculo(
    matricula: str,
    db = Depends(get_db),
    _: str = Depends(verificar_token)
):
    doc = db.collection("garantias").document(matricula.upper()).get()
    if not doc.exists:
        return {}
    return doc.to_dict()

@router.get("/{matricula}", response_model=schemas.VehiculoOut)
def get_vehiculo(
    matricula: str,
    db = Depends(get_db),
    _: str = Depends(verificar_token)
):
    doc = db.collection("vehicles").document(matricula).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")
    m = _map(doc.id, doc.to_dict())
    conductores_map = _build_conductores_activos_map()
    conductor_id_map = _build_conductor_id_map()
    conductor = conductores_map.get(matricula, "")
    if conductor:
        m["conductor_actual"]    = conductor
        m["conductor_actual_id"] = conductor_id_map.get(matricula, "")
        m["tipo_conductor"]      = "actual"
    return m

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
        "fecha_mat": "fechaMat", "gps": "gps", "origen": "origen",
        "equipamiento": "equipamiento",
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
