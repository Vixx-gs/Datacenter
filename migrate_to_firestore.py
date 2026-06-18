#!/usr/bin/env python3
"""
migrate_to_firestore.py
=======================
Genera todos los archivos del backend migrados de PostgreSQL/SQLAlchemy
a Firebase Firestore en la carpeta firebase_migration/.

Ejecutar con:
    python migrate_to_firestore.py

Luego, revisar los archivos generados y copiar al proyecto con:
    bash firebase_migration/deploy_vps.sh
"""

import sys
import shutil
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).parent
OUT_DIR  = BASE_DIR / "firebase_migration"

def write_file(relative_path: str, content: str):
    full_path = OUT_DIR / relative_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content, encoding="utf-8")
    print(f"  ✓ {relative_path}")

def backup_original():
    bak = BASE_DIR / "backup_postgres"
    bak.mkdir(exist_ok=True)
    (bak / "routers").mkdir(exist_ok=True)
    for fn in ["database.py", "models.py", "schemas.py", "sync_sheets.py", "requirements.txt"]:
        src = BASE_DIR / fn
        if src.exists():
            shutil.copy2(src, bak / fn)
    routers_src = BASE_DIR / "routers"
    if routers_src.exists():
        for f in routers_src.glob("*.py"):
            shutil.copy2(f, bak / "routers" / f.name)
    print(f"  ✓ Backup guardado en backup_postgres/")

# ─────────────────────────────────────────────────────────────────────────────
#  CONTENIDO DE CADA ARCHIVO
# ─────────────────────────────────────────────────────────────────────────────

DATABASE_PY = '''\
"""
database.py  –  Conexión a Firebase Firestore (reemplaza SQLAlchemy/PostgreSQL)
Usa google-cloud-firestore con credenciales de Service Account.
"""
from google.cloud import firestore
from google.oauth2.service_account import Credentials
from pathlib import Path

_BASE = Path(__file__).parent
_SA   = _BASE / "ai-studio-applet-webapp-55a1a-firebase-adminsdk-fbsvc-67d511e6d4.json"

_creds = Credentials.from_service_account_file(str(_SA))
db = firestore.Client(
    project     = "ai-studio-applet-webapp-55a1a",
    credentials = _creds,
    database    = "ai-studio-7801edee-96c4-47bb-8194-68abcf65e834",
)

def get_db():
    """Dependency injection compatible con FastAPI (igual que el antiguo get_db)."""
    return db
'''

# ── REQUIREMENTS ──────────────────────────────────────────────────────────────

REQUIREMENTS_TXT = '''\
fastapi
uvicorn[standard]
pyjwt
bcrypt
python-dotenv
google-cloud-firestore
google-auth
'''

# ── VEHICULOS ROUTER ──────────────────────────────────────────────────────────

VEHICULOS_PY = '''\
from fastapi import APIRouter, Depends, HTTPException, Query
from database import get_db
from auth import verificar_token
from typing import Optional, List
import schemas

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

def _build_conductores_activos_map(db) -> dict:
    """
    Recorre driverAssignments y devuelve un dict:
        vehicleId → "Conductor A, Conductor B"
    Solo incluye asignaciones SIN fechaFin (activas).
    Si hay más de uno, los une con ", ".
    """
    mapa: dict = {}
    for doc in db.collection("driverAssignments").stream():
        d = doc.to_dict()
        if d.get("fechaFin"):          # tiene fecha fin → no está activo
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
    # Construir mapa de conductores activos desde driverAssignments
    conductores_map = _build_conductores_activos_map(db)

    docs = db.collection("vehicles").stream()
    result = []
    for doc in docs:
        d = doc.to_dict()
        if estado      and d.get("estado")      != estado:      continue
        if destinado_a and d.get("destinadoA")  != destinado_a: continue
        m = _map(doc.id, d)
        # Sobreescribir conductor_actual con datos en tiempo real de driverAssignments
        # (soporta múltiples conductores activos separados por ", ")
        activos = conductores_map.get(doc.id, "")
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
'''

# ── CONDUCTORES ROUTER ────────────────────────────────────────────────────────

CONDUCTORES_PY = '''\
from fastapi import APIRouter, Depends, HTTPException, Query
from database import get_db
from auth import verificar_token
from typing import List, Optional
import schemas

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

def _build_vehiculo_map(db) -> dict:
    """Construye dict conductor_nombre → matricula desde la colección vehicles."""
    result = {}
    for doc in db.collection("vehicles").stream():
        d = doc.to_dict()
        nombre = d.get("conductorActual", "")
        mat    = doc.id
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
    docs = db.collection("clients").stream()
    veh_map = _build_vehiculo_map(db)
    result = []
    for doc in docs:
        d = doc.to_dict()
        if d.get("estado", "").lower() not in ("ex-socio", "ex socio", "exsocio"):
            continue
        if empresa and d.get("empresa", "").upper() != empresa.upper():
            continue
        result.append(_map(doc.id, d, veh_map))
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
    docs = db.collection("clients").stream()
    veh_map = _build_vehiculo_map(db)
    result = []
    for doc in docs:
        d = doc.to_dict()
        estado_doc  = d.get("estado", "")
        situacion   = d.get("situacion", "").upper()  # DEFINITIVO / PERDIDO / BAJA

        if not estado:
            # Por defecto: Confirmado + DEFINITIVO (excluye ex-socios)
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
        result.append(_map(doc.id, d, veh_map))
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
'''

# ── SEGUROS ROUTER ────────────────────────────────────────────────────────────

SEGUROS_PY = '''\
from fastapi import APIRouter, Depends, Query
from database import get_db
from auth import verificar_token
from typing import List, Optional
import schemas
from datetime import datetime

router = APIRouter(prefix="/seguros", tags=["seguros"])

def _map(doc_id: str, d: dict) -> dict:
    """Mapea un doc de insurancePolicies (campos en español del sheet) al API."""
    return {
        "id":            doc_id,
        "poliza":        d.get("Nº de Póliza", "") or doc_id,
        "matricula":     d.get("Matrícula", "") or d.get("Matricula", ""),
        "tomador":       d.get("Tomador", ""),
        "tipo":          d.get("Tipo de Seguro", "") or d.get("Tipo", ""),
        "aseguradora":   d.get("Aseguradora", "") or d.get("aseguradora", ""),
        "corredor":      d.get("Corredor", ""),
        "vencimiento":   d.get("Fecha de Vencimiento", "") or d.get("FechaVencimiento", ""),
        "ambito":        d.get("Ámbito", "") or d.get("Ambito", ""),
        "garantias":     d.get("Garantías", "") or d.get("Garantias", ""),
        "estado":        (d.get("Estado", "") or "").upper(),
        "observaciones": d.get("Observaciones", ""),
        "created_at":    None,
    }

@router.get("/", response_model=List[schemas.SeguroOut])
def get_seguros(
    matricula: Optional[str] = Query(None),
    estado:    Optional[str] = Query(None),
    tomador:   Optional[str] = Query(None),
    db = Depends(get_db),
    _: str = Depends(verificar_token)
):
    docs = db.collection("insurancePolicies").stream()
    result = []
    for doc in docs:
        d = doc.to_dict()
        m = _map(doc.id, d)
        if matricula and m["matricula"] != matricula: continue
        if estado    and m["estado"]    != estado.upper(): continue
        if tomador   and m["tomador"]   != tomador: continue
        result.append(m)
    result.sort(key=lambda x: x["vencimiento"] or "")
    return result
'''

# ── FINANCIERAS ROUTER ────────────────────────────────────────────────────────

FINANCIERAS_PY = '''\
from fastapi import APIRouter, Depends, Query
from database import get_db
from auth import verificar_token
from typing import List, Optional
import schemas

router = APIRouter(prefix="/financieras", tags=["financieras"])

def _clean_float(val) -> Optional[float]:
    try:
        v = str(val or "").replace(".", "").replace(",", ".").replace("€", "").strip()
        return float(v) if v else None
    except:
        return None

def _clean_int(val) -> Optional[int]:
    try:
        return int(str(val or "").strip()) if str(val or "").strip() else None
    except:
        return None

def _map(doc_id: str, d: dict) -> dict:
    """Mapea un doc de financialAgreements (campos del sheet) al API."""
    return {
        "id":                 doc_id,
        "num_contrato":       d.get("NumContrato", ""),
        "vehiculo_id":        d.get("VehiculoID", ""),
        "empresa_id":         d.get("EmpresaID", ""),
        "tipo":               d.get("Tipo", ""),
        "fecha_inicio":       d.get("FechaInicio", ""),
        "fecha_fin":          d.get("FechaFin", ""),
        "cuota_mensual":      _clean_float(d.get("CuotaMensual")),
        "num_cuotas":         _clean_int(d.get("NumCuotas")),
        "dia_pago":           _clean_int(d.get("DiaPago")),
        "importe_financiado": _clean_float(d.get("ImporteFinanciado")),
        "valor_residual":     _clean_float(d.get("ValorResidual")),
        "financiera":         d.get("Financiera", ""),
        "gastos_iniciales":   _clean_float(d.get("GastosIniciales")),
        "fianzas":            _clean_float(d.get("Fianzas")),
        "entrada":            _clean_float(d.get("Entrada")),
        "observaciones":      d.get("Comentarios", "") or d.get("Observaciones", "") or d.get("Co", ""),
        "created_at":         None,
    }

@router.get("/", response_model=List[schemas.FinancieraOut])
def get_financieras(
    vehiculo_id: Optional[str] = Query(None),
    empresa_id:  Optional[str] = Query(None),
    tipo:        Optional[str] = Query(None),
    db = Depends(get_db),
    _: str = Depends(verificar_token)
):
    docs = db.collection("financialAgreements").stream()
    result = []
    for doc in docs:
        d = doc.to_dict()
        m = _map(doc.id, d)
        if vehiculo_id and m["vehiculo_id"] != vehiculo_id: continue
        if empresa_id  and m["empresa_id"]  != empresa_id:  continue
        if tipo        and m["tipo"]         != tipo:         continue
        result.append(m)
    result.sort(key=lambda x: x["fecha_inicio"] or "")
    return result
'''

# ── CONTRATOS ROUTER ──────────────────────────────────────────────────────────

CONTRATOS_PY = '''\
from fastapi import APIRouter, Depends, Query
from database import get_db
from auth import verificar_token
from typing import List, Optional
import schemas

router = APIRouter(prefix="/contratos", tags=["contratos"])

def _clean_float(val):
    try:
        v = str(val or "").replace(".", "").replace(",", ".").replace("€", "").strip()
        return float(v) if v else None
    except:
        return None

def _clean_int(val):
    try:
        return int(str(val or "").strip()) if str(val or "").strip() else None
    except:
        return None

def _map(doc_id: str, d: dict) -> dict:
    """Mapea un doc de rentalContracts (campos del sheet) al API."""
    return {
        "id":                    doc_id,
        "num_contrato":          d.get("NumContrato", ""),
        "tipo_contrato":         d.get("TipoContrato", ""),
        "vehiculo_id":           d.get("VehiculoID", ""),
        "cliente_id":            d.get("ClienteID", ""),
        "empresa_id":            d.get("EmpresaID", ""),
        "fecha_inicio":          d.get("FechaInicio", ""),
        "fecha_fin":             d.get("FechaFin", ""),
        "num_cuotas":            _clean_int(d.get("NumCuotas")),
        "cuota_base":            _clean_float(d.get("CuotaBase")),
        "incluye_mantenimiento": None,
        "incluye_neumaticos":    None,
        "condiciones":           d.get("Condiciones", ""),
        "fianza":                _clean_float(d.get("Fianza")),
        "entrada":               _clean_float(d.get("Entrada")),
        "valor_residual":        _clean_float(d.get("ValorResidual")),
        "nombre_conductor":      d.get("NombreConductor", "") or d.get("Conductor", ""),
        "estado":                "ACTIVO",
        "created_at":            None,
    }

@router.get("/", response_model=List[schemas.ContratoOut])
def get_contratos(
    vehiculo_id: Optional[str] = Query(None),
    empresa_id:  Optional[str] = Query(None),
    estado:      Optional[str] = Query(None),
    db = Depends(get_db),
    _: str = Depends(verificar_token)
):
    docs = db.collection("rentalContracts").stream()
    result = []
    for doc in docs:
        d = doc.to_dict()
        m = _map(doc.id, d)
        if vehiculo_id and m["vehiculo_id"] != vehiculo_id: continue
        if empresa_id  and m["empresa_id"]  != empresa_id:  continue
        if estado      and m["estado"]       != estado:       continue
        result.append(m)
    result.sort(key=lambda x: x["fecha_inicio"] or "", reverse=True)
    return result
'''

# ── TALLERES ROUTER ───────────────────────────────────────────────────────────

TALLERES_PY = '''\
from fastapi import APIRouter, Depends, Query
from database import get_db
from auth import verificar_token
from typing import List, Optional
import schemas
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
    docs = db.collection("workshopEntries").stream()
    registros = []
    for doc in docs:
        d = doc.to_dict()
        if matricula and d.get("matricula", "") != matricula:
            continue
        registros.append(_map_entrada(doc.id, d))
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
'''

# ── CAMBIOS ROUTER ────────────────────────────────────────────────────────────

CAMBIOS_PY = '''\
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
'''

# ── TELEFONOS ROUTER ──────────────────────────────────────────────────────────

TELEFONOS_PY = '''\
from fastapi import APIRouter, Depends, Query
from database import get_db
from auth import verificar_token
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
        "area":      d.get("area", ""),
        "created_at": None,
    }

@router.get("/", response_model=List[schemas.TelefonoOut])
def get_telefonos(
    empresa: Optional[str] = Query(None),
    db = Depends(get_db)
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
    fs_data = {k: v for k, v in data.items() if k != "id"}
    db.collection("telefonos").document(doc_id).set(fs_data)
    return _map(doc_id, fs_data)
'''

# ── REGISTRO ROUTER ───────────────────────────────────────────────────────────

REGISTRO_PY = '''\
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
'''

# ── INGRESOS ROUTER ───────────────────────────────────────────────────────────

INGRESOS_PY = '''\
from fastapi import APIRouter, Depends, Query
from database import get_db
from auth import verificar_token
from typing import List, Optional
import schemas

router = APIRouter(prefix="/ingresos", tags=["ingresos"])

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
        "fecha":       d.get("fecha", ""),
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
    result.sort(key=lambda x: x["fecha"] or "", reverse=True)
    return result[skip:skip + limit]
'''

# ── ITV ROUTER ────────────────────────────────────────────────────────────────

ITV_PY = '''\
from fastapi import APIRouter, Depends, Query
from database import get_db
from auth import verificar_token
from datetime import datetime

router = APIRouter(prefix="/itv", tags=["itv"])

def parse_fecha(f: str):
    """Parsea fechas en formato YYYY-MM-DD (Firestore) o DD/MM/YYYY (legacy)."""
    if not f or not f.strip(): return None
    s = f.strip().split("T")[0].split(" ")[0]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y"):
        try: return datetime.strptime(s, fmt)
        except: pass
    return None

@router.get("/caducadas")
def get_itv_caducadas(
    db = Depends(get_db),
    _: str = Depends(verificar_token)
):
    hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    resultado = []
    for doc in db.collection("vehicles").stream():
        d = doc.to_dict()
        if d.get("estado", "").upper() == "BAJA":
            continue
        fi = parse_fecha(d.get("itv", ""))
        if fi is None or fi <= hoy:
            resultado.append({
                "matricula":           doc.id,
                "marca":               d.get("marca", ""),
                "modelo":              d.get("modelo", ""),
                "destinado_a":         d.get("destinadoA", ""),
                "conductor_actual":    d.get("conductorActual", ""),
                "conductor_actual_id": "",
                "itv":                 d.get("itv", ""),
                "dias_caducada":       (hoy - fi).days if fi else None,
            })
    resultado.sort(key=lambda x: (1 if x["dias_caducada"] is None else 0, -(x["dias_caducada"] or 0)))
    return resultado

@router.get("/proximas")
def get_itv_proximas(
    dias: int = Query(30),
    db = Depends(get_db),
    _: str = Depends(verificar_token)
):
    hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    resultado = []
    for doc in db.collection("vehicles").stream():
        d = doc.to_dict()
        if d.get("estado", "").upper() == "BAJA":
            continue
        fi = parse_fecha(d.get("itv", ""))
        if fi is None:
            continue
        dias_restantes = (fi - hoy).days
        if 0 < dias_restantes <= dias:
            resultado.append({
                "matricula":           doc.id,
                "marca":               d.get("marca", ""),
                "modelo":              d.get("modelo", ""),
                "destinado_a":         d.get("destinadoA", ""),
                "conductor_actual":    d.get("conductorActual", ""),
                "conductor_actual_id": "",
                "itv":                 d.get("itv", ""),
                "dias_restantes":      dias_restantes,
            })
    resultado.sort(key=lambda x: x["dias_restantes"])
    return resultado
'''

# ── TACOGRAFO ROUTER ──────────────────────────────────────────────────────────

TACOGRAFO_PY = '''\
from fastapi import APIRouter, Depends, Query
from database import get_db
from auth import verificar_token
from datetime import datetime

router = APIRouter(prefix="/tacografo", tags=["tacografo"])

def parse_fecha(f: str):
    """Parsea fechas en formato YYYY-MM-DD (Firestore) o DD/MM/YYYY (legacy)."""
    if not f or not f.strip(): return None
    s = f.strip().split("T")[0].split(" ")[0]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y"):
        try: return datetime.strptime(s, fmt)
        except: pass
    return None

@router.get("/caducadas")
def get_tacografo_caducadas(
    db = Depends(get_db),
    _: str = Depends(verificar_token)
):
    hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    resultado = []
    for doc in db.collection("vehicles").stream():
        d = doc.to_dict()
        if d.get("estado", "").upper() == "BAJA":
            continue
        # Excluir remolques (matrícula empieza por R)
        if (doc.id or "").upper().startswith("R"):
            continue
        fi = parse_fecha(d.get("tacografo", ""))
        if fi is None or fi <= hoy:
            resultado.append({
                "matricula":           doc.id,
                "marca":               d.get("marca", ""),
                "modelo":              d.get("modelo", ""),
                "destinado_a":         d.get("destinadoA", ""),
                "conductor_actual":    d.get("conductorActual", ""),
                "conductor_actual_id": "",
                "tacografo":           d.get("tacografo", ""),
                "dias_caducada":       (hoy - fi).days if fi else None,
            })
    resultado.sort(key=lambda x: (1 if x["dias_caducada"] is None else 0, -(x["dias_caducada"] or 0)))
    return resultado

@router.get("/proximas")
def get_tacografo_proximas(
    dias: int = Query(30),
    db = Depends(get_db),
    _: str = Depends(verificar_token)
):
    hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    resultado = []
    for doc in db.collection("vehicles").stream():
        d = doc.to_dict()
        if d.get("estado", "").upper() == "BAJA":
            continue
        if (doc.id or "").upper().startswith("R"):
            continue
        fi = parse_fecha(d.get("tacografo", ""))
        if fi is None:
            continue
        dias_restantes = (fi - hoy).days
        if 0 < dias_restantes <= dias:
            resultado.append({
                "matricula":           doc.id,
                "marca":               d.get("marca", ""),
                "modelo":              d.get("modelo", ""),
                "destinado_a":         d.get("destinadoA", ""),
                "conductor_actual":    d.get("conductorActual", ""),
                "conductor_actual_id": "",
                "tacografo":           d.get("tacografo", ""),
                "dias_restantes":      dias_restantes,
            })
    resultado.sort(key=lambda x: x["dias_restantes"])
    return resultado
'''

# ── ENTREGAS ROUTER ───────────────────────────────────────────────────────────

ENTREGAS_PY = '''\
from fastapi import APIRouter, Depends, Query
from database import get_db
from auth import verificar_token
from datetime import datetime

router = APIRouter(prefix="/entregas", tags=["entregas"])

def parse_fecha(f: str):
    if not f or not f.strip(): return None
    s = f.strip().split("T")[0].split(" ")[0]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y"):
        try: return datetime.strptime(s, fmt)
        except: pass
    return None

def _all_assignments(db) -> list:
    return [
        {
            "vehiculo_id":  doc.to_dict().get("vehicleId", ""),
            "conductor_id": doc.to_dict().get("driverId", ""),
            "conductor":    doc.to_dict().get("driverName", "—"),
            "fecha_inicio": doc.to_dict().get("fechaInicio", ""),
            "fecha_fin":    doc.to_dict().get("fechaFin", ""),
            "accion":       doc.to_dict().get("accion", ""),
        }
        for doc in db.collection("driverAssignments").stream()
    ]

@router.get("/entradas")
def get_entradas(
    mes: int = Query(None), anio: int = Query(None),
    db = Depends(get_db), _: str = Depends(verificar_token)
):
    hoy    = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    mes_c  = mes  or hoy.month
    anio_c = anio or hoy.year
    todos  = _all_assignments(db)

    filtrados = []
    for r in todos:
        fi = parse_fecha(r["fecha_inicio"])
        if not fi or fi.month != mes_c or fi.year != anio_c: continue
        ff = parse_fecha(r["fecha_fin"])
        if ff and ff <= hoy: continue
        filtrados.append(r)

    return sorted(filtrados, key=lambda x: x["fecha_inicio"] or "", reverse=True)

@router.get("/salidas")
def get_salidas(
    mes: int = Query(None), anio: int = Query(None),
    db = Depends(get_db), _: str = Depends(verificar_token)
):
    hoy    = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    mes_c  = mes  or hoy.month
    anio_c = anio or hoy.year
    todos  = _all_assignments(db)

    vehiculos_con_entrada_activa = set()
    for r in todos:
        fi = parse_fecha(r["fecha_inicio"])
        if not fi or fi.month != mes_c or fi.year != anio_c: continue
        ff = parse_fecha(r["fecha_fin"])
        if ff is None or ff > hoy:
            vehiculos_con_entrada_activa.add(r["vehiculo_id"])

    filtrados = []
    for r in todos:
        ff = parse_fecha(r["fecha_fin"])
        if not ff or ff.month != mes_c or ff.year != anio_c: continue
        if ff > hoy: continue
        if r["vehiculo_id"] in vehiculos_con_entrada_activa: continue
        filtrados.append({**r, "fecha": r["fecha_fin"]})

    return sorted(filtrados, key=lambda x: x["fecha"] or "", reverse=True)
'''

# ── DASHBOARD ROUTER ──────────────────────────────────────────────────────────

DASHBOARD_PY = '''\
from fastapi import APIRouter, Depends, Query
from database import get_db
from auth import verificar_token
from datetime import datetime, timedelta
from typing import Optional

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

def parse_fecha(f: str):
    if not f or not f.strip(): return None
    s = f.strip().split("T")[0].split(" ")[0]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y"):
        try: return datetime.strptime(s, fmt)
        except: pass
    return None

def _all_conductores(db) -> list:
    """Retorna todos los conductores de Firestore como lista de dicts."""
    result = []
    for doc in db.collection("clients").stream():
        d  = doc.to_dict()
        result.append({
            "id":             doc.id,
            "nombre":         d.get("nombre", ""),
            "apellidos":      d.get("apellidos", ""),
            "nif":            d.get("nif", ""),
            "movil":          d.get("movil", ""),
            "email":          d.get("email", ""),
            "empresa":        d.get("empresa", ""),
            "gestor":         d.get("gestor", ""),
            # fechaAlta = fecha real de incorporación
            "fecha_inicio":   d.get("fechaAlta", ""),
            # fechaIngreso = fecha prevista de incorporación (campo clave para altas)
            "fecha_prevista": d.get("fechaIngreso", ""),
            "fecha_baja":     d.get("fechaBaja", ""),
            "estado":         d.get("estado", ""),
            # situacion = DEFINITIVO / PERDIDO
            "codigo_socio":   d.get("situacion", ""),
            "num_socio":      d.get("codigo", ""),
            "vehiculo":       "",
        })
    return result

def _all_entradas_taller(db) -> list:
    return [doc.to_dict() for doc in db.collection("workshopEntries").stream()]

def contar_en_taller(db) -> int:
    hoy  = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    count = 0
    for d in _all_entradas_taller(db):
        ff = d.get("fechaFin", "")
        if not ff or not ff.strip():
            count += 1
            continue
        fd = parse_fecha(ff)
        if fd and fd >= hoy:
            count += 1
    return count

def socios_rango(conductores: list, campo: str, desde: datetime, hasta: datetime) -> list:
    result = []
    for c in conductores:
        if c.get("estado", "").lower() != "confirmado":    continue
        if c.get("codigo_socio", "").upper() != "definitivo".upper() and c.get("codigo_socio", "").upper() != "DEFINITIVO": continue
        fd = parse_fecha(c.get(campo, ""))
        if fd and desde <= fd <= hasta:
            result.append(c)
    return result

def bajas_rango(conductores: list, desde: datetime, hasta: datetime) -> list:
    result = []
    for c in conductores:
        fd = parse_fecha(c.get("fecha_baja", ""))
        if fd and desde <= fd <= hasta:
            result.append(c)
    return result

def _count_activos_hasta(conductores: list, hasta: datetime, empresa: str = "TODAS") -> int:
    n = 0
    for c in conductores:
        if empresa != "TODAS" and c.get("empresa", "").upper() != empresa.upper():
            continue
        codigo = c.get("codigo_socio", "").upper()
        if codigo not in ("DEFINITIVO", "PERDIDO"):
            continue
        if codigo == "PERDIDO" and not c.get("fecha_baja"):
            continue
        fi = parse_fecha(c.get("fecha_prevista")) or parse_fecha(c.get("fecha_inicio"))
        fb = parse_fecha(c.get("fecha_baja")) if c.get("fecha_baja") else None
        if fi and fi <= hasta:
            if fb is None or fb > hasta:
                n += 1
    return n

@router.get("/stats")
def get_stats(db = Depends(get_db), _: str = Depends(verificar_token)):
    import schemas
    hoy    = datetime.now()
    hace30 = hoy - timedelta(days=30)
    conductores = _all_conductores(db)

    confirmados = [c for c in conductores
                   if c["estado"].lower() == "confirmado"
                   and c["codigo_socio"].upper() == "DEFINITIVO"]

    total_veh = sum(1 for _ in db.collection("vehicles").stream())
    activos_v = sum(1 for doc in db.collection("vehicles").stream()
                    if doc.to_dict().get("estado", "").upper() == "ACTIVO")
    seguros_a = sum(1 for doc in db.collection("insurancePolicies").stream()
                    if doc.to_dict().get("Estado", "").upper() == "ACTIVO")

    altas = socios_rango(conductores, "fecha_prevista", hace30, hoy)
    bajas = bajas_rango(conductores, hace30, hoy)

    return {
        "total_vehiculos":     total_veh,
        "vehiculos_activos":   activos_v,
        "total_conductores":   len(confirmados),
        "conductores_activos": len(confirmados),
        "seguros_activos":     seguros_a,
        "vehiculos_en_taller": contar_en_taller(db),
        "socios_nuevos":       len(altas),
        "socios_bajas":        len(bajas),
        "transcoop":    sum(1 for c in confirmados if c["empresa"].upper() == "TRANSCOOP"),
        "ecotransporte":sum(1 for c in confirmados if c["empresa"].upper() == "ECOTRANSPORTE"),
        "centralcoop":  sum(1 for c in confirmados if c["empresa"].upper() == "CENTRALCOOP"),
    }

@router.get("/socios-altas")
def get_socios_altas(
    rango: str = Query("mes"),
    mes:  int = Query(None),
    anio: int = Query(None),
    db = Depends(get_db),
    _: str = Depends(verificar_token)
):
    hoy = datetime.now()
    if rango == "semana":
        fd, fh = hoy - timedelta(days=7), hoy
    elif rango == "mes_selector" and mes and anio:
        fd = datetime(anio, mes, 1)
        fh = datetime(anio + (1 if mes == 12 else 0), (mes % 12) + 1, 1) - timedelta(seconds=1)
    elif rango == "anio_selector" and anio:
        fd, fh = datetime(anio, 1, 1), datetime(anio, 12, 31, 23, 59, 59)
    else:
        fd, fh = hoy - timedelta(days=30), hoy
    socios = socios_rango(_all_conductores(db), "fecha_prevista", fd, fh)
    return sorted(socios, key=lambda x: x["fecha_prevista"] or "", reverse=True)

@router.get("/socios-bajas")
def get_socios_bajas(
    rango: str = Query("mes"),
    mes:  int = Query(None),
    anio: int = Query(None),
    db = Depends(get_db),
    _: str = Depends(verificar_token)
):
    hoy = datetime.now()
    if rango == "semana":
        fd, fh = hoy - timedelta(days=7), hoy
    elif rango == "mes_selector" and mes and anio:
        fd = datetime(anio, mes, 1)
        fh = datetime(anio + (1 if mes == 12 else 0), (mes % 12) + 1, 1) - timedelta(seconds=1)
    elif rango == "anio_selector" and anio:
        fd, fh = datetime(anio, 1, 1), datetime(anio, 12, 31, 23, 59, 59)
    else:
        fd, fh = hoy - timedelta(days=30), hoy
    bajas = bajas_rango(_all_conductores(db), fd, fh)
    return sorted(bajas, key=lambda x: x["fecha_baja"] or "", reverse=True)

@router.get("/evolucion-socios")
def get_evolucion_socios(
    modo: str = Query("mes"),
    anio: int = Query(None),
    cooperativa: str = Query("TODAS"),
    desde: str = Query(None),
    hasta: str = Query(None),
    db = Depends(get_db),
    _: str = Depends(verificar_token)
):
    hoy = datetime.now()
    anio_c = anio or hoy.year
    conductores = _all_conductores(db)

    def count_activos(fin: datetime) -> int:
        return _count_activos_hasta(conductores, fin, cooperativa)

    if modo == "personalizado" and desde and hasta:
        fd = parse_fecha(desde)
        fh = parse_fecha(hasta)
        if not fd or not fh or fd > fh: return []
        delta = (fh - fd).days + 1
        resultado = []
        if delta > 60:
            semana = fd
            while semana <= fh:
                fin_sem = min(semana + timedelta(days=6), fh)
                resultado.append({"label": semana.strftime("%d/%m"), "valor": count_activos(fin_sem), "periodo": semana.strftime("%d/%m/%Y")})
                semana += timedelta(days=7)
        else:
            for i in range(delta):
                dia = fd + timedelta(days=i)
                resultado.append({"label": dia.strftime("%d/%m"), "valor": count_activos(dia), "periodo": dia.strftime("%d/%m/%Y")})
        return resultado

    elif modo == "mes":
        nombres = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
        resultado = []
        for m in range(1, 13):
            inicio = datetime(anio_c, m, 1)
            if inicio > hoy: break
            fin = datetime(anio_c, m+1, 1) - timedelta(seconds=1) if m < 12 else datetime(anio_c, 12, 31, 23, 59, 59)
            resultado.append({"label": nombres[m-1], "valor": count_activos(min(fin, hoy)), "periodo": f"{m:02d}/{anio_c}"})
        return resultado

    else:  # anio
        resultado = []
        for a in range(2020, hoy.year + 1):
            if datetime(a, 1, 1) > hoy: break
            fin = datetime(a, 12, 31, 23, 59, 59)
            resultado.append({"label": str(a), "valor": count_activos(min(fin, hoy)), "periodo": str(a)})
        return resultado

@router.get("/socios-evolucion")
def get_socios_evolucion(
    modo: str = Query("dia"),
    mes:  int = Query(None),
    anio: int = Query(None),
    cooperativa: str = Query("TODAS"),
    db = Depends(get_db),
    _: str = Depends(verificar_token)
):
    hoy    = datetime.now()
    mes_c  = mes  or hoy.month
    anio_c = anio or hoy.year
    conductores = _all_conductores(db)

    def count_activos(hasta: datetime) -> int:
        return _count_activos_hasta(conductores, hasta, cooperativa)

    if modo == "anio":
        resultado = []
        for a in range(2020, hoy.year + 1):
            if datetime(a, 1, 1) > hoy: break
            hasta = datetime(a, 12, 31, 23, 59, 59)
            resultado.append({"label": str(a), "valor": count_activos(min(hasta, hoy))})
        return resultado

    elif modo == "mes":
        nombres = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
        resultado = []
        for m in range(1, 13):
            if datetime(anio_c, m, 1) > hoy: break
            h = datetime(anio_c, m+1, 1) - timedelta(seconds=1) if m < 12 else datetime(anio_c, 12, 31, 23, 59, 59)
            resultado.append({"label": nombres[m-1], "valor": count_activos(min(h, hoy))})
        return resultado

    else:  # dia
        if mes_c == 12:
            fin_mes = datetime(anio_c + 1, 1, 1) - timedelta(days=1)
        else:
            fin_mes = datetime(anio_c, mes_c + 1, 1) - timedelta(days=1)
        resultado = []
        for dia in range(1, fin_mes.day + 1):
            fd = datetime(anio_c, mes_c, dia)
            if fd > hoy: break
            resultado.append({"label": str(dia), "valor": count_activos(fd)})
        return resultado
'''

# ── LOGIN ROUTER (sin cambios) ─────────────────────────────────────────────────

LOGIN_PY = '''\
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from auth import verificar_credenciales, crear_token, verificar_horario, es_sin_horario

router = APIRouter(prefix="/auth", tags=["auth"])

class LoginRequest(BaseModel):
    usuario: str
    password: str

@router.post("/login")
def login(data: LoginRequest):
    if not verificar_credenciales(data.usuario, data.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales incorrectas")
    if not es_sin_horario(data.usuario):
        verificar_horario()
    token = crear_token(data.usuario)
    return {"access_token": token, "token_type": "bearer"}
'''

# ── SYNC_SHEETS.PY (Firestore version) ───────────────────────────────────────

SYNC_SHEETS_PY = '''\
"""
sync_sheets.py  –  Sincroniza Google Sheets → Firebase Firestore
Ejecutar con: python sync_sheets.py
Sustituye al antiguo sync_sheets.py que escribía en PostgreSQL.
"""
import csv, io, sys, urllib.request, uuid
from datetime import datetime
from pathlib import Path

# Forzar UTF-8 en stdout
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from google.cloud import firestore
from google.oauth2.service_account import Credentials

_BASE  = Path(__file__).parent
_SA    = _BASE / "ai-studio-applet-webapp-55a1a-firebase-adminsdk-fbsvc-67d511e6d4.json"
_creds = Credentials.from_service_account_file(str(_SA))
db     = firestore.Client(
    project     = "ai-studio-applet-webapp-55a1a",
    credentials = _creds,
    database    = "ai-studio-7801edee-96c4-47bb-8194-68abcf65e834",
)

# ─── URLs Google Sheets ───────────────────────────────────────────────────────
_DC  = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSryhAruJS1FpMgGVHUe6qnYfbIt3_qUWy10s3a5-vVReJpmZB5SIo_drLziXVf8PjCQyyJ1EPMjVfR/pub?single=true&output=csv"
_SEG = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTLyHazuC46Ld7iKm7ehu6gwVpMuT_E1wkE6KWQv_6nRaAB5KS19bnFeRKBo2ycVcP5_TU9cOz-KLXq/pub?single=true&output=csv"
_FIN = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRubGv6OUV1t1zs6Uo8ACs3xQhF_4vZLuJTNO3pLacR2iejX6oNQc6orPFMhAP2kf4kumCn_ael6qGU/pub?single=true&output=csv"

URL_VEHICULOS    = f"{_DC}&gid=972014913"
URL_CLIENTES     = f"{_DC}&gid=1341381949"
URL_HISTORIAL    = f"{_DC}&gid=1746464690"
URL_SEGUROS      = f"{_SEG}&gid=702011553"
URL_ASEGURADORAS = f"{_SEG}&gid=1750903629"
URL_FINANCIERAS  = f"{_FIN}&gid=0"
URL_CONTRATOS    = f"{_FIN}&gid=28649955"

EMPRESAS_VALIDAS = {"ECOTRANSPORTE", "TRANSCOOP", "CENTRALCOOP"}
BATCH_SIZE       = 400  # Firestore: máx 500 ops por batch

# ─── Utilidades ───────────────────────────────────────────────────────────────

def fetch_csv(url: str) -> list:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        content = r.read().decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(content)))

def clean(val) -> str:
    return val.strip() if val else ""

def clean_float(val):
    v = clean(val).replace(".", "").replace(",", ".").replace("€", "").replace(" ", "")
    try: return float(v) if v else None
    except: return None

def clean_int(val):
    v = clean(val)
    try: return int(v) if v else None
    except: return None

def normalize_date(val: str) -> str:
    """Convierte cualquier formato de fecha a YYYY-MM-DD."""
    if not val or not val.strip(): return ""
    s = val.strip()
    if "T" in s: s = s.split("T")[0]
    parts = s.replace("-", "/").split("/")
    if len(parts) == 3:
        if len(parts[0]) == 4:   # YYYY-MM-DD
            return f"{parts[0]}-{parts[1].zfill(2)}-{parts[2].zfill(2)}"
        else:                     # DD/MM/YYYY
            y = parts[2]
            if len(y) == 2: y = ("19" + y) if int(y) > 30 else ("20" + y)
            return f"{y}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
    return s

def normalize_mat(m: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFD", m or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return "".join(c for c in s.upper() if c.isalnum())

def upsert_batch(collection: str, docs: list):
    """Escribe docs en Firestore en batches. Cada doc debe tener \'_id\'."""
    total = 0
    for i in range(0, len(docs), BATCH_SIZE):
        batch = db.batch()
        for doc in docs[i:i + BATCH_SIZE]:
            doc_id = doc.pop("_id", "")
            if not doc_id: continue
            batch.set(db.collection(collection).document(doc_id), doc, merge=True)
            total += 1
        batch.commit()
    return total

# ─── Funciones de sincronización ──────────────────────────────────────────────

def sync_vehiculos(rows: list):
    print(f"  Vehículos: {len(rows)} filas")
    docs = []
    for row in rows:
        mat = normalize_mat(clean(row.get("Matrícula", "")))
        if not mat: continue
        docs.append({
            "_id":                mat,
            "matricula":          mat,
            "marca":              clean(row.get("Marca", "")),
            "modelo":             clean(row.get("Modelo", "")),
            "bastidor":           clean(row.get("Bastidor", "")),
            "fechaMat":           normalize_date(clean(row.get("FechaMat.", ""))),
            "destinadoA":         clean(row.get("Destinado a", "")),
            "propiedad":          clean(row.get("Propiedad", "")),
            "situacion":          clean(row.get("Situación", "")),
            "estado":             clean(row.get("Estado", "ACTIVO")) or "ACTIVO",
            "fechaIncorporacion": normalize_date(clean(row.get("Fecha Incorporación", "") or row.get("FechaIncorporación", ""))),
            "itv":                normalize_date(clean(row.get("ITV", ""))),
            "tacografo":          normalize_date(clean(row.get("Tacógrafo", "") or row.get("Tacografo", ""))),
            "mantenimiento":      clean(row.get("Mantenimiento", "")).upper() in ("SI", "S", "1", "TRUE", "YES"),
            "fechaFinMto":        normalize_date(clean(row.get("FechaFinMto", ""))),
            "kmFinMto":           clean_float(row.get("KmFinMto", "")) or 0,
            "precioMto":          clean_float(row.get("PrecioMto", "")) or 0,
            "garantia":           clean(row.get("Garantia", "")).upper() in ("SI", "S", "1", "TRUE", "YES"),
            "fechaFinGarantia":   normalize_date(clean(row.get("FechaFinGarantia", ""))),
            "kmFinGarantia":      clean_float(row.get("KmFinGarantia", "")) or 0,
            "kilometros":         clean_float(row.get("Kilómetros", "")) or 0,
            "equipamiento":       clean(row.get("Equipamiento", "")),
            "observaciones":      clean(row.get("Observaciones", "")),
        })
    n = upsert_batch("vehicles", docs)
    print(f"  ✓ {n} vehículos actualizados en Firestore")

def sync_clientes(rows_clientes: list, rows_historial: list):
    print(f"  Clientes: {len(rows_clientes)} filas")

    # Mapa de historial: conductor_id → lista de asignaciones
    hist_map: dict = {}
    for row in rows_historial:
        cid = clean(row.get("ConductorID", ""))
        if not cid: continue
        hist_map.setdefault(cid, []).append({
            "vehiculo_id":  clean(row.get("VehículoID", "") or row.get("VehiculoID", "")),
            "fecha_inicio": clean(row.get("FechaInicio", "")),
            "fecha_fin":    clean(row.get("FechaFin", "")),
        })

    def parse_fecha(f: str):
        if not f: return None
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
            try: return datetime.strptime(f.strip(), fmt)
            except: pass
        return None

    docs = []
    omitidos = 0
    ids_validos = set()

    for row in rows_clientes:
        id_c = clean(row.get("ID", ""))
        if not id_c: continue

        estado_raw = clean(row.get("Estado", "")).lower()
        situacion  = clean(row.get("Situación", "")).lower()
        empresa    = clean(row.get("Empresa", "")).upper()

        if estado_raw not in ("confirmado", "ex-socio", "ex socio", "exsocio") \\
           and situacion not in ("definitivo", "perdido", "baja"):
            omitidos += 1
            continue
        if empresa not in EMPRESAS_VALIDAS:
            omitidos += 1
            continue

        ids_validos.add(id_c)

        if estado_raw == "confirmado" and situacion == "definitivo":
            estado_final = "Confirmado"
        elif estado_raw in ("ex-socio", "ex socio", "exsocio") or situacion in ("perdido", "baja"):
            estado_final = "Ex-socio"
        else:
            estado_final = clean(row.get("Estado", "")) or "Confirmado"

        fecha_baja = clean(row.get("FECHA BAJA", ""))
        if fecha_baja:
            fb_dt = parse_fecha(fecha_baja)
            if fb_dt:
                for r in hist_map.get(id_c, []):
                    fi = parse_fecha(r["fecha_inicio"])
                    if fi and fi > fb_dt:
                        fecha_baja = ""
                        break

        docs.append({
            "_id":             id_c,
            "nombre":          clean(row.get("Nombre", "")),
            "nombrePropio":    clean(row.get("NOMBRE PROPIO", "")),
            "apellidos":       clean(row.get("APELLIDOS", "")),
            "nif":             clean(row.get("NIF", "")) or id_c,
            "numTarjConductor":clean(row.get("NUM_TARJ_CONDUCTOR", "")),
            "movil":           clean(row.get("Móvil", "")),
            "email":           clean(row.get("Email", "")),
            "empresa":         clean(row.get("Empresa", "")),
            "gestor":          clean(row.get("GESTOR", "") or row.get("Comercial", "")),
            "estado":          estado_final,
            "fechaAlta":       normalize_date(clean(row.get("Fecha Alta", ""))),
            "fechaIngreso":    normalize_date(clean(row.get("Fecha prevista", ""))),
            "fechaBaja":       normalize_date(fecha_baja),
            "fechaNacimiento": normalize_date(clean(row.get("FECHA NACIMIENTO", ""))),
            "codigo":          clean(row.get("CODIGO", "")),
            "situacion":       clean(row.get("Situación", "")),
            "direccion":       clean(row.get("DIRECCION", "")),
            "poblacion":       clean(row.get("POBLACION", "")),
            "codigoP":         clean(row.get("CODIGO P.", "")),
            "provincia":       clean(row.get("PROVINCIA", "")),
        })

    n = upsert_batch("clients", docs)
    print(f"  ✓ {n} clientes actualizados, {omitidos} omitidos")

def sync_historial(rows: list):
    """Sincroniza driverAssignments y actualiza conductorActual en vehicles."""
    print(f"  HistorialVehiculo: {len(rows)} filas")
    docs = []
    vehiculo_map: dict = {}  # vehiculo_id → lista de asignaciones

    for row in rows:
        id_hist     = clean(row.get("ID", ""))
        vehiculo_id = normalize_mat(clean(row.get("VehículoID", "") or row.get("VehiculoID", "")))
        conductor_id= clean(row.get("ConductorID", ""))
        if not vehiculo_id or not id_hist: continue

        fecha_fin = clean(row.get("FechaFin", ""))
        docs.append({
            "_id":         id_hist,
            "vehicleId":   vehiculo_id,
            "driverId":    conductor_id,
            "driverName":  conductor_id,
            "fechaInicio": normalize_date(clean(row.get("FechaInicio", ""))),
            "fechaFin":    normalize_date(fecha_fin),
            "accion":      clean(row.get("Acción", "") or row.get("Accion", "")),
            "observaciones": clean(row.get("Observaciones", "")),
        })
        vehiculo_map.setdefault(vehiculo_id, []).append({
            "conductor_id": conductor_id,
            "fecha_fin":    fecha_fin,
            "fecha_inicio": clean(row.get("FechaInicio", "")),
        })

    n = upsert_batch("driverAssignments", docs)
    print(f"  ✓ {n} asignaciones actualizadas")

    # Actualizar conductorActual en vehicles basado en el historial
    actualizados = 0
    for mat, registros in vehiculo_map.items():
        activo = next((r for r in registros if not r["fecha_fin"] and r["conductor_id"]), None)
        if activo:
            conductor_nombre = activo["conductor_id"]
        else:
            con_fecha = [r for r in registros if r["fecha_fin"] and r["conductor_id"]]
            if not con_fecha: continue
            ultimo = sorted(con_fecha, key=lambda x: x["fecha_fin"], reverse=True)[0]
            conductor_nombre = ultimo["conductor_id"]
        try:
            db.collection("vehicles").document(mat).update({"conductorActual": conductor_nombre})
            actualizados += 1
        except Exception:
            pass
    print(f"  ✓ conductorActual actualizado en {actualizados} vehículos")

def sync_seguros(rows_seguros: list, rows_aseguradoras: list):
    print(f"  Seguros: {len(rows_seguros)} filas")
    aseg_map = {
        clean(r.get("ID_Aseguradora", "")): clean(r.get("Aseguradora", ""))
        for r in rows_aseguradoras
        if clean(r.get("ID_Aseguradora", ""))
    }
    docs = []
    omitidos = 0
    for row in rows_seguros:
        estado = clean(row.get("Estado", "")).upper()
        if estado != "ACTIVO":
            omitidos += 1
            continue
        doc_id = clean(row.get("ID", "")) or clean(row.get("Nº de Póliza", ""))
        if not doc_id: continue
        aseg_id = clean(row.get("Aseguradora_ID", ""))
        doc_data = dict(row)  # guardar campos en español tal cual vienen del sheet
        doc_data["_id"]        = doc_id
        doc_data["Aseguradora"] = aseg_map.get(aseg_id, aseg_id)
        docs.append(doc_data)
    n = upsert_batch("insurancePolicies", docs)
    print(f"  ✓ {n} seguros actualizados, {omitidos} omitidos")

def sync_financieras(rows: list):
    print(f"  Financieras: {len(rows)} filas")
    docs = []
    for row in rows:
        doc_id = clean(row.get("FinAcuerdoID", ""))
        if not doc_id: continue
        doc_data = dict(row)
        doc_data["_id"] = doc_id
        docs.append(doc_data)
    n = upsert_batch("financialAgreements", docs)
    print(f"  ✓ {n} financieras actualizadas")

def sync_contratos(rows: list):
    print(f"  Contratos: {len(rows)} filas")
    docs = []
    for row in rows:
        doc_id = clean(row.get("AlqContratoID", ""))
        if not doc_id: continue
        doc_data = dict(row)
        doc_data["_id"] = doc_id
        docs.append(doc_data)
    n = upsert_batch("rentalContracts", docs)
    print(f"  ✓ {n} contratos actualizados")

# ─── Main ─────────────────────────────────────────────────────────────────────

def sync_all():
    sep = "=" * 52
    print(f"\\n{sep}")
    print(f"  Sync Firestore: {datetime.now().strftime(\'%d/%m/%Y %H:%M:%S\')}")
    print(f"{sep}")

    print("\\n[0/6] Descargando historial y clientes...")
    rows_historial = fetch_csv(URL_HISTORIAL)
    rows_clientes  = fetch_csv(URL_CLIENTES)

    print("\\n[1/6] Vehículos...")
    sync_vehiculos(fetch_csv(URL_VEHICULOS))

    print("\\n[2/6] Clientes...")
    sync_clientes(rows_clientes, rows_historial)

    print("\\n[3/6] Seguros...")
    sync_seguros(fetch_csv(URL_SEGUROS), fetch_csv(URL_ASEGURADORAS))

    print("\\n[4/6] Financieras...")
    sync_financieras(fetch_csv(URL_FINANCIERAS))

    print("\\n[5/6] Contratos...")
    sync_contratos(fetch_csv(URL_CONTRATOS))

    print("\\n[6/6] Historial / driverAssignments...")
    sync_historial(rows_historial)

    print(f"\\n✓ Completado: {datetime.now().strftime(\'%d/%m/%Y %H:%M:%S\')}\\n")

if __name__ == "__main__":
    sync_all()
'''

# ── DEPLOY SCRIPT ─────────────────────────────────────────────────────────────

DEPLOY_SH = '''\
#!/bin/bash
# deploy_vps.sh — Instala el backend migrado a Firestore en el VPS
# Ejecutar desde la carpeta datacenter-backend/:
#   bash firebase_migration/deploy_vps.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== Deploy: PostgreSQL → Firestore ==="
echo "Backend dir: $BACKEND_DIR"

cd "$BACKEND_DIR"

# 1. Instalar dependencias nuevas
echo "[1/4] Instalando dependencias..."
source venv/bin/activate 2>/dev/null || true
pip install --quiet google-cloud-firestore google-auth

# 2. Copiar nuevos archivos (los originales ya están en backup_postgres/)
echo "[2/4] Copiando archivos migrados..."
cp firebase_migration/database.py       database.py
cp firebase_migration/sync_sheets.py    sync_sheets.py
cp firebase_migration/requirements.txt  requirements.txt
cp firebase_migration/routers/vehiculos.py  routers/vehiculos.py
cp firebase_migration/routers/conductores.py routers/conductores.py
cp firebase_migration/routers/seguros.py    routers/seguros.py
cp firebase_migration/routers/financieras.py routers/financieras.py
cp firebase_migration/routers/contratos.py  routers/contratos.py
cp firebase_migration/routers/talleres.py   routers/talleres.py
cp firebase_migration/routers/cambios.py    routers/cambios.py
cp firebase_migration/routers/telefonos.py  routers/telefonos.py
cp firebase_migration/routers/registro.py   routers/registro.py
cp firebase_migration/routers/ingresos.py   routers/ingresos.py
cp firebase_migration/routers/dashboard.py  routers/dashboard.py
cp firebase_migration/routers/entregas.py   routers/entregas.py
cp firebase_migration/routers/itv.py        routers/itv.py
cp firebase_migration/routers/tacografo.py  routers/tacografo.py

# 3. Verificar que Firestore responde
echo "[3/4] Verificando conexión Firestore..."
python - <<\'PYEOF\'
from database import db
docs = list(db.collection("vehicles").limit(1).stream())
print(f"  OK — colección vehicles accesible ({len(docs)} doc de prueba)")
PYEOF

# 4. Reiniciar la API
echo "[4/4] Reiniciando pm2..."
pm2 restart datacenter-api

echo ""
echo "=== Listo ==="
echo "Para hacer el primer sync completo ejecuta:"
echo "  python sync_sheets.py"
'''

# ── INSTRUCCIONES ─────────────────────────────────────────────────────────────

INSTRUCCIONES_MD = '''\
# Migración: PostgreSQL → Firebase Firestore

## Colecciones Firestore necesarias

| Colección Firestore     | Tabla PostgreSQL antigua  | Notas                                  |
|------------------------|--------------------------|----------------------------------------|
| `vehicles`             | `vehiculos`              | Doc ID = matrícula. Fechas YYYY-MM-DD |
| `clients`              | `conductores`            | Doc ID = ID del cliente                |
| `workshops`            | `talleres_lista`         |                                        |
| `workshopEntries`      | `talleres_entradas`      |                                        |
| `driverAssignments`    | `historial_vehiculo`     |                                        |
| `insurancePolicies`    | `seguros`                | Campos en español (del sheet)          |
| `financialAgreements`  | `financieras`            | Campos en español (del sheet)          |
| `rentalContracts`      | `contratos`              | Campos en español (del sheet)          |
| `telefonos`            | `telefonos`              | **NUEVA — crear en Firestore**         |
| `registroEmpresas`     | `registro_empresas`      | **NUEVA — crear en Firestore**         |
| `ingresos`             | `ingresos`               | **NUEVA — crear en Firestore**         |
| `cambiosVehiculos`     | `cambios_vehiculos`      | **NUEVA — crear en Firestore**         |

## Colecciones nuevas — campos a crear en Firestore

### `telefonos`
- `telefono` (string)
- `extension` (string)
- `persona` (string)
- `empresa` (string)
- `email` (string)
- `area` (string)

### `registroEmpresas`
- `matricula` (string)
- `tipoVehiculo` (string)
- `fechaMat` (string YYYY-MM-DD)
- `autorizacion` (string)
- `fechaAdscripcion` (string YYYY-MM-DD)
- `empresa` (string)
- `flota` (string)
- `propiedad` (string)
- `conductor` (string)
- `fechaInicio` (string YYYY-MM-DD)
- `tipoContrato` (string)
- `arrendatario` (string)
- `cuotaSocio` (number)
- `financiera` (string)
- `tipoFinan` (string)
- `cuotaFinan` (number)

### `ingresos`
- `nombreMes` (string)
- `proveedor` (string)
- `nif` (string)
- `codigo` (string)
- `familia` (string)
- `numFactura` (number)
- `refFactura` (string)
- `fecha` (string YYYY-MM-DD)
- `cooperativa` (string)

### `cambiosVehiculos`
- `fechaInicio` (string YYYY-MM-DD)
- `matriculaEntra` (string)
- `conductorEntra` (string)
- `fechaFin` (string YYYY-MM-DD)
- `matriculaSale` (string)
- `conductorSale` (string)

## Pasos para desplegar

1. **Generar archivos** (en local):
   ```
   python migrate_to_firestore.py
   ```

2. **Subir carpeta** `firebase_migration/` al VPS:
   ```
   scp -r firebase_migration/ usuario@vps:/ruta/datacenter-backend/
   ```

3. **Ejecutar deploy** en el VPS:
   ```
   bash firebase_migration/deploy_vps.sh
   ```

4. **Verificar** que la API responde correctamente.

5. **Primer sync** para que los datos queden actualizados:
   ```
   python sync_sheets.py
   ```

## Rollback

Si hay problemas, los archivos originales están en `backup_postgres/`:
```bash
cp backup_postgres/database.py database.py
cp backup_postgres/sync_sheets.py sync_sheets.py
cp backup_postgres/requirements.txt requirements.txt
cp -r backup_postgres/routers/* routers/
pip install -r requirements.txt
pm2 restart datacenter-api
```
'''

# ─────────────────────────────────────────────────────────────────────────────
#  MAIN — genera todos los archivos
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print(f"\n{'='*52}")
    print(f"  migrate_to_firestore.py")
    print(f"  Generando archivos en: firebase_migration/")
    print(f"{'='*52}\n")

    OUT_DIR.mkdir(exist_ok=True)

    print("[1/3] Haciendo backup de archivos originales...")
    backup_original()

    print("\n[2/3] Generando nuevos archivos Firestore...")
    write_file("database.py",                 DATABASE_PY)
    write_file("requirements.txt",            REQUIREMENTS_TXT)
    write_file("sync_sheets.py",              SYNC_SHEETS_PY)
    write_file("routers/vehiculos.py",        VEHICULOS_PY)
    write_file("routers/conductores.py",      CONDUCTORES_PY)
    write_file("routers/seguros.py",          SEGUROS_PY)
    write_file("routers/financieras.py",      FINANCIERAS_PY)
    write_file("routers/contratos.py",        CONTRATOS_PY)
    write_file("routers/talleres.py",         TALLERES_PY)
    write_file("routers/cambios.py",          CAMBIOS_PY)
    write_file("routers/telefonos.py",        TELEFONOS_PY)
    write_file("routers/registro.py",         REGISTRO_PY)
    write_file("routers/ingresos.py",         INGRESOS_PY)
    write_file("routers/dashboard.py",        DASHBOARD_PY)
    write_file("routers/entregas.py",         ENTREGAS_PY)
    write_file("routers/itv.py",              ITV_PY)
    write_file("routers/tacografo.py",        TACOGRAFO_PY)
    write_file("routers/login.py",            LOGIN_PY)

    print("\n[3/3] Generando scripts de deploy...")
    write_file("deploy_vps.sh",               DEPLOY_SH)
    write_file("INSTRUCCIONES.md",            INSTRUCCIONES_MD)

    print(f"\n{'='*52}")
    print(f"  ✅ Generación completada.")
    print(f"  Carpeta: {OUT_DIR}")
    print(f"  Archivos originales en: backup_postgres/")
    print(f"\n  Próximos pasos:")
    print(f"  1. Revisar firebase_migration/")
    print(f"  2. Subir al VPS")
    print(f"  3. bash firebase_migration/deploy_vps.sh")
    print(f"{'='*52}\n")

if __name__ == "__main__":
    main()
