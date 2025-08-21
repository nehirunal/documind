from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, UniqueConstraint
from backend.config.database import Base

class NewsletterPreference(Base):
    __tablename__ = "newsletter_preferences"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    sender = Column(String, index=True, nullable=False)
    name = Column(String, nullable=False)
    is_selected = Column(Boolean, default=True)
    count30d = Column(Integer, default=0)

    __table_args__ = (UniqueConstraint("user_id", "sender", name="uq_user_sender"),)
