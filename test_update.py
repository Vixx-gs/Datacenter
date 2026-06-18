from database import SessionLocal
import models
from sqlalchemy import text

db = SessionLocal()

v = db.query(models.Vehiculo).filter(models.Vehiculo.matricula == '0033MWC').first()
print(f'ANTES: {v.conductor_actual}')

db.execute(text("UPDATE vehiculos SET conductor_actual='DRAGOS CRISTIAN ROSCA', conductor_actual_id='2146', tipo_conductor='actual' WHERE matricula='0033MWC'"))
db.commit()
db.expire_all()

v2 = db.query(models.Vehiculo).filter(models.Vehiculo.matricula == '0033MWC').first()
print(f'DESPUES: {v2.conductor_actual}')
db.close()