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
