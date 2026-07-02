"""
sheets_cache.py — Caché en memoria para datos de Google Sheets.
TTL configurable (por defecto 5 minutos).
Hilo-seguro con threading.Lock.

Uso:
    import sheets_cache as sc
    rows = sc.get_seguros()
"""

import csv
import io
import time
import threading
import urllib.request
from datetime import datetime

# ── URLs de los spreadsheets ────────────────────────────────────────────────
BASE_DATACENTER  = (
    "https://docs.google.com/spreadsheets/d/e/"
    "2PACX-1vSryhAruJS1FpMgGVHUe6qnYfbIt3_qUWy10s3a5-vVReJpmZB5SIo_drLziXVf8PjCQyyJ1EPMjVfR"
    "/pub?single=true&output=csv"
)
BASE_SEGUROS = (
    "https://docs.google.com/spreadsheets/d/e/"
    "2PACX-1vTLyHazuC46Ld7iKm7ehu6gwVpMuT_E1wkE6KWQv_6nRaAB5KS19bnFeRKBo2ycVcP5_TU9cOz-KLXq"
    "/pub?single=true&output=csv"
)
BASE_FINANCIERAS = (
    "https://docs.google.com/spreadsheets/d/e/"
    "2PACX-1vRubGv6OUV1t1zs6Uo8ACs3xQhF_4vZLuJTNO3pLacR2iejX6oNQc6orPFMhAP2kf4kumCn_ael6qGU"
    "/pub?single=true&output=csv"
)

URL_SEGUROS      = f"{BASE_SEGUROS}&gid=702011553"
URL_ASEGURADORAS = f"{BASE_SEGUROS}&gid=1750903629"
URL_FINANCIERAS  = f"{BASE_FINANCIERAS}&gid=0"
URL_CONTRATOS    = f"{BASE_FINANCIERAS}&gid=28649955"
URL_HISTORIAL    = f"{BASE_DATACENTER}&gid=1746464690"

# ── Caché ────────────────────────────────────────────────────────────────────
TTL   = 300        # segundos (5 min)
_lock  = threading.Lock()
_store: dict = {}  # { key: {"data": list, "ts": float} }


def _fetch_csv(url: str) -> list:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        content = r.read().decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(content)))


def _get(key: str, url: str) -> list:
    """Devuelve datos en caché o los descarga si han expirado."""
    with _lock:
        entry = _store.get(key)
        if entry and (time.time() - entry["ts"]) < TTL:
            return entry["data"]
    # Descarga fuera del lock para no bloquear otros hilos
    data = _fetch_csv(url)
    with _lock:
        _store[key] = {"data": data, "ts": time.time()}
    return data


def invalidate(key: str | None = None):
    """Invalida una entrada (o toda la caché si key=None)."""
    with _lock:
        if key:
            _store.pop(key, None)
        else:
            _store.clear()


# ── Accesores públicos ────────────────────────────────────────────────────────
def get_seguros()      -> list: return _get("seguros",      URL_SEGUROS)
def get_aseguradoras() -> list: return _get("aseguradoras", URL_ASEGURADORAS)
def get_financieras()  -> list: return _get("financieras",  URL_FINANCIERAS)
def get_contratos()    -> list: return _get("contratos",    URL_CONTRATOS)
def get_historial()    -> list: return _get("historial",    URL_HISTORIAL)


# ── Helpers de limpieza (reutilizados en routers) ────────────────────────────
def clean(val) -> str:
    return val.strip() if val else ""


def clean_float(val):
    v = clean(str(val or "")).replace(".", "").replace(",", ".").replace("€", "").replace(" ", "")
    try:
        return float(v) if v else None
    except Exception:
        return None


def clean_int(val):
    v = clean(str(val or ""))
    try:
        return int(v) if v else None
    except Exception:
        return None


def parse_fecha(fecha_str: str):
    if not fecha_str:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(fecha_str.strip(), fmt)
        except Exception:
            pass
    return None


def build_aseguradoras_map() -> dict:
    """Devuelve {ID_Aseguradora: nombre} para resolución de nombres."""
    return {
        clean(r.get("ID_Aseguradora", "")): clean(r.get("Aseguradora", ""))
        for r in get_aseguradoras()
        if r.get("ID_Aseguradora")
    }
