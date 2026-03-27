from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.api.image_proxy import router as image_router
from app.api.admin import router as admin_router
from app.api.agents import router as agents_router
from app.api.feedback import router as feedback_router
from app.api.files import router as files_router
from app.config import get_settings


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    
    app = FastAPI(
        title="Grocery List Structuring Engine",
        description="""
        AI-powered engine that converts unstructured grocery input into clean, structured shopping lists.
        
        ## How it works
        
        1. **Parser Agent** (LLM) - Splits raw text into individual grocery items
        2. **Normalizer Agent** (LLM) - Extracts structured data (product name, quantity, unit, modifiers)
        3. **Autocomplete API** - Resolves products using the ONLY authoritative product database
        4. **Confidence Scoring** - Applies deterministic guardrails and safe fallbacks
        
        ## Guarantees
        
        - SKU is ONLY present if returned by the Autocomplete API
        - No hallucinated products
        - All uncertainty is captured in the notes field
        - Fail-safe behavior: prefers generic products over wrong products
        """,
        version=settings.app_version,
    )
    
    # CORS: allow any origin via regex (Vercel, localhost, etc.)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[],
        allow_origin_regex=r"https?://[^/]+",  # any http(s) origin
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )
    
    # Include routes
    app.include_router(router, prefix="/api/v1", tags=["grocery-list"])
    app.include_router(image_router, prefix="/api/v1", tags=["images"])
    app.include_router(admin_router, prefix="/api/v1", tags=["admin"])
    app.include_router(agents_router, prefix="/api/v1/agents", tags=["agents"])
    app.include_router(feedback_router, prefix="/api/v1", tags=["feedback"])
    app.include_router(files_router, prefix="/api/v1", tags=["files"])
    
    # Health check endpoint
    @app.get("/health", tags=["health"])
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "version": settings.app_version}
    
    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
