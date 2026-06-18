from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class VehiculoBase(BaseModel):
    matricula: str
    marca: Optional[str] = None
    modelo: Optional[str] = None
    bastidor: Optional[str] = None
    fecha_mat: Optional[str] = None
    destinado_a: Optional[str] = None
    propiedad: Optional[str] = None
    situacion: Optional[str] = None
    estado: Optional[str] = "ACTIVO"
    fecha_incorporacion: Optional[str] = None
    itv: Optional[str] = None
    tacografo: Optional[str] = None
    mantenimiento: Optional[str] = None
    fecha_fin_mto: Optional[str] = None
    km_fin_mto: Optional[str] = None
    precio_mto: Optional[str] = None
    garantia: Optional[str] = None
    fecha_fin_garantia: Optional[str] = None
    km_fin_garantia: Optional[str] = None
    kilometros: Optional[str] = None
    equipamiento: Optional[str] = None
    observaciones: Optional[str] = None
    conductor_actual: Optional[str] = None
    conductor_actual_id: Optional[str] = None
    tipo_conductor: Optional[str] = None

class VehiculoCreate(VehiculoBase): pass
class VehiculoUpdate(VehiculoBase): pass
class VehiculoOut(VehiculoBase):
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    class Config: from_attributes = True

class ConductorBase(BaseModel):
    id: str
    nombre: str
    nombre_propio: Optional[str] = None
    apellidos: Optional[str] = None
    nif: str
    movil: Optional[str] = None
    email: Optional[str] = None
    fecha_nac: Optional[str] = None
    gestor: Optional[str] = None
    empresa: Optional[str] = None
    vehiculo: Optional[str] = None
    fecha_inicio: Optional[str] = None
    fecha_baja: Optional[str] = None
    codigo_socio: Optional[str] = None
    num_socio: Optional[str] = None
    direccion: Optional[str] = None
    poblacion: Optional[str] = None
    codigo_postal: Optional[str] = None
    provincia: Optional[str] = None
    estado: Optional[str] = "ACTIVO"

class ConductorCreate(ConductorBase): pass
class ConductorUpdate(ConductorBase): pass
class ConductorOut(ConductorBase):
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    class Config: from_attributes = True

class ConductorOut2(ConductorBase):
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    class Config: from_attributes = True

class SeguroBase(BaseModel):
    id: str
    poliza: str
    matricula: str
    tomador: Optional[str] = None
    tipo: Optional[str] = None
    aseguradora: Optional[str] = None
    corredor: Optional[str] = None
    vencimiento: Optional[str] = None
    ambito: Optional[str] = None
    garantias: Optional[str] = None
    estado: Optional[str] = "ACTIVO"
    observaciones: Optional[str] = None

class SeguroCreate(SeguroBase): pass
class SeguroOut(SeguroBase):
    created_at: Optional[datetime] = None
    class Config: from_attributes = True

class FinancieraBase(BaseModel):
    id: str
    num_contrato: str
    vehiculo_id: str
    empresa_id: Optional[str] = None
    tipo: Optional[str] = None
    fecha_inicio: Optional[str] = None
    fecha_fin: Optional[str] = None
    cuota_mensual: Optional[float] = None
    num_cuotas: Optional[int] = None
    dia_pago: Optional[int] = None
    importe_financiado: Optional[float] = None
    valor_residual: Optional[float] = None
    financiera: Optional[str] = None
    gastos_iniciales: Optional[float] = None
    fianzas: Optional[float] = None
    entrada: Optional[float] = None
    observaciones: Optional[str] = None

class FinancieraCreate(FinancieraBase): pass
class FinancieraOut(FinancieraBase):
    created_at: Optional[datetime] = None
    class Config: from_attributes = True

class ContratoBase(BaseModel):
    id: str
    num_contrato: str
    tipo_contrato: Optional[str] = None
    vehiculo_id: str
    cliente_id: Optional[str] = None
    empresa_id: Optional[str] = None
    fecha_inicio: Optional[str] = None
    fecha_fin: Optional[str] = None
    num_cuotas: Optional[int] = None
    cuota_base: Optional[float] = None
    incluye_mantenimiento: Optional[bool] = None
    incluye_neumaticos: Optional[bool] = None
    condiciones: Optional[str] = None
    fianza: Optional[float] = None
    entrada: Optional[float] = None
    valor_residual: Optional[float] = None
    nombre_conductor: Optional[str] = None
    estado: Optional[str] = "ACTIVO"

class ContratoCreate(ContratoBase): pass
class ContratoOut(ContratoBase):
    created_at: Optional[datetime] = None
    class Config: from_attributes = True

class TallerBase(BaseModel):
    id: str
    nombre: str
    telefono: Optional[str] = None
    persona_contacto: Optional[str] = None
    direccion: Optional[str] = None

class TallerOut(TallerBase):
    class Config: from_attributes = True

class TallerEntradaBase(BaseModel):
    id: str
    matricula: str
    taller_id: Optional[str] = None
    taller_nombre: Optional[str] = None
    fecha_entrada: str
    fecha_prevista: Optional[str] = None
    fecha_fin: Optional[str] = None
    tipo_averia: Optional[str] = None
    notas: Optional[str] = None

class TallerEntradaCreate(TallerEntradaBase): pass
class TallerEntradaOut(TallerEntradaBase):
    created_at: Optional[datetime] = None
    class Config: from_attributes = True

class CambioVehiculoBase(BaseModel):
    id: str
    fecha_inicio: str
    matricula_entra: Optional[str] = None
    conductor_entra: Optional[str] = None
    fecha_fin: Optional[str] = None
    matricula_sale: Optional[str] = None
    conductor_sale: Optional[str] = None

class CambioVehiculoCreate(CambioVehiculoBase): pass
class CambioVehiculoOut(CambioVehiculoBase):
    created_at: Optional[datetime] = None
    class Config: from_attributes = True

class TelefonoBase(BaseModel):
    id: Optional[str] = None
    telefono: str
    extension: Optional[str] = None
    persona: Optional[str] = None
    empresa: Optional[str] = None
    email: Optional[str] = None
    pertenece: Optional[str] = None
    area: Optional[str] = None

class TelefonoCreate(TelefonoBase): pass
class TelefonoOut(TelefonoBase):
    created_at: Optional[datetime] = None
    class Config: from_attributes = True

class RegistroEmpresaBase(BaseModel):
    id: str
    matricula: str
    tipo_vehiculo: Optional[str] = None
    fecha_mat: Optional[str] = None
    autorizacion: Optional[str] = None
    fecha_adscripcion: Optional[str] = None
    empresa: Optional[str] = None
    flota: Optional[str] = None
    propiedad: Optional[str] = None
    conductor: Optional[str] = None
    fecha_inicio: Optional[str] = None
    tipo_contrato: Optional[str] = None
    arrendatario: Optional[str] = None
    cuota_socio: Optional[float] = None
    financiera: Optional[str] = None
    tipo_finan: Optional[str] = None
    cuota_finan: Optional[float] = None

class RegistroEmpresaCreate(RegistroEmpresaBase): pass
class RegistroEmpresaOut(RegistroEmpresaBase):
    created_at: Optional[datetime] = None
    class Config: from_attributes = True

class IngresoBase(BaseModel):
    id: str
    nombre_mes: Optional[str] = None
    proveedor: Optional[str] = None
    nif: Optional[str] = None
    codigo: Optional[str] = None
    familia: Optional[str] = None
    num_factura: Optional[int] = None
    ref_factura: Optional[str] = None
    fecha: Optional[str] = None
    cooperativa: Optional[str] = None

class IngresoCreate(IngresoBase): pass
class IngresoOut(IngresoBase):
    created_at: Optional[datetime] = None
    class Config: from_attributes = True

class DashboardStats(BaseModel):
    total_vehiculos: int
    vehiculos_activos: int
    total_conductores: int
    conductores_activos: int
    seguros_activos: int
    vehiculos_en_taller: int
    socios_nuevos: int = 0
    socios_bajas: int = 0
    transcoop: int
    ecotransporte: int
    centralcoop: int