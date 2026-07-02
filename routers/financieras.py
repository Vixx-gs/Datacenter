from fastapi import APIRouter, Query
from typing import List, Optional
import schemas
import sheets_cache as sc

router = APIRouter(prefix="/financieras", tags=["financieras"])


@router.get("/", response_model=List[schemas.FinancieraOut])
def get_financieras(
    vehiculo_id: Optional[str] = Query(None),
    empresa_id:  Optional[str] = Query(None),
    tipo:        Optional[str] = Query(None),
):
    """
    Lee las financieras directamente de Google Sheets (caché 5 min).
    """
    rows   = sc.get_financieras()
    result = []

    for row in rows:
        id_fin = sc.clean(row.get("FinAcuerdoID", ""))
        if not id_fin:
            continue

        m = {
            "id":                 id_fin,
            "num_contrato":       sc.clean(row.get("NumContrato", "")),
            "vehiculo_id":        sc.clean(row.get("VehiculoID", "")),
            "empresa_id":         sc.clean(row.get("EmpresaID", "")),
            "tipo":               sc.clean(row.get("Tipo", "")),
            "fecha_inicio":       sc.clean(row.get("FechaInicio", "")),
            "fecha_fin":          sc.clean(row.get("FechaFin", "")),
            "cuota_mensual":      sc.clean_float(row.get("CuotaMensual", "")),
            "num_cuotas":         sc.clean_int(row.get("NumCuotas", "")),
            "dia_pago":           sc.clean_int(row.get("DiaPago", "")),
            "importe_financiado": sc.clean_float(row.get("ImporteFinanciado", "")),
            "valor_residual":     sc.clean_float(row.get("ValorResidual", "")),
            "financiera":         sc.clean(row.get("Financiera", "")),
            "gastos_iniciales":   sc.clean_float(row.get("GastosIniciales", "")),
            "fianzas":            sc.clean_float(row.get("Fianzas", "")),
            "entrada":            sc.clean_float(row.get("Entrada", "")),
            "observaciones":      sc.clean(
                row.get("Co", "") or row.get("Comentarios", "") or row.get("Observaciones", "")
            ),
            "created_at":         None,
        }

        if vehiculo_id and m["vehiculo_id"] != vehiculo_id:
            continue
        if empresa_id  and m["empresa_id"]  != empresa_id:
            continue
        if tipo        and m["tipo"]         != tipo:
            continue

        result.append(m)

    result.sort(key=lambda x: x["fecha_inicio"] or "")
    return result
