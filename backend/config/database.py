# backend/config.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# ==== Genel Path Ayarları ====
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # backend/
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)  # data klasörü yoksa oluştur

# Newsletter JSON dosyası yolu
SAVE_PATH = os.path.join(DATA_DIR, "selected_newsletters.json")

# ==== Veritabanı Ayarları ====
DB_PATH = os.path.join(DATA_DIR, "users.db")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
