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
cp firebase_migration/sheets_cache.py   sheets_cache.py
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
python - <<'PYEOF'
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
