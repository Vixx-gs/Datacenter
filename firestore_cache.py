"""
firestore_cache.py — Caché Firestore persistente en disco + background refresh.

Estrategia:
  1. Al arrancar: carga desde JSON en disco si tiene < 10 min → 0 lecturas Firestore
  2. Si el disco está obsoleto: lee de Firestore una vez y guarda en disco
  3. Thread background: refresca Firestore cada 5 min y actualiza disco
  → Resultado: 0 lecturas Firestore por request, solo 1 refresh cada 5 min
"""
import threading, time, json
from pathlib import Path

from database import db as _db   # singleton Firestore — no circular porque database.py no importa esto

REFRESH  = 300   # refrescar cada 5 min
DISK_TTL = 600   # usar disco si tiene menos de 10 min de antigüedad

_CACHE_DIR = Path(__file__).parent / "cache"
_CACHE_DIR.mkdir(exist_ok=True)

_COLS = {
    "clients":           "clients",
    "vehicles":          "vehicles",
    "workshopEntries":   "workshopEntries",
    "driverAssignments": "driverAssignments",
}

_lock  = threading.Lock()
_store: dict = {}   # key → {"data": list[tuple(id, dict)], "ts": float}


# ── disco ──────────────────────────────────────────────────────

def _disk_file(key: str) -> Path:
    return _CACHE_DIR / f"{key}.json"


def _load_disk(key: str):
    f = _disk_file(key)
    if not f.exists():
        return None
    if time.time() - f.stat().st_mtime > DISK_TTL:
        return None
    try:
        raw = json.loads(f.read_text(encoding="utf-8"))
        return [(r["id"], r["data"]) for r in raw]
    except Exception:
        return None


def _save_disk(key: str, data: list):
    try:
        payload = [{"id": doc_id, "data": d} for doc_id, d in data]
        tmp = _disk_file(key).with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        tmp.replace(_disk_file(key))
    except Exception as e:
        print(f"[cache] Error disco {key}: {e}")


# ── Firestore ──────────────────────────────────────────────────

def _fetch(key: str) -> list:
    docs = list(_db.collection(_COLS[key]).stream())
    return [(doc.id, doc.to_dict()) for doc in docs]


def _refresh(key: str):
    try:
        t0   = time.time()
        data = _fetch(key)
        with _lock:
            _store[key] = {"data": data, "ts": time.time()}
        _save_disk(key, data)
        print(f"[cache] {key}: {len(data)} docs en {time.time()-t0:.1f}s")
    except Exception as e:
        print(f"[cache] Error refrescando {key}: {e}")


# ── background thread ──────────────────────────────────────────

def _background():
    while True:
        time.sleep(REFRESH)
        for key in _COLS:
            _refresh(key)


# ── inicialización al importar ─────────────────────────────────

def _init():
    needs_fs = []
    for key in _COLS:
        data = _load_disk(key)
        if data is not None:
            with _lock:
                _store[key] = {"data": data, "ts": time.time()}
            print(f"[cache] {key}: disco ({len(data)} docs)")
        else:
            needs_fs.append(key)

    for key in needs_fs:
        _refresh(key)

    threading.Thread(target=_background, daemon=True).start()
    print(f"[cache] Listo — refresh cada {REFRESH}s")


# ── API pública ────────────────────────────────────────────────

def _get(key: str) -> list:
    with _lock:
        entry = _store.get(key)
    if entry:
        return entry["data"]
    _refresh(key)
    with _lock:
        return _store.get(key, {}).get("data", [])


def get_clients()            -> list: return _get("clients")
def get_vehicles()           -> list: return _get("vehicles")
def get_workshop_entries()   -> list: return _get("workshopEntries")
def get_driver_assignments() -> list: return _get("driverAssignments")


def invalidate(key: str = None):
    """Fuerza recarga en el próximo acceso."""
    with _lock:
        if key:
            _store.pop(key, None)
        else:
            _store.clear()


_init()
