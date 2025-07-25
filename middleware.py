"""
Middleware for API integrations
Handles authentication, rate limiting, caching, and request/response transformation
"""

import asyncio
import json
import time
import hashlib
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime, timedelta
from functools import wraps
import logging

import structlog
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse

logger = structlog.get_logger(__name__)

class CacheManager:
    """In-memory cache manager with TTL support"""
    
    def __init__(self, default_ttl: int = 300):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl
        self.lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get cached value"""
        async with self.lock:
            if key in self.cache:
                entry = self.cache[key]
                if datetime.now() < entry['expires_at']:
                    logger.debug(f"Cache hit for key: {key}")
                    return entry['value']
                else:
                    # Expired, remove from cache
                    del self.cache[key]
                    logger.debug(f"Cache expired for key: {key}")
            
            logger.debug(f"Cache miss for key: {key}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set cached value with TTL"""
        async with self.lock:
            expires_at = datetime.now() + timedelta(seconds=ttl or self.default_ttl)
            self.cache[key] = {
                'value': value,
                'expires_at': expires_at
            }
            logger.debug(f"Cached value for key: {key}, expires at: {expires_at}")
    
    async def delete(self, key: str) -> None:
        """Delete cached value"""
        async with self.lock:
            if key in self.cache:
                del self.cache[key]
                logger.debug(f"Deleted cache key: {key}")
    
    async def clear(self) -> None:
        """Clear all cached values"""
        async with self.lock:
            self.cache.clear()
            logger.info("Cache cleared")
    
    def _make_key(self, *args) -> str:
        """Create cache key from arguments"""
        key_data = json.dumps(args, sort_keys=True, default=str)
        return hashlib.md5(key_data.encode()).hexdigest()

class RequestTransformer:
    """Transform requests for different API formats"""
    
    @staticmethod
    def transform_slack_request(data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform request for Slack API format"""
        # Example transformations
        if 'message' in data:
            data['text'] = data.pop('message')
        
        if 'channel_name' in data:
            data['channel'] = f"#{data.pop('channel_name')}"
        
        return data
    
    @staticmethod
    def transform_github_request(data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform request for GitHub API format"""
        # GitHub-specific transformations
        if 'description' in data and 'body' not in data:
            data['body'] = data['description']
        
        return data
    
    @staticmethod
    def transform_generic_request(data: Dict[str, Any], provider: str) -> Dict[str, Any]:
        """Generic request transformation based on provider"""
        transformers = {
            'slack': RequestTransformer.transform_slack_request,
            'github': RequestTransformer.transform_github_request,
        }
        
        transformer = transformers.get(provider, lambda x: x)
        return transformer(data)

class ResponseTransformer:
    """Transform responses to standardized format"""
    
    @staticmethod
    def transform_slack_response(data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Slack API response"""
        if 'ok' in data:
            return {
                'success': data['ok'],
                'data': {k: v for k, v in data.items() if k != 'ok'},
                'provider': 'slack'
            }
        return data
    
    @staticmethod
    def transform_github_response(data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform GitHub API response"""
        # Standardize GitHub response format
        return {
            'success': True,
            'data': data,
            'provider': 'github'
        }
    
    @staticmethod
    def transform_generic_response(data: Dict[str, Any], provider: str) -> Dict[str, Any]:
        """Generic response transformation"""
        transformers = {
            'slack': ResponseTransformer.transform_slack_response,
            'github': ResponseTransformer.transform_github_response,
        }
        
        transformer = transformers.get(provider, lambda x: {'success': True, 'data': x, 'provider': provider})
        return transformer(data)

class IntegrationMiddleware:
    """Main middleware class for integrations"""
    
    def __init__(
        self,
        provider: str,
        cache_ttl: int = 300,
        enable_request_logging: bool = True,
        enable_response_caching: bool = True,
        max_request_size: int = 10 * 1024 * 1024  # 10MB
    ):
        self.provider = provider
        self.cache_manager = CacheManager(default_ttl=cache_ttl)
        self.enable_request_logging = enable_request_logging
        self.enable_response_caching = enable_response_caching
        self.max_request_size = max_request_size
        
        # Request/response transformers
        self.request_transformer = RequestTransformer()
        self.response_transformer = ResponseTransformer()
        
        # Metrics
        self.request_count = 0
        self.error_count = 0
        self.cache_hits = 0
        self.cache_misses = 0
    
    def cache_key(self, method: str, endpoint: str, params: Dict = None, data: Dict = None) -> str:
        """Generate cache key for request"""
        return self.cache_manager._make_key(method, endpoint, params or {}, data or {})
    
    async def process_request(self, request: Request) -> Optional[Dict[str, Any]]:
        """Process incoming request"""
        self.request_count += 1
        
        # Check request size
        if hasattr(request, 'headers') and 'content-length' in request.headers:
            content_length = int(request.headers['content-length'])
            if content_length > self.max_request_size:
                raise HTTPException(status_code=413, detail="Request too large")
        
        # Log request if enabled
        if self.enable_request_logging:
            logger.info(
                "Processing request",
                method=request.method,
                url=str(request.url),
                provider=self.provider,
                user_agent=request.headers.get('user-agent'),
                request_id=request.headers.get('x-request-id')
            )
        
        return None
    
    async def process_response(
        self,
        response_data: Dict[str, Any],
        method: str,
        endpoint: str,
        cache_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process outgoing response"""
        
        # Transform response format
        transformed_data = self.response_transformer.transform_generic_response(
            response_data, self.provider
        )
        
        # Cache response if enabled and method is GET
        if self.enable_response_caching and method.upper() == "GET" and cache_key:
            await self.cache_manager.set(cache_key, transformed_data)
        
        # Log response if enabled
        if self.enable_request_logging:
            logger.info(
                "Response processed",
                provider=self.provider,
                endpoint=endpoint,
                success=transformed_data.get('success', True)
            )
        
        return transformed_data
    
    async def handle_cached_response(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Check for cached response"""
        if not self.enable_response_caching:
            return None
        
        cached_response = await self.cache_manager.get(cache_key)
        if cached_response:
            self.cache_hits += 1
            logger.debug("Returning cached response", cache_key=cache_key)
            return cached_response
        
        self.cache_misses += 1
        return None
    
    async def transform_request_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform request data for the specific provider"""
        return self.request_transformer.transform_generic_request(data, self.provider)
    
    async def handle_error(self, error: Exception, request_context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle and transform errors"""
        self.error_count += 1
        
        error_response = {
            'success': False,
            'error': type(error).__name__,
            'message': str(error),
            'provider': self.provider,
            'timestamp': datetime.now().isoformat()
        }
        
        # Log error
        logger.error(
            "Request error",
            error=str(error),
            provider=self.provider,
            **request_context,
            exc_info=True
        )
        
        return error_response
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get middleware metrics"""
        cache_hit_rate = self.cache_hits / max(1, self.cache_hits + self.cache_misses)
        error_rate = self.error_count / max(1, self.request_count)
        
        return {
            'provider': self.provider,
            'total_requests': self.request_count,
            'total_errors': self.error_count,
            'error_rate': error_rate,
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'cache_hit_rate': cache_hit_rate
        }

# Decorator for applying middleware to endpoints
def with_integration_middleware(provider: str, cache_ttl: int = 300):
    """Decorator to apply middleware to endpoint functions"""
    
    def decorator(func: Callable) -> Callable:
        middleware = IntegrationMiddleware(provider, cache_ttl=cache_ttl)
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request object
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                # If no request object found, proceed without middleware
                return await func(*args, **kwargs)
            
            try:
                # Process request
                await middleware.process_request(request)
                
                # Check cache for GET requests
                if request.method == "GET":
                    cache_key = middleware.cache_key(
                        request.method,
                        str(request.url.path),
                        dict(request.query_params)
                    )
                    
                    cached_response = await middleware.handle_cached_response(cache_key)
                    if cached_response:
                        return cached_response
                
                # Execute original function
                result = await func(*args, **kwargs)
                
                # Process response
                if isinstance(result, dict):
                    processed_result = await middleware.process_response(
                        result,
                        request.method,
                        str(request.url.path),
                        cache_key if request.method == "GET" else None
                    )
                    return processed_result
                
                return result
                
            except Exception as e:
                # Handle error
                error_response = await middleware.handle_error(e, {
                    'method': request.method,
                    'url': str(request.url),
                    'args': str(args),
                    'kwargs': str(kwargs)
                })
                
                return JSONResponse(
                    status_code=500,
                    content=error_response
                )
        
        # Attach middleware instance to function for metrics access
        wrapper.middleware = middleware
        return wrapper
    
    return decorator

# Health check middleware
class HealthCheckMiddleware:
    """Middleware for health checks and monitoring"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.health_checks = {}
    
    async def check_api_health(self, client, provider: str) -> Dict[str, Any]:
        """Check API health"""
        try:
            is_healthy = await client.health_check()
            
            health_status = {
                'provider': provider,
                'status': 'healthy' if is_healthy else 'unhealthy',
                'timestamp': datetime.now().isoformat(),
                'response_time_ms': None  # Could add timing here
            }
            
            self.health_checks[provider] = health_status
            return health_status
            
        except Exception as e:
            health_status = {
                'provider': provider,
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            
            self.health_checks[provider] = health_status
            return health_status
    
    def get_overall_health(self) -> Dict[str, Any]:
        """Get overall system health"""
        uptime = (datetime.now() - self.start_time).total_seconds()
        
        healthy_count = sum(1 for check in self.health_checks.values() 
                          if check.get('status') == 'healthy')
        total_count = len(self.health_checks)
        
        overall_status = 'healthy' if healthy_count == total_count else 'degraded'
        if healthy_count == 0 and total_count > 0:
            overall_status = 'unhealthy'
        
        return {
            'status': overall_status,
            'uptime_seconds': uptime,
            'checks': self.health_checks,
            'healthy_services': healthy_count,
            'total_services': total_count,
            'timestamp': datetime.now().isoformat()
        }

# Rate limiting middleware
class RateLimitMiddleware:
    """Rate limiting middleware with different strategies"""
    
    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        burst_size: int = 10
    ):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.burst_size = burst_size
        
        # Track requests per IP/user
        self.request_counts = {}
        self.lock = asyncio.Lock()
    
    async def is_rate_limited(self, identifier: str) -> tuple[bool, Dict[str, Any]]:
        """Check if request should be rate limited"""
        async with self.lock:
            now = datetime.now()
            
            if identifier not in self.request_counts:
                self.request_counts[identifier] = {
                    'minute_requests': [],
                    'hour_requests': [],
                    'burst_requests': []
                }
            
            user_data = self.request_counts[identifier]
            
            # Clean old requests
            minute_ago = now - timedelta(minutes=1)
            hour_ago = now - timedelta(hours=1)
            burst_window = now - timedelta(seconds=10)
            
            user_data['minute_requests'] = [
                req_time for req_time in user_data['minute_requests']
                if req_time > minute_ago
            ]
            user_data['hour_requests'] = [
                req_time for req_time in user_data['hour_requests']
                if req_time > hour_ago
            ]
            user_data['burst_requests'] = [
                req_time for req_time in user_data['burst_requests']
                if req_time > burst_window
            ]
            
            # Check limits
            minute_count = len(user_data['minute_requests'])
            hour_count = len(user_data['hour_requests'])
            burst_count = len(user_data['burst_requests'])
            
            # Rate limit info
            rate_limit_info = {
                'requests_remaining_minute': max(0, self.requests_per_minute - minute_count),
                'requests_remaining_hour': max(0, self.requests_per_hour - hour_count),
                'requests_remaining_burst': max(0, self.burst_size - burst_count),
                'reset_minute': (minute_ago + timedelta(minutes=1)).isoformat(),
                'reset_hour': (hour_ago + timedelta(hours=1)).isoformat()
            }
            
            # Check if rate limited
            if (minute_count >= self.requests_per_minute or 
                hour_count >= self.requests_per_hour or 
                burst_count >= self.burst_size):
                return True, rate_limit_info
            
            # Add current request
            user_data['minute_requests'].append(now)
            user_data['hour_requests'].append(now)
            user_data['burst_requests'].append(now)
            
            return False, rate_limit_info

# Usage example
def create_middleware_stack(provider: str) -> List[Callable]:
    """Create a complete middleware stack for an integration"""
    
    middleware_stack = []
    
    # Rate limiting
    rate_limiter = RateLimitMiddleware()
    
    # Health checking
    health_checker = HealthCheckMiddleware()
    
    # Integration-specific middleware
    integration_middleware = IntegrationMiddleware(provider)
    
    return [rate_limiter, health_checker, integration_middleware]