"""
Base client class for all API integrations
Provides common functionality for OAuth, rate limiting, and error handling
"""

import asyncio
import time
import json
import logging
from typing import Dict, Any, Optional, List, Union
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta

import aiohttp
from aiohttp import ClientSession, ClientTimeout, ClientError
import structlog

logger = structlog.get_logger(__name__)

@dataclass
class APIResponse:
    """Standardized API response wrapper"""
    status_code: int
    data: Optional[Dict[str, Any]]
    headers: Dict[str, str]
    success: bool
    error_message: Optional[str] = None
    rate_limit_remaining: Optional[int] = None
    rate_limit_reset: Optional[datetime] = None

@dataclass 
class RateLimitConfig:
    """Rate limiting configuration"""
    requests_per_minute: int = 60
    requests_per_second: int = 10
    burst_limit: int = 5
    backoff_multiplier: float = 1.5
    max_retries: int = 3

class TokenManager:
    """Manages OAuth tokens using Nango"""
    
    def __init__(self, nango_public_key: str, connection_id: str, provider_config_key: str):
        self.nango_public_key = nango_public_key
        self.connection_id = connection_id
        self.provider_config_key = provider_config_key
        self.base_url = "https://api.nango.dev"
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        
    async def get_access_token(self) -> str:
        """Get valid access token, refreshing if necessary"""
        if self._access_token and self._token_expires_at:
            if datetime.now() < self._token_expires_at - timedelta(minutes=5):
                return self._access_token
        
        await self._refresh_token()
        return self._access_token
    
    async def _refresh_token(self) -> None:
        """Refresh access token from Nango"""
        headers = {
            "Authorization": f"Bearer {self.nango_public_key}",
            "Provider-Config-Key": self.provider_config_key,
            "Connection-Id": self.connection_id
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/connection/{self.connection_id}",
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    credentials = data.get("credentials", {})
                    self._access_token = credentials.get("access_token")
                    
                    # Set expiration (default to 1 hour if not provided)
                    expires_in = credentials.get("expires_in", 3600)
                    self._token_expires_at = datetime.now() + timedelta(seconds=expires_in)
                    
                    logger.info("Access token refreshed successfully")
                else:
                    error_text = await response.text()
                    raise Exception(f"Failed to refresh token: {error_text}")

class RateLimiter:
    """Token bucket rate limiter"""
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.tokens = config.burst_limit
        self.last_update = time.time()
        self.lock = asyncio.Lock()
    
    async def acquire(self) -> bool:
        """Acquire a rate limit token"""
        async with self.lock:
            now = time.time()
            
            # Add tokens based on time passed
            time_passed = now - self.last_update
            tokens_to_add = time_passed * (self.config.requests_per_second)
            self.tokens = min(self.config.burst_limit, self.tokens + tokens_to_add)
            self.last_update = now
            
            if self.tokens >= 1:
                self.tokens -= 1
                return True
            return False
    
    async def wait_for_token(self) -> None:
        """Wait until a token is available"""
        while not await self.acquire():
            await asyncio.sleep(0.1)

class BaseAPIClient(ABC):
    """Base class for all API integrations"""
    
    def __init__(
        self,
        connection_id: str,
        nango_public_key: str,
        provider_config_key: str,
        base_url: str,
        rate_limit_config: Optional[RateLimitConfig] = None
    ):
        self.connection_id = connection_id
        self.base_url = base_url.rstrip('/')
        self.provider_config_key = provider_config_key
        
        # Initialize components
        self.token_manager = TokenManager(nango_public_key, connection_id, provider_config_key)
        self.rate_limiter = RateLimiter(rate_limit_config or RateLimitConfig())
        
        # Session configuration
        self.timeout = ClientTimeout(total=30, connect=10)
        self._session: Optional[ClientSession] = None
        
        # Request tracking
        self.request_count = 0
        self.error_count = 0
        
    async def __aenter__(self):
        """Async context manager entry"""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def _ensure_session(self) -> None:
        """Ensure HTTP session is available"""
        if not self._session or self._session.closed:
            connector = aiohttp.TCPConnector(
                limit=100,
                limit_per_host=30,
                ttl_dns_cache=300,
                use_dns_cache=True,
            )
            self._session = ClientSession(
                connector=connector,
                timeout=self.timeout,
                headers={"User-Agent": "Integration-Agent/1.0"}
            )
    
    async def _get_headers(self, additional_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Get request headers with authentication"""
        access_token = await self.token_manager.get_access_token()
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        if additional_headers:
            headers.update(additional_headers)
        
        return headers
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        retry_count: int = 0
    ) -> APIResponse:
        """Make HTTP request with rate limiting and error handling"""
        
        # Apply rate limiting
        await self.rate_limiter.wait_for_token()
        
        # Ensure session exists
        await self._ensure_session()
        
        # Prepare request
        url = f"{self.base_url}{endpoint}"
        request_headers = await self._get_headers(headers)
        
        self.request_count += 1
        
        try:
            async with self._session.request(
                method=method,
                url=url,
                json=data,
                params=params,
                headers=request_headers
            ) as response:
                
                # Parse response
                response_headers = dict(response.headers)
                
                try:
                    response_data = await response.json()
                except:
                    response_data = {"raw_response": await response.text()}
                
                # Handle rate limiting
                if response.status == 429:
                    if retry_count < self.rate_limiter.config.max_retries:
                        retry_after = int(response_headers.get('Retry-After', 60))
                        logger.warning(f"Rate limited, waiting {retry_after} seconds")
                        await asyncio.sleep(retry_after)
                        return await self._make_request(method, endpoint, data, params, headers, retry_count + 1)
                    else:
                        self.error_count += 1
                        return APIResponse(
                            status_code=response.status,
                            data=response_data,
                            headers=response_headers,
                            success=False,
                            error_message="Rate limit exceeded, max retries reached"
                        )
                
                # Handle other errors
                if response.status >= 400:
                    self.error_count += 1
                    error_message = response_data.get('error', response_data.get('message', f'HTTP {response.status}'))
                    
                    # Retry on server errors
                    if response.status >= 500 and retry_count < self.rate_limiter.config.max_retries:
                        wait_time = (self.rate_limiter.config.backoff_multiplier ** retry_count)
                        logger.warning(f"Server error {response.status}, retrying in {wait_time} seconds")
                        await asyncio.sleep(wait_time)
                        return await self._make_request(method, endpoint, data, params, headers, retry_count + 1)
                    
                    return APIResponse(
                        status_code=response.status,
                        data=response_data,
                        headers=response_headers,
                        success=False,
                        error_message=error_message
                    )
                
                # Success response
                return APIResponse(
                    status_code=response.status,
                    data=response_data,
                    headers=response_headers,
                    success=True,
                    rate_limit_remaining=response_headers.get('X-RateLimit-Remaining'),
                    rate_limit_reset=self._parse_rate_limit_reset(response_headers.get('X-RateLimit-Reset'))
                )
                
        except ClientError as e:
            self.error_count += 1
            logger.error(f"HTTP client error: {e}")
            return APIResponse(
                status_code=0,
                data=None,
                headers={},
                success=False,
                error_message=f"Connection error: {str(e)}"
            )
        except Exception as e:
            self.error_count += 1
            logger.error(f"Unexpected error: {e}")
            return APIResponse(
                status_code=0,
                data=None,
                headers={},
                success=False,
                error_message=f"Unexpected error: {str(e)}"
            )
    
    def _parse_rate_limit_reset(self, reset_header: Optional[str]) -> Optional[datetime]:
        """Parse rate limit reset header"""
        if not reset_header:
            return None
        
        try:
            # Assume Unix timestamp
            timestamp = int(reset_header)
            return datetime.fromtimestamp(timestamp)
        except:
            return None
    
    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None, **kwargs) -> APIResponse:
        """Make GET request"""
        return await self._make_request("GET", endpoint, params=params, **kwargs)
    
    async def post(self, endpoint: str, data: Optional[Dict[str, Any]] = None, **kwargs) -> APIResponse:
        """Make POST request"""
        return await self._make_request("POST", endpoint, data=data, **kwargs)
    
    async def put(self, endpoint: str, data: Optional[Dict[str, Any]] = None, **kwargs) -> APIResponse:
        """Make PUT request"""
        return await self._make_request("PUT", endpoint, data=data, **kwargs)
    
    async def patch(self, endpoint: str, data: Optional[Dict[str, Any]] = None, **kwargs) -> APIResponse:
        """Make PATCH request"""
        return await self._make_request("PATCH", endpoint, data=data, **kwargs)
    
    async def delete(self, endpoint: str, **kwargs) -> APIResponse:
        """Make DELETE request"""
        return await self._make_request("DELETE", endpoint, **kwargs)
    
    async def health_check(self) -> bool:
        """Check if the API is accessible"""
        try:
            response = await self.get("/")
            return response.success or response.status_code in [200, 404]  # 404 is ok for root endpoint
        except:
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics"""
        return {
            "total_requests": self.request_count,
            "total_errors": self.error_count,
            "error_rate": self.error_count / max(1, self.request_count),
            "connection_id": self.connection_id,
            "provider": self.provider_config_key
        }
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """Test the API connection - must be implemented by subclasses"""
        pass