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
    rol: str | None = None   # rol en el portal (solo en SSO): admin | gestorT | gestor

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

# ── Inicio de sesión con el Portal del Empleado (SSO) ─────────────
# El navegador envía la cookie de sesión del portal a todo *.gesticotrans.app.
# Se la reenviamos al portal, que dice quién es y qué rol tiene en Datacenter.
import os
import requests

PORTAL_URL = os.getenv("PORTAL_URL", "https://gesticotrans.app")
PORTAL_COOKIE = "__Secure-gt_session"
ROLES = {"admin", "gestorT", "gestor"}
ROLES_SIN_HORARIO = {"admin", "gestorT"}   # "gestor" solo de 8:00 a 18:00

@router.post("/sso", response_model=LoginResponse)
def sso(request: Request):
    cookie = request.cookies.get(PORTAL_COOKIE)
    if not cookie:
        raise HTTPException(status_code=401, detail="No has iniciado sesión en el portal.")
    try:
        r = requests.get(f"{PORTAL_URL}/api/me", cookies={PORTAL_COOKIE: cookie}, timeout=8)
    except requests.RequestException:
        raise HTTPException(status_code=502, detail="El portal no responde.")
    if r.status_code in (401, 403):
        raise HTTPException(status_code=401, detail="La sesión del portal no es válida.")
    if not r.ok:
        raise HTTPException(status_code=502, detail="El portal no responde.")
    me = r.json()
    role = (me.get("access") or {}).get("datacenter")
    if role not in ROLES:
        raise HTTPException(status_code=403, detail="No tienes acceso a Datacenter. Pídelo a un administrador del portal.")

    sin_horario = role in ROLES_SIN_HORARIO
    if not sin_horario:
        verificar_horario()

    from datetime import datetime, timedelta
    expira = (datetime.now() + timedelta(hours=24)).strftime("%H:%M") if sin_horario         else datetime.now().replace(hour=HORA_FIN, minute=0, second=0).strftime("%H:%M")
    return {
        "token":   crear_token(me["username"], sin_horario=sin_horario),
        "usuario": me.get("nombre") or me["username"],
        "expira":  expira,
        "rol":     role,
    }

@router.post("/logout")
def logout():
    return {"message": "Sesión cerrada"}