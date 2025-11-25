from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from app.core.config import get_settings
from urllib.parse import quote_plus
import logging

logger = logging.getLogger(__name__)

settings = get_settings()

# Tạo DATABASE_URL từ các thông tin riêng lẻ
password = quote_plus(settings.DB_PASSWORD)
DATABASE_URL = f"mysql://{settings.DB_USER}:{password}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"

# Create database engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.DEBUG
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function to get database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    try:
        # CHỈ tạo tables, không xóa trước
        Base.metadata.create_all(bind=engine)
        print("✅ Tables checked/created successfully!")

    except Exception as e:
        print(f"❌ Error: {e}")