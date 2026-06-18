from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text
from database import Base
from datetime import datetime

class Vehiculo(Base):
    __tablename__ = "vehiculos"

    matricula           = Column(String, primary_key=True, index=True)
    marca               = Column(String, nullable=True)
    modelo              = Column(String, nullable=True)
    bastidor            = Column(String, nullable=True)
    fecha_mat           = Column(String, nullable=True)
    destinado_a         = Column(String, nullable=True)
    propiedad           = Column(String, nullable=True)
    situacion           = Column(String, nullable=True)
    estado              = Column(String, default="ACTIVO")
    fecha_incorporacion = Column(String, nullable=True)
    itv                 = Column(String, nullable=True)
    tacografo           = Column(String, nullable=True)
    mantenimiento       = Column(String, nullable=True)
    fecha_fin_mto       = Column(String, nullable=True)
    km_fin_mto          = Column(String, nullable=True)
    precio_mto          = Column(String, nullable=True)
    garantia            = Column(String, nullable=True)
    fecha_fin_garantia  = Column(String, nullable=True)
    km_fin_garantia     = Column(String, nullable=True)
    kilometros          = Column(String, nullable=True)
    equipamiento        = Column(Text, nullable=True)
    observaciones       = Column(Text, nullable=True)
    conductor_actual    = Column(String, nullable=True)
    conductor_actual_id = Column(String, nullable=True)
    tipo_conductor      = Column(String, nullable=True)
    created_at          = Column(DateTime, default=datetime.utcnow)
    updated_at          = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Conductor(Base):
    __tablename__ = "conductores"

    id            = Column(String, primary_key=True, index=True)
    nombre        = Column(String, index=True)
    nombre_propio = Column(String, nullable=True)
    apellidos     = Column(String, nullable=True)
    nif           = Column(String, index=True)
    num_tarj_conductor = Column(String, nullable=True)
    movil         = Column(String, nullable=True)
    email         = Column(String, nullable=True)
    fecha_nac     = Column(String, nullable=True)
    gestor        = Column(String, nullable=True)
    empresa       = Column(String, nullable=True)
    vehiculo      = Column(String, nullable=True)
    fecha_inicio  = Column(String, nullable=True)
    fecha_prevista= Column(String, nullable=True)
    fecha_baja    = Column(String, nullable=True)
    codigo_socio  = Column(String, nullable=True)
    num_socio     = Column(String, nullable=True)
    direccion     = Column(String, nullable=True)
    poblacion     = Column(String, nullable=True)
    codigo_postal = Column(String, nullable=True)
    provincia     = Column(String, nullable=True)
    estado        = Column(String, default="ACTIVO")
    created_at    = Column(DateTime, default=datetime.utcnow)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Seguro(Base):
    __tablename__ = "seguros"

    id            = Column(String, primary_key=True, index=True)
    poliza        = Column(String, index=True)
    matricula     = Column(String, index=True)
    tomador       = Column(String, nullable=True)
    tipo          = Column(String, nullable=True)
    aseguradora   = Column(String, nullable=True)
    corredor      = Column(String, nullable=True)
    vencimiento   = Column(String, nullable=True)
    ambito        = Column(String, nullable=True)
    garantias     = Column(String, nullable=True)
    estado        = Column(String, default="ACTIVO")
    observaciones = Column(Text, nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Financiera(Base):
    __tablename__ = "financieras"

    id                 = Column(String, primary_key=True, index=True)
    num_contrato       = Column(String, index=True)
    vehiculo_id        = Column(String, index=True)
    empresa_id         = Column(String, nullable=True)
    tipo               = Column(String, nullable=True)
    fecha_inicio       = Column(String, nullable=True)
    fecha_fin          = Column(String, nullable=True)
    cuota_mensual      = Column(Float, nullable=True)
    num_cuotas         = Column(Integer, nullable=True)
    dia_pago           = Column(Integer, nullable=True)
    importe_financiado = Column(Float, nullable=True)
    valor_residual     = Column(Float, nullable=True)
    financiera         = Column(String, nullable=True)
    gastos_iniciales   = Column(Float, nullable=True)
    fianzas            = Column(Float, nullable=True)
    entrada            = Column(Float, nullable=True)
    observaciones      = Column(Text, nullable=True)
    created_at         = Column(DateTime, default=datetime.utcnow)
    updated_at         = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Contrato(Base):
    __tablename__ = "contratos"

    id                    = Column(String, primary_key=True, index=True)
    num_contrato          = Column(String, index=True)
    tipo_contrato         = Column(String, nullable=True)
    vehiculo_id           = Column(String, index=True)
    cliente_id            = Column(String, nullable=True)
    empresa_id            = Column(String, nullable=True)
    fecha_inicio          = Column(String, nullable=True)
    fecha_fin             = Column(String, nullable=True)
    num_cuotas            = Column(Integer, nullable=True)
    cuota_base            = Column(Float, nullable=True)
    incluye_mantenimiento = Column(Boolean, nullable=True)
    incluye_neumaticos    = Column(Boolean, nullable=True)
    condiciones           = Column(Text, nullable=True)
    fianza                = Column(Float, nullable=True)
    entrada               = Column(Float, nullable=True)
    valor_residual        = Column(Float, nullable=True)
    nombre_conductor      = Column(String, nullable=True)
    estado                = Column(String, default="ACTIVO")
    created_at            = Column(DateTime, default=datetime.utcnow)
    updated_at            = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Taller(Base):
    __tablename__ = "talleres_lista"
    id               = Column(String, primary_key=True, index=True)
    nombre           = Column(String)
    telefono         = Column(String, nullable=True)
    persona_contacto = Column(String, nullable=True)
    direccion        = Column(String, nullable=True)


class TallerEntrada(Base):
    __tablename__ = "talleres_entradas"
    id             = Column(String, primary_key=True, index=True)
    matricula      = Column(String, index=True)
    taller_id      = Column(String, nullable=True)
    taller_nombre  = Column(String, nullable=True)
    fecha_entrada  = Column(String)
    fecha_prevista = Column(String, nullable=True)
    fecha_fin      = Column(String, nullable=True)
    tipo_averia    = Column(String, nullable=True)
    notas          = Column(Text, nullable=True)
    created_at     = Column(DateTime, default=datetime.utcnow)
    updated_at     = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CambioVehiculo(Base):
    __tablename__ = "cambios_vehiculos"
    id              = Column(String, primary_key=True, index=True)
    fecha_inicio    = Column(String)
    matricula_entra = Column(String, nullable=True)
    conductor_entra = Column(String, nullable=True)
    fecha_fin       = Column(String, nullable=True)
    matricula_sale  = Column(String, nullable=True)
    conductor_sale  = Column(String, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)


class Telefono(Base):
    __tablename__ = "telefonos"
    id         = Column(String, primary_key=True, index=True)
    telefono   = Column(String)
    extension  = Column(String, nullable=True)
    persona    = Column(String, nullable=True)
    empresa    = Column(String, nullable=True)
    email      = Column(String, nullable=True)
    pertenece  = Column(String, nullable=True)
    area       = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RegistroEmpresa(Base):
    __tablename__ = "registro_empresas"
    id                = Column(String, primary_key=True, index=True)
    matricula         = Column(String, index=True)
    tipo_vehiculo     = Column(String, nullable=True)
    fecha_mat         = Column(String, nullable=True)
    autorizacion      = Column(String, nullable=True)
    fecha_adscripcion = Column(String, nullable=True)
    empresa           = Column(String, nullable=True)
    flota             = Column(String, nullable=True)
    propiedad         = Column(String, nullable=True)
    conductor         = Column(String, nullable=True)
    fecha_inicio      = Column(String, nullable=True)
    tipo_contrato     = Column(String, nullable=True)
    arrendatario      = Column(String, nullable=True)
    cuota_socio       = Column(Float, nullable=True)
    financiera        = Column(String, nullable=True)
    tipo_finan        = Column(String, nullable=True)
    cuota_finan       = Column(Float, nullable=True)
    created_at        = Column(DateTime, default=datetime.utcnow)
    updated_at        = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Ingreso(Base):
    __tablename__ = "ingresos"
    id          = Column(String, primary_key=True, index=True)
    nombre_mes  = Column(String, nullable=True)
    proveedor   = Column(String, nullable=True)
    nif         = Column(String, nullable=True)
    codigo      = Column(String, nullable=True)
    familia     = Column(String, nullable=True)
    num_factura = Column(Integer, nullable=True)
    ref_factura = Column(String, nullable=True)
    fecha       = Column(String, nullable=True)
    cooperativa = Column(String, nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow)


class HistorialVehiculo(Base):
    __tablename__ = "historial_vehiculo"

    id           = Column(String, primary_key=True, index=True)
    vehiculo_id  = Column(String, index=True)
    conductor_id = Column(String, index=True)
    fecha_inicio = Column(String, nullable=True)
    fecha_fin    = Column(String, nullable=True)
    accion       = Column(String, nullable=True)
    observaciones= Column(Text, nullable=True)
    created_at   = Column(DateTime, default=datetime.utcnow)