import jwt
import bcrypt
import os
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

load_dotenv()

# ── Configuración ─────────────────────────────────────────────
SECRET_KEY  = os.getenv("SECRET_KEY", "change_me")
ALGORITHM   = "HS256"
HORA_INICIO = 8   # 08:00
HORA_FIN    = 18  # 18:00

# Usuarios del sistema
USUARIOS = {
    "gestor": {
        "password_hash": bcrypt.hashpw(os.getenv("PASS_GESTOR", "").encode(), bcrypt.gensalt()),
        "sin_horario": False,
    },
    "admin": {
        "password_hash": bcrypt.hashpw(os.getenv("PASS_ADMIN", "").encode(), bcrypt.gensalt()),
        "sin_horario": True,  # acceso 24h
    },
    "gestorT": {
        "password_hash": bcrypt.hashpw(os.getenv("PASS_GESTORT", "").encode(), bcrypt.gensalt()),
        "sin_horario": True,  # acceso 24h
    },
}

security = HTTPBearer()

def verificar_horario():
    ahora = datetime.now()
    hora  = ahora.hour
    if not (HORA_INICIO <= hora < HORA_FIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Acceso solo permitido de {HORA_INICIO}:00 a {HORA_FIN}:00h"
        )

def verificar_credenciales(usuario: str, password: str) -> bool:
    if usuario not in USUARIOS:
        return False
    user_data = USUARIOS[usuario]
    return bcrypt.checkpw(password.encode(), user_data["password_hash"])

def es_sin_horario(usuario: str) -> bool:
    return USUARIOS.get(usuario, {}).get("sin_horario", False)

def crear_token(usuario: str) -> str:
    ahora = datetime.now(timezone.utc)
    if es_sin_horario(usuario):
        expiracion = ahora + timedelta(hours=24)
    else:
        hoy_18     = ahora.replace(hour=HORA_FIN, minute=0, second=0, microsecond=0)
        expiracion = min(hoy_18, ahora + timedelta(hours=3))

    payload = {
        "sub": usuario,
        "iat": ahora,
        "exp": expiracion,
        "sin_horario": es_sin_horario(usuario),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verificar_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        usuario = payload.get("sub")
        if not usuario:
            raise HTTPException(status_code=401, detail="Token inválido")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Sesión expirada")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")

    if not payload.get("sin_horario", False):
        verificar_horario()

    return usuario
