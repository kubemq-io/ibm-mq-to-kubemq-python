"""Main FastAPI application for exposing metrics and health endpoints."""
import asyncio
import json
import os
from pathlib import Path
from typing import Optional, Callable, Any
import uvicorn
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from src.api.routes import health, metrics
from src.bindings.bindings import Bindings
from src.common.log import get_logger


logger = get_logger("api")


class PrettyJSONResponse(JSONResponse):
    """Custom JSONResponse that formats JSON with indentation."""
    
    def render(self, content: Any) -> bytes:
        """Render the content with pretty JSON formatting.
        
        Args:
            content: The content to render
            
        Returns:
            bytes: The rendered content
        """
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=2,
            separators=(", ", ": "),
        ).encode("utf-8")


class APIServer:
    """API server for exposing metrics and health endpoints.
    
    This class manages the FastAPI application for exposing metrics and
    health information from all bindings.
    """
    
    def __init__(self, bindings: Bindings, host: str = "0.0.0.0", port: int = 9000):
        """Initialize the API server.
        
        Args:
            bindings: The bindings instance to expose
            host: The host to bind to
            port: The port to listen on
        """
        self.bindings = bindings
        self.host = host
        self.port = port
        self.app = self._create_app()
        self._server_task = None
        
    def _create_app(self) -> FastAPI:
        """Create the FastAPI application.
        
        Returns:
            FastAPI: The configured FastAPI application
        """
        app = FastAPI(
            title="IBM MQ - KubeMQ Connector API",
            description="API for monitoring IBM MQ - KubeMQ connections",
            version="1.0.0",
            default_response_class=PrettyJSONResponse
        )
        
        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Setup dependency injection properly using dependency_overrides
        def get_bindings_dependency():
            logger.debug("Dependency injector called - returning bindings instance")
            return self.bindings
        
        # Include routers
        app.include_router(health.router)
        app.include_router(metrics.router)
        
        # Set up dependency overrides correctly - this is the proper way in FastAPI
        app.dependency_overrides[health.get_bindings] = get_bindings_dependency
        app.dependency_overrides[metrics.get_bindings] = get_bindings_dependency
        
        # Mount static files
        static_dir = Path(__file__).parent / "static"
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
        
        # Add dashboard endpoint
        @app.get("/dashboard", response_class=HTMLResponse)
        async def dashboard():
            """Serve the dashboard HTML page."""
            html_file = static_dir / "index.html"
            return html_file.read_text("utf-8")
            
        # Add root endpoint
        @app.get("/")
        async def root():
            return {
                "name": "IBM MQ - KubeMQ Connector API",
                "version": "1.0.0",
                "endpoints": [
                    {"path": "/health", "description": "Health status for all bindings"},
                    {"path": "/health/{binding_name}", "description": "Health status for a specific binding"},
                    {"path": "/metrics", "description": "Metrics for all bindings"},
                    {"path": "/metrics/{binding_name}", "description": "Metrics for a specific binding"},
                    {"path": "/dashboard", "description": "Dashboard for monitoring bindings"}
                ]
            }
            
        return app
    
    async def start(self):
        """Start the API server."""
        config = uvicorn.Config(
            app=self.app,
            host=self.host,
            port=self.port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        
        logger.info(f"Starting API server on {self.host}:{self.port}")
        self._server_task = asyncio.create_task(server.serve())
        
    async def stop(self):
        """Stop the API server."""
        if self._server_task and not self._server_task.done():
            logger.info("Stopping API server")
            self._server_task.cancel()
            try:
                await self._server_task
            except asyncio.CancelledError:
                pass
            
            logger.info("API server stopped") 