import bcrypt
from fastapi import APIRouter, HTTPException, status, Request
from pydantic import BaseModel
from auth import verificar_credenciales, es_sin_horario, crear_token, verificar_horario, HORA_FIN

router = APIRouter(prefix="/auth", tags=["auth"])

class LoginRequest(BaseModel):
    usuario: str
    password: str

class LoginResponse(BaseModel):
    token: str
    usuario: str
    expira: str

@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, request: Request):
    # Solo verificar horario si NO es un usuario sin restricción
    if not es_sin_horario(body.usuario):
        verificar_horario()

    # Verificar credenciales
    if not verificar_credenciales(body.usuario, body.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos"
        )

    token = crear_token(body.usuario)

    from datetime import datetime, timedelta
    if es_sin_horario(body.usuario):
        expira = (datetime.now() + timedelta(hours=24)).strftime("%H:%M")
    else:
        expira = datetime.now().replace(hour=HORA_FIN, minute=0, second=0).strftime("%H:%M")

    return {
        "token":   token,
        "usuario": body.usuario,
        "expira":  expira,
    }

@router.post("/logout")
def logout():
    return {"message": "Sesión cerrada"}