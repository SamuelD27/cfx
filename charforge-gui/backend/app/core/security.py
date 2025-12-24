"""Security middleware and utilities for CharForge GUI."""

import time
from collections import defaultdict
from typing import Dict, Optional
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

class RateLimiter:
    """Simple in-memory rate limiter."""
    
    def __init__(self):
        self.requests: Dict[str, list] = defaultdict(list)
        self.limits = {
            "auth": (50, 300),      # 50 requests per 5 minutes for auth endpoints
            "upload": (100, 60),    # 100 uploads per minute
            "training": (100, 3600), # 100 training sessions per hour (increased for development)
            "inference": (200, 300), # 200 inference requests per 5 minutes
            "default": (1000, 60)   # 1000 requests per minute for other endpoints
        }
    
    def is_allowed(self, identifier: str, endpoint_type: str = "default") -> bool:
        """Check if request is allowed based on rate limits."""
        now = time.time()
        limit, window = self.limits.get(endpoint_type, self.limits["default"])
        
        # Clean old requests
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier]
            if now - req_time < window
        ]
        
        # Check if limit exceeded
        if len(self.requests[identifier]) >= limit:
            return False
        
        # Add current request
        self.requests[identifier].append(now)
        return True

# Global rate limiter instance
rate_limiter = RateLimiter()

async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware."""
    # Get client identifier (IP address)
    client_ip = request.client.host
    
    # Determine endpoint type
    path = request.url.path
    endpoint_type = "default"
    
    if "/auth/" in path:
        endpoint_type = "auth"
    elif "/media/upload" in path:
        endpoint_type = "upload"
    elif "/training/" in path and request.method == "POST":
        endpoint_type = "training"
    elif "/inference/" in path and request.method == "POST":
        endpoint_type = "inference"
    
    # Check rate limit
    if not rate_limiter.is_allowed(client_ip, endpoint_type):
        logger.warning(f"Rate limit exceeded for {client_ip} on {path}")
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": "Rate limit exceeded. Please try again later."}
        )
    
    response = await call_next(request)
    return response

def validate_file_upload(file_content: bytes, filename: str, max_size: int = 50 * 1024 * 1024) -> bool:
    """Validate uploaded file for security."""

    # For partial content validation, we only check the first chunk
    # The max_size check is done during streaming in the upload handler

    # Check for malicious file signatures
    malicious_signatures = [
        b'\x4D\x5A',  # PE executable
        b'\x7F\x45\x4C\x46',  # ELF executable
        b'\xCA\xFE\xBA\xBE',  # Java class file
        b'\x50\x4B\x03\x04',  # ZIP file (could contain malicious content)
        b'\x00\x00\x01\x00',  # ICO file (could be disguised executable)
    ]

    for signature in malicious_signatures:
        if file_content.startswith(signature):
            return False

    # Check for valid image signatures
    valid_image_signatures = [
        b'\xFF\xD8\xFF',  # JPEG
        b'\x89\x50\x4E\x47',  # PNG
        b'\x47\x49\x46\x38',  # GIF
        b'\x52\x49\x46\x46',  # WebP (RIFF)
        b'\x42\x4D',  # BMP
    ]

    is_valid_image = any(file_content.startswith(sig) for sig in valid_image_signatures)
    if not is_valid_image:
        return False

    # Additional filename validation
    allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']
    file_ext = filename.lower().split('.')[-1] if '.' in filename else ''
    if f'.{file_ext}' not in allowed_extensions:
        return False

    return True

def sanitize_sql_input(value: str) -> str:
    """Sanitize input to prevent SQL injection."""
    if not isinstance(value, str):
        return str(value)
    
    # Remove or escape dangerous SQL characters
    dangerous_chars = ["'", '"', ';', '--', '/*', '*/', 'xp_', 'sp_']
    sanitized = value
    
    for char in dangerous_chars:
        sanitized = sanitized.replace(char, '')
    
    return sanitized.strip()

def validate_json_input(data: dict, max_depth: int = 10, max_keys: int = 100) -> bool:
    """Validate JSON input to prevent DoS attacks."""
    
    def count_depth(obj, current_depth=0):
        if current_depth > max_depth:
            return False
        
        if isinstance(obj, dict):
            if len(obj) > max_keys:
                return False
            return all(count_depth(v, current_depth + 1) for v in obj.values())
        elif isinstance(obj, list):
            if len(obj) > max_keys:
                return False
            return all(count_depth(item, current_depth + 1) for item in obj)
        
        return True
    
    return count_depth(data)

class SecurityHeaders:
    """Security headers middleware."""
    
    @staticmethod
    def add_security_headers(response):
        """Add security headers to response."""
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        return response

async def security_headers_middleware(request: Request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)
    return SecurityHeaders.add_security_headers(response)

def log_security_event(event_type: str, details: dict, request: Request):
    """Log security-related events."""
    logger.warning(f"Security Event: {event_type}", extra={
        "event_type": event_type,
        "client_ip": request.client.host,
        "user_agent": request.headers.get("user-agent", ""),
        "path": request.url.path,
        "details": details
    })
