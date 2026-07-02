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
