"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import router_chat, router_search, router_misc


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        Configured FastAPI application instance
    """
    app = FastAPI(
        title="Product Search API",
        description="AI-powered product search with sentiment analysis",
        version="1.0.0"
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(router_chat.router, tags=["chat"])
    app.include_router(router_search.router, tags=["search"])
    app.include_router(router_misc.router, tags=["misc"])
    
    return app


# Create the app instance
app = create_app()
