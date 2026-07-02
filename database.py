from google.cloud import firestore
from google.oauth2.service_account import Credentials
from pathlib import Path

_SA = Path(__file__).parent / "firebase_migration" / "ai-studio-applet-webapp-55a1a-firebase-adminsdk-fbsvc-827f939cd7.json"

_creds = Credentials.from_service_account_file(str(_SA))
db = firestore.Client(
    project     = "ai-studio-applet-webapp-55a1a",
    credentials = _creds,
    database    = "ai-studio-7801edee-96c4-47bb-8194-68abcf65e834",
)

def get_db():
    return db
