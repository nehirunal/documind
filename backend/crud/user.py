from sqlalchemy.orm import Session
from backend.models.user import User
from backend.utils.auth import get_password_hash, verify_password
from backend.schemas.user import UserCreate

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def create_user(db: Session, user: UserCreate):
    hashed_pw = get_password_hash(user.password)
    db_user = User(email=user.email, hashed_password=hashed_pw)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
