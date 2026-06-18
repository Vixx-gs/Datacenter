# DataCenter Backend

FastAPI + PostgreSQL — API de gestión de flota Transcoop

## Instalación local

```bash
# 1. Crear entorno virtual
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Linux/Mac

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar .env
# Edita .env y pon tu contraseña de PostgreSQL en DATABASE_URL

# 4. Crear base de datos en PostgreSQL
# Abre psql o pgAdmin y ejecuta:
# CREATE DATABASE datacenter_db;

# 5. Arrancar
uvicorn main:app --reload --port 8001
```

## Despliegue en VPS (217.154.97.154)

```bash
# 1. Subir archivos
scp -r datacenter-backend/ usuario@217.154.97.154:/var/www/gesticotrans/

# 2. En el VPS
cd /var/www/gesticotrans/datacenter-backend
pip install -r requirements.txt

# 3. Configurar .env con datos del VPS

# 4. Arrancar con pm2
pm2 start "uvicorn main:app --host 0.0.0.0 --port 8001" --name datacenter-backend
pm2 save
```

## Endpoints principales

- GET  /vehiculos/              — lista de vehículos (filtros: estado, destinado_a)
- GET  /vehiculos/{matricula}   — detalle vehículo
- GET  /conductores/            — lista conductores (filtros: empresa, gestor, estado)
- GET  /conductores/{nif}       — detalle conductor
- GET  /seguros/                — lista seguros (filtros: matricula, estado, tomador)
- GET  /financieras/            — contratos financiación
- GET  /contratos/              — contratos alquiler
- GET  /talleres/entradas       — vehículos en taller
- GET  /cambios/                — cambios de vehículo
- GET  /telefonos/              — directorio
- GET  /registro/               — registro empresas
- GET  /ingresos/               — ingresos
- GET  /dashboard/stats         — stats para el dashboard

Documentación automática: http://localhost:8001/docs
