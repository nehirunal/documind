# backend/config/__init__.py

# DB ile ilgili şeyler
from .database import engine, SessionLocal, Base, get_db

# Yollar
from .paths import BASE_DIR, DATA_DIR, SAVE_PATH

import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_PATH = os.path.join(BASE_DIR, "..", "data", "selected_newsletters.json")
SAVE_PATH = os.path.abspath(SAVE_PATH)
print(">>> SAVE_PATH =", SAVE_PATH)
