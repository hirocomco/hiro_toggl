from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from app.api.test_routes import router as test_router
from app.api.rates import router as rates_router
from app.api.sync import router as sync_router
from app.api.reports import router as reports_router

app = FastAPI(
    title="Toggl Client Reports API",
    description="API for generating client-based time tracking reports with rate management",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(test_router)
app.include_router(rates_router)
app.include_router(sync_router)
app.include_router(reports_router)

@app.get("/")
async def root():
    return {"message": "Toggl Client Reports API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "toggl-client-reports"}

@app.get("/api/test")
async def test_endpoint():
    return {
        "message": "API is working",
        "toggl_token_set": bool(os.getenv("TOGGL_API_TOKEN")),
        "workspace_id_set": bool(os.getenv("TOGGL_WORKSPACE_ID"))
    }