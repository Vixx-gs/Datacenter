from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from auth import verificar_credenciales, crear_token, verificar_horario, es_sin_horario

router = APIRouter(prefix="/auth", tags=["auth"])

class LoginRequest(BaseModel):
    usuario: str
    password: str

@router.post("/login")
def login(data: LoginRequest):
    if not verificar_credenciales(data.usuario, data.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales incorrectas")
    if not es_sin_horario(data.usuario):
        verificar_horario()
    token = crear_token(data.usuario)
    return {"access_token": token, "token_type": "bearer"}
