# backend/routes/auth.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.schemas.user import UserCreate, UserOut, UserLogin
from backend.crud.user import get_user_by_email, create_user
from backend.utils.auth import verify_password
from backend.config.database import SessionLocal

router = APIRouter(prefix="/auth", tags=["auth"])  # <-- EKLENDİ

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/signup", response_model=UserOut)
def signup(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = get_user_by_email(db, user.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return create_user(db, user)

@router.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = get_user_by_email(db, user.email)
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"message": "Login successful!"}
