import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.config import get_settings
from app.core.database import init_db
from app.api.v1 import auth  # users, products, categories, cart, order, ai_consultation
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    # Startup
    logger.info("🚀 Starting application...")
    init_db()
    logger.info("✅ Database initialized successfully!")
    logger.info(f"🎯 {settings.APP_NAME} v{settings.APP_VERSION} started successfully!")
    yield
    # Shutdown
    logger.info("🛑 Shutting down application...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API for Cosmetics Store with AI Consultation",
    lifespan=lifespan
)


# Add middleware để log requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()

    # Log request
    logger.info(f"📍 {request.method} {request.url}")
    logger.info(f"📝 Headers: {dict(request.headers)}")

    response = await call_next(request)

    # Log response
    process_time = time.time() - start_time
    logger.info(f"✅ {request.method} {request.url} - Status: {response.status_code} - Time: {process_time:.2f}s")

    return response


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
import os

if not os.path.exists(settings.UPLOAD_DIR):
    os.makedirs(settings.UPLOAD_DIR)
    logger.info(f"📁 Created upload directory: {settings.UPLOAD_DIR}")
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])


# app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
# app.include_router(products.router, prefix="/api/v1/products", tags=["Products"])
# app.include_router(categories.router, prefix="/api/v1/categories", tags=["Categories"])
# app.include_router(cart.router, prefix="/api/v1/cart", tags=["Cart"])
# app.include_router(order.router, prefix="/api/v1/orders", tags=["Orders"])
# app.include_router(ai_consultation.router, prefix="/api/v1/ai", tags=["AI Consultation"])

@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {
        "message": "Welcome to Cosmetics Store API",
        "version": settings.APP_VERSION,
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    logger.info("Health check endpoint accessed")
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn

    logger.info("Starting server with uvicorn...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"  # Thêm dòng này để hiện log của uvicorn
    )