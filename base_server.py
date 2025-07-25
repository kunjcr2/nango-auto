"""
Base FastAPI server template for API integrations
Provides OAuth flow, webhook handling, and API proxying
"""

import os
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field
import uvicorn
import structlog

from base_client import BaseAPIClient, APIResponse

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Pydantic models
class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str = "1.0.0"
    integration: str

class ErrorResponse(BaseModel):
    error: str
    message: str
    timestamp: datetime
    request_id: Optional[str] = None

class OAuthCallbackModel(BaseModel):
    code: str
    state: Optional[str] = None

class WebhookPayload(BaseModel):
    event: str
    data: Dict[str, Any]
    timestamp: datetime

class IntegrationStats(BaseModel):
    total_requests: int
    total_errors: int
    error_rate: float
    connection_id: str
    provider: str
    uptime_seconds: int

# Global client instance (will be initialized by subclass)
api_client: Optional[BaseAPIClient] = None
app_start_time = datetime.now()

class BaseIntegrationServer:
    """Base class for integration servers"""
    
    def __init__(
        self,
        integration_name: str,
        provider: str,
        client_class: type,
        nango_public_key: str,
        oauth_redirect_uri: str = None
    ):
        self.integration_name = integration_name
        self.provider = provider
        self.client_class = client_class
        self.nango_public_key = nango_public_key
        self.oauth_redirect_uri = oauth_redirect_uri or f"http://localhost:8000/oauth/callback"
        
        # Initialize FastAPI app
        self.app = self.create_app()
        
        # Store active connections
        self.active_connections: Dict[str, BaseAPIClient] = {}
    
    def create_app(self) -> FastAPI:
        """Create FastAPI application with middleware and routes"""
        
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Startup
            logger.info(f"Starting {self.integration_name} integration server")
            yield
            # Shutdown
            logger.info(f"Shutting down {self.integration_name} integration server")
            await self.cleanup_connections()
        
        app = FastAPI(
            title=f"{self.integration_name} Integration API",
            description=f"API integration for {self.integration_name} using Nango OAuth",
            version="1.0.0",
            lifespan=lifespan
        )
        
        # Add middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Configure appropriately for production
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["*"]  # Configure appropriately for production
        )
        
        # Add custom middleware
        @app.middleware("http")
        async def logging_middleware(request: Request, call_next):
            start_time = datetime.now()
            
            # Log request
            logger.info(
                "Request started",
                method=request.method,
                url=str(request.url),
                client_ip=request.client.host if request.client else None
            )
            
            try:
                response = await call_next(request)
                duration = (datetime.now() - start_time).total_seconds()
                
                # Log response
                logger.info(
                    "Request completed",
                    method=request.method,
                    url=str(request.url),
                    status_code=response.status_code,
                    duration_seconds=duration
                )
                
                return response
                
            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds()
                logger.error(
                    "Request failed",
                    method=request.method,
                    url=str(request.url),
                    error=str(e),
                    duration_seconds=duration
                )
                raise
        
        # Add exception handler
        @app.exception_handler(Exception)
        async def global_exception_handler(request: Request, exc: Exception):
            logger.error(
                "Unhandled exception",
                url=str(request.url),
                method=request.method,
                error=str(exc),
                exc_info=True
            )
            
            return JSONResponse(
                status_code=500,
                content=ErrorResponse(
                    error="Internal Server Error",
                    message="An unexpected error occurred",
                    timestamp=datetime.now()
                ).dict()
            )
        
        # Register routes
        self.register_routes(app)
        
        return app
    
    def register_routes(self, app: FastAPI) -> None:
        """Register all API routes"""
        
        @app.get("/health", response_model=HealthResponse)
        async def health_check():
            """Health check endpoint"""
            return HealthResponse(
                status="healthy",
                timestamp=datetime.now(),
                integration=self.integration_name
            )
        
        @app.get("/stats", response_model=IntegrationStats)
        async def get_stats(connection_id: str):
            """Get integration statistics"""
            client = await self.get_client(connection_id)
            stats = client.get_stats()
            
            uptime = (datetime.now() - app_start_time).total_seconds()
            
            return IntegrationStats(
                **stats,
                uptime_seconds=int(uptime)
            )
        
        @app.post("/oauth/initiate")
        async def initiate_oauth(connection_id: str):
            """Initiate OAuth flow"""
            # In a real implementation, this would redirect to Nango's OAuth initiation
            nango_oauth_url = f"https://api.nango.dev/oauth/authorize/{self.provider}"
            
            params = {
                "connection_id": connection_id,
                "redirect_uri": self.oauth_redirect_uri,
                "response_type": "code"
            }
            
            # Build URL with params
            param_string = "&".join([f"{k}={v}" for k, v in params.items()])
            full_url = f"{nango_oauth_url}?{param_string}"
            
            return {"oauth_url": full_url}
        
        @app.get("/oauth/callback")
        async def oauth_callback(code: str, state: str = None, connection_id: str = None):
            """Handle OAuth callback"""
            try:
                # Nango handles the token exchange automatically
                # We just need to verify the connection was created
                if connection_id:
                    client = await self.get_client(connection_id)
                    if await client.test_connection():
                        return {"status": "success", "message": "OAuth flow completed successfully"}
                
                return {"status": "error", "message": "Failed to establish connection"}
                
            except Exception as e:
                logger.error(f"OAuth callback error: {e}")
                raise HTTPException(status_code=400, detail=str(e))
        
        @app.post("/webhook/{connection_id}")
        async def handle_webhook(
            connection_id: str,
            payload: WebhookPayload,
            background_tasks: BackgroundTasks
        ):
            """Handle incoming webhooks"""
            background_tasks.add_task(self.process_webhook, connection_id, payload)
            return {"status": "accepted"}
        
        # Add integration-specific routes
        self.add_integration_routes(app)
    
    def add_integration_routes(self, app: FastAPI) -> None:
        """Add integration-specific routes - to be overridden by subclasses"""
        pass
    
    async def get_client(self, connection_id: str) -> BaseAPIClient:
        """Get or create API client for connection"""
        if connection_id not in self.active_connections:
            client = self.client_class(
                connection_id=connection_id,
                nango_public_key=self.nango_public_key,
                provider_config_key=self.provider
            )
            self.active_connections[connection_id] = client
        
        return self.active_connections[connection_id]
    
    async def process_webhook(self, connection_id: str, payload: WebhookPayload) -> None:
        """Process webhook payload - to be overridden by subclasses"""
        logger.info(
            "Webhook received",
            connection_id=connection_id,
            event=payload.event
        )
    
    async def cleanup_connections(self) -> None:
        """Clean up active connections"""
        for client in self.active_connections.values():
            if hasattr(client, '__aexit__'):
                try:
                    await client.__aexit__(None, None, None)
                except:
                    pass
        
        self.active_connections.clear()
    
    def run(self, host: str = "0.0.0.0", port: int = 8000, **kwargs):
        """Run the server"""
        uvicorn.run(
            self.app,
            host=host,
            port=port,
            log_config=None,  # Use our structured logging
            **kwargs
        )

# Utility functions for creating standardized responses
def success_response(data: Any, message: str = "Success") -> Dict[str, Any]:
    """Create standardized success response"""
    return {
        "success": True,
        "message": message,
        "data": data,
        "timestamp": datetime.now().isoformat()
    }

def error_response(error: str, message: str = None, status_code: int = 400) -> HTTPException:
    """Create standardized error response"""
    return HTTPException(
        status_code=status_code,
        detail={
            "success": False,
            "error": error,
            "message": message or error,
            "timestamp": datetime.now().isoformat()
        }
    )

async def proxy_request(client: BaseAPIClient, method: str, endpoint: str, data: Dict = None, params: Dict = None) -> Dict[str, Any]:
    """Proxy request to external API through client"""
    try:
        if method.upper() == "GET":
            response = await client.get(endpoint, params=params)
        elif method.upper() == "POST":
            response = await client.post(endpoint, data=data)
        elif method.upper() == "PUT":
            response = await client.put(endpoint, data=data)
        elif method.upper() == "PATCH":
            response = await client.patch(endpoint, data=data)
        elif method.upper() == "DELETE":
            response = await client.delete(endpoint)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        if response.success:
            return success_response(response.data)
        else:
            raise error_response(
                error="API Error",
                message=response.error_message,
                status_code=response.status_code
            )
            
    except Exception as e:
        logger.error(f"Proxy request failed: {e}")
        raise error_response(
            error="Proxy Error",
            message=str(e),
            status_code=500
        )

# Example usage in integration-specific server
if __name__ == "__main__":
    # This would be implemented by the specific integration
    pass