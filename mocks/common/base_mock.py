# File: mocks/common/base_mock.py
# Base Mock Server with standard patterns and best practices

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pydantic_settings import BaseSettings


class MockConfig(BaseSettings):
    """
    Base configuration for all mock servers

    Environment variables can override defaults:
    - MOCK_HOST: Server host
    - MOCK_PORT: Server port
    - MOCK_LOG_LEVEL: Logging level
    - MOCK_RESPONSE_DELAY_MS: Artificial delay in milliseconds
    - MOCK_ERROR_RATE: Random error rate (0.0 to 1.0)
    """

    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    enable_cors: bool = True
    response_delay_ms: int = 0
    error_rate: float = 0.0

    class Config:
        env_prefix = "MOCK_"


class HealthResponse(BaseModel):
    """Standard health check response"""
    status: str
    timestamp: str
    service_name: str
    version: str


class ErrorResponse(BaseModel):
    """Standard error response following RFC 7807"""
    error: str
    message: str
    timestamp: str
    details: Optional[Dict[str, Any]] = None


class BaseMockServer(ABC):
    """
    Abstract base class for all mock servers

    Provides:
    - Standard FastAPI app configuration
    - CORS middleware
    - Health check endpoint
    - Error simulation support
    - Logging configuration
    - Response delay simulation

    Usage:
        class MyMock(BaseMockServer):
            def __init__(self):
                super().__init__(
                    title="My Mock API",
                    description="Mock server for testing",
                    version="1.0.0"
                )
                self._setup_routes()

            def _setup_routes(self):
                @self.app.get("/my-endpoint")
                async def my_endpoint():
                    return {"data": "example"}
    """

    def __init__(
        self,
        title: str,
        description: str,
        version: str = "1.0.0",
        config: Optional[MockConfig] = None
    ):
        """
        Initialize base mock server

        Args:
            title: API title for OpenAPI docs
            description: API description
            version: API version
            config: Optional custom configuration
        """
        self.config = config or MockConfig()
        self.title = title
        self.description = description
        self.version = version

        # Configure logging
        self._setup_logging()

        # Create FastAPI app
        self.app = FastAPI(
            title=title,
            description=description,
            version=version,
            docs_url="/docs",
            redoc_url="/redoc",
            openapi_url="/openapi.json"
        )

        # Add CORS middleware
        if self.config.enable_cors:
            self._add_cors()

        # Add standard endpoints
        self._add_health_endpoint()

        self.logger.info(
            "Mock server initialized: %s v%s",
            title,
            version
        )

    def _setup_logging(self):
        """Configure logging for the mock server"""
        logging.basicConfig(
            level=getattr(logging, self.config.log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(self.__class__.__name__)

    def _add_cors(self):
        """Add CORS middleware for development"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        self.logger.info("CORS enabled for all origins")

    def _add_health_endpoint(self):
        """Add standard health check endpoint"""
        @self.app.get("/health", response_model=HealthResponse)
        async def health_check():
            """
            Health check endpoint

            Returns service status and basic information
            """
            return HealthResponse(
                status="healthy",
                timestamp=datetime.utcnow().isoformat(),
                service_name=self.title,
                version=self.version
            )

        self.logger.debug("Health check endpoint registered at /health")

    def check_error_simulation(
        self,
        simulate_error: Optional[int] = Query(
            None,
            description="Simulate HTTP error (e.g., 404, 500)",
            example=500
        )
    ) -> None:
        """
        Check if error simulation is requested

        Use as a dependency in routes:
            @app.get("/endpoint")
            async def endpoint(error_check = Depends(self.check_error_simulation)):
                # endpoint logic

        Args:
            simulate_error: HTTP status code to simulate

        Raises:
            HTTPException: If error simulation is requested
        """
        if simulate_error:
            self.logger.warning("Simulating error: HTTP %d", simulate_error)
            error_messages = {
                400: "Bad Request - simulated error",
                401: "Unauthorized - simulated error",
                403: "Forbidden - simulated error",
                404: "Not Found - simulated error",
                500: "Internal Server Error - simulated error",
                502: "Bad Gateway - simulated error",
                503: "Service Unavailable - simulated error",
            }
            raise HTTPException(
                status_code=simulate_error,
                detail={
                    "error": f"simulated_error_{simulate_error}",
                    "message": error_messages.get(
                        simulate_error,
                        f"Simulated error {simulate_error}"
                    ),
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

    @abstractmethod
    def _setup_routes(self):
        """
        Setup API routes

        Must be implemented by subclasses to define their specific endpoints
        """
        pass

    def run(self, host: Optional[str] = None, port: Optional[int] = None):
        """
        Run the mock server

        Args:
            host: Override configured host
            port: Override configured port
        """
        import uvicorn

        run_host = host or self.config.host
        run_port = port or self.config.port

        self.logger.info(
            "Starting %s on http://%s:%d",
            self.title,
            run_host,
            run_port
        )
        self.logger.info("OpenAPI docs: http://%s:%d/docs", run_host, run_port)

        uvicorn.run(
            self.app,
            host=run_host,
            port=run_port,
            log_level=self.config.log_level.lower()
        )
