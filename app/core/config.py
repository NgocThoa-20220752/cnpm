import os
from typing import List
from functools import lru_cache
from dotenv import load_dotenv

# Load .env từ thư mục gốc
load_dotenv()

class Settings:
    # Application
    APP_NAME: str = os.getenv("APP_NAME", "Cosmetics Store API")
    APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"

    # Database
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
    DB_USER: str = os.getenv("DB_USER", "root")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_NAME: str = os.getenv("DB_NAME", "cosmetics")

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    # Email
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    EMAIL_FROM: str = os.getenv("EMAIL_FROM", "")
    EMAIL_FROM_NAME: str = os.getenv("EMAIL_FROM_NAME", "Cosmetics Store")

    # AI Configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    AI_MODEL: str = os.getenv("AI_MODEL", "gpt-4")

    # Payment
    MOMO_PARTNER_CODE: str = os.getenv("MOMO_PARTNER_CODE", "")
    MOMO_ACCESS_KEY: str = os.getenv("MOMO_ACCESS_KEY", "")
    MOMO_SECRET_KEY: str = os.getenv("MOMO_SECRET_KEY", "")
    VNP_TMN_CODE: str = os.getenv("VNP_TMN_CODE", "")
    VNP_HASH_SECRET: str = os.getenv("VNP_HASH_SECRET", "")
    VNP_URL: str = os.getenv("VNP_URL", "https://sandbox.vnpayment.vn/paymentv2/vpcpay.html")

    # File Upload
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
    MAX_UPLOAD_SIZE: int = int(os.getenv("MAX_UPLOAD_SIZE", "5242880"))
    ALLOWED_EXTENSIONS: str = os.getenv("ALLOWED_EXTENSIONS", "jpg,jpeg,png,gif")

    # Redis
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))

    # CORS
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8080")

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    @property
    def allowed_extensions_list(self) -> List[str]:
        return [ext.strip() for ext in self.ALLOWED_EXTENSIONS.split(",")]

    @property
    def database_url(self) -> str:
        """Tạo DATABASE_URL từ các thành phần"""
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


@lru_cache()
def get_settings() -> Settings:
    return Settings()