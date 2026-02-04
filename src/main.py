from fastapi import FastAPI
from src.commit.router import router as commit_router
from src.readme.router import router as readme_router
from src.infrastructure.router import router as infrastructure_router



app = FastAPI(title="SubText Backend")

# Mount Domain Routers (Prefix /api/v1)
app.include_router(commit_router, prefix="/api/v1/commits", tags=["Commit"])
app.include_router(readme_router, prefix="/api/v1/readmes", tags=["ReadMe"])

# Mount Infrastructure Router
app.include_router(infrastructure_router, tags=["Infrastructure"])


@app.get("/", tags=["health"])
def root():
    return {
        "service": "subtext-backend",
        "status": "ok",
        "docs": "/docs",
        "readme_api": "/api/readme/generate",
    }

