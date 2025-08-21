# backend/config/paths.py
import os

# backend/ klasörünün yolu
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # -> .../backend
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

# Newsletter seçimlerinin tutulduğu JSON
SAVE_PATH = os.path.join(DATA_DIR, "selected_newsletters.json")
CREDENTIALS_PATH = os.path.join(DATA_DIR, "credentials.json")
TOKEN_PATH = os.path.join(DATA_DIR, "token.json")