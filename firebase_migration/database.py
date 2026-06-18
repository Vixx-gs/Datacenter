"""
database.py  –  Conexión a Firebase Firestore (reemplaza SQLAlchemy/PostgreSQL)
Usa google-cloud-firestore con credenciales de Service Account.
"""
from google.cloud import firestore
from google.oauth2.service_account import Credentials
from pathlib import Path

_BASE = Path(__file__).parent
_SA   = _BASE / "ai-studio-applet-webapp-55a1a-firebase-adminsdk-fbsvc-67d511e6d4.json"

_creds = Credentials.from_service_account_file(str(_SA))
db = firestore.Client(
    project     = "ai-studio-applet-webapp-55a1a",
    credentials = _creds,
    database    = "ai-studio-7801edee-96c4-47bb-8194-68abcf65e834",
)

def get_db():
    """Dependency injection compatible con FastAPI (igual que el antiguo get_db)."""
    return db
