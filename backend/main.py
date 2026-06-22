import os
import uvicorn
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
load_dotenv()

# Import routes and database init
from backend.database.mongodb import init_db, is_mock_db
from backend.api.chat_routes import router as chat_router
from backend.api.train_routes import router as train_router
from backend.api.booking_routes import router as booking_router
from backend.api.pnr_routes import router as pnr_router
from backend.api.analytics import router as analytics_router
from backend.api.monitoring import router as monitoring_router
from backend.mcp.server import router as mcp_router
from backend.api.auth_routes import router as auth_router, get_current_user


# Setup logging — only configure once here, not in submodules
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger("traingpt.main")

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up TrainGPT AI Backend...")
    await init_db()
    try:
        yield
    finally:
        # Graceful shutdown — log and allow connections to drain
        logger.info("Shutting down TrainGPT AI Backend...")

# Determine allowed origins from environment (defaults to local dev)
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"
).split(",")

app = FastAPI(
    title="TrainGPT AI Backend",
    description="Multi-Agent Railway Booking Assistant backend using FastAPI, ADK, and Gemini.",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
# NOTE: allow_origins=["*"] is incompatible with allow_credentials=True per the CORS spec.
# Use explicit origin list to support credentialed requests from the frontend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(train_router)
app.include_router(booking_router)
app.include_router(pnr_router)
app.include_router(analytics_router)
app.include_router(mcp_router)
app.include_router(monitoring_router)

# Legacy fallbacks mapping directly to auth methods
from fastapi import Depends
@app.get("/api/profile")
async def profile_legacy_fallback(current_user = Depends(get_current_user)):
    from backend.api.auth_routes import get_profile
    return await get_profile(current_user)

@app.post("/api/logout")
async def logout_legacy_fallback(current_user = Depends(get_current_user)):
    from backend.api.auth_routes import logout
    return await logout(current_user)

@app.get("/health")
def health_check():
    from backend.database import mongodb as db_module
    # Keep the health endpoint minimal for monitoring checks.
    return {
        "status": "healthy",
        "service": "TrainGPT AI"
    }

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Running FastAPI on http://{host}:{port}")
    uvicorn.run("backend.main:app", host=host, port=port, reload=True)
