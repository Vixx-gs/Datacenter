# Migración: PostgreSQL → Firebase Firestore

## Colecciones Firestore necesarias

| Colección Firestore     | Tabla PostgreSQL antigua  | Notas                                  |
|------------------------|--------------------------|----------------------------------------|
| `vehicles`             | `vehiculos`              | Doc ID = matrícula. Fechas YYYY-MM-DD |
| `clients`              | `conductores`            | Doc ID = ID del cliente                |
| `workshops`            | `talleres_lista`         |                                        |
| `workshopEntries`      | `talleres_entradas`      |                                        |
| `driverAssignments`    | `historial_vehiculo`     |                                        |
| `insurancePolicies`    | `seguros`                | Campos en español (del sheet)          |
| `financialAgreements`  | `financieras`            | Campos en español (del sheet)          |
| `rentalContracts`      | `contratos`              | Campos en español (del sheet)          |
| `telefonos`            | `telefonos`              | **NUEVA — crear en Firestore**         |
| `registroEmpresas`     | `registro_empresas`      | **NUEVA — crear en Firestore**         |
| `ingresos`             | `ingresos`               | **NUEVA — crear en Firestore**         |
| `cambiosVehiculos`     | `cambios_vehiculos`      | **NUEVA — crear en Firestore**         |

## Colecciones nuevas — campos a crear en Firestore

### `telefonos`
- `telefono` (string)
- `extension` (string)
- `persona` (string)
- `empresa` (string)
- `email` (string)
- `area` (string)

### `registroEmpresas`
- `matricula` (string)
- `tipoVehiculo` (string)
- `fechaMat` (string YYYY-MM-DD)
- `autorizacion` (string)
- `fechaAdscripcion` (string YYYY-MM-DD)
- `empresa` (string)
- `flota` (string)
- `propiedad` (string)
- `conductor` (string)
- `fechaInicio` (string YYYY-MM-DD)
- `tipoContrato` (string)
- `arrendatario` (string)
- `cuotaSocio` (number)
- `financiera` (string)
- `tipoFinan` (string)
- `cuotaFinan` (number)

### `ingresos`
- `nombreMes` (string)
- `proveedor` (string)
- `nif` (string)
- `codigo` (string)
- `familia` (string)
- `numFactura` (number)
- `refFactura` (string)
- `fecha` (string YYYY-MM-DD)
- `cooperativa` (string)

### `cambiosVehiculos`
- `fechaInicio` (string YYYY-MM-DD)
- `matriculaEntra` (string)
- `conductorEntra` (string)
- `fechaFin` (string YYYY-MM-DD)
- `matriculaSale` (string)
- `conductorSale` (string)

## Pasos para desplegar

1. **Generar archivos** (en local):
   ```
   python migrate_to_firestore.py
   ```

2. **Subir carpeta** `firebase_migration/` al VPS:
   ```
   scp -r firebase_migration/ usuario@vps:/ruta/datacenter-backend/
   ```

3. **Ejecutar deploy** en el VPS:
   ```
   bash firebase_migration/deploy_vps.sh
   ```

4. **Verificar** que la API responde correctamente.

5. **Primer sync** para que los datos queden actualizados:
   ```
   python sync_sheets.py
   ```

## Rollback

Si hay problemas, los archivos originales están en `backup_postgres/`:
```bash
cp backup_postgres/database.py database.py
cp backup_postgres/sync_sheets.py sync_sheets.py
cp backup_postgres/requirements.txt requirements.txt
cp -r backup_postgres/routers/* routers/
pip install -r requirements.txt
pm2 restart datacenter-api
```
