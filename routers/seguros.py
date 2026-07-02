from fastapi import APIRouter, Query
from typing import List, Optional
from datetime import datetime
import schemas
import sheets_cache as sc

router = APIRouter(prefix="/seguros", tags=["seguros"])


@router.get("/", response_model=List[schemas.SeguroOut])
def get_seguros(
    matricula: Optional[str] = Query(None),
    estado:    Optional[str] = Query(None),
    tomador:   Optional[str] = Query(None),
):
    """
    Lee los seguros directamente de Google Sheets (caché 5 min).
    Solo devuelve seguros ACTIVO con vencimiento futuro.
    """
    rows              = sc.get_seguros()
    aseguradoras_map  = sc.build_aseguradoras_map()
    hoy               = datetime.now()
    result            = []

    for row in rows:
        estado_row = sc.clean(row.get("Estado", "")).upper()
        if estado_row != "ACTIVO":
            continue

        fecha_venc_str = sc.clean(row.get("Fecha de Vencimiento", ""))
        fecha_venc     = sc.parse_fecha(fecha_venc_str)
        if fecha_venc and fecha_venc < hoy:
            continue

        id_seg = sc.clean(row.get("ID", "")) or sc.clean(row.get("Nº de Póliza", ""))
        if not id_seg:
            continue

        aseguradora_id     = sc.clean(row.get("Aseguradora_ID", ""))
        aseguradora_nombre = aseguradoras_map.get(aseguradora_id, aseguradora_id)

        m = {
            "id":            id_seg,
            "poliza":        sc.clean(row.get("Nº de Póliza", "")),
            "matricula":     sc.clean(row.get("Matrícula", "")),
            "tomador":       sc.clean(row.get("Tomador", "")),
            "tipo":          sc.clean(row.get("Tipo de Seguro", "")),
            "aseguradora":   aseguradora_nombre,
            "corredor":      sc.clean(row.get("Corredor", "")),
            "vencimiento":   fecha_venc_str,
            "ambito":        sc.clean(row.get("Ámbito", "")),
            "garantias":     sc.clean(row.get("Garantías", "")),
            "estado":        estado_row,
            "observaciones": sc.clean(row.get("Observaciones", "")),
            "created_at":    None,
        }

        if matricula and m["matricula"] != matricula:
            continue
        if tomador and m["tomador"] != tomador:
            continue

        result.append(m)

    result.sort(key=lambda x: x["vencimiento"] or "")
    return result
