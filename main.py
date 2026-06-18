from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from routers import vehiculos, conductores, seguros, financieras, contratos, talleres, cambios, telefonos, registro, ingresos, dashboard, entregas, itv, tacografo
from routers import login

app = FastAPI(title="DataCenter API", docs_url=None, redoc_url=None)  # Desactivar docs en prod

# ── Security Headers Middleware ────────────────────────────────
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"]    = "nosniff"
        response.headers["X-Frame-Options"]            = "DENY"
        response.headers["X-XSS-Protection"]           = "1; mode=block"
        response.headers["Referrer-Policy"]             = "strict-origin-when-cross-origin"
        response.headers["Strict-Transport-Security"]   = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"]     = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "connect-src 'self' https://datacenter.gesticotrans.com"
        )
        return response

app.add_middleware(SecurityHeadersMiddleware)

# ── CORS estricto ─────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://datacenter.gesticotrans.com",
        "http://localhost:4200",  # solo para desarrollo local
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# ── Routers ───────────────────────────────────────────────────
app.include_router(login.router)
app.include_router(vehiculos.router)
app.include_router(conductores.router)
app.include_router(seguros.router)
app.include_router(financieras.router)
app.include_router(contratos.router)
app.include_router(talleres.router)
app.include_router(cambios.router)
app.include_router(telefonos.router)
app.include_router(registro.router)
app.include_router(ingresos.router)
app.include_router(dashboard.router)
app.include_router(entregas.router)
app.include_router(itv.router)
app.include_router(tacografo.router)

@app.get("/health")
def health():
    return {"status": "ok"}