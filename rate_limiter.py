"""Simple rate limiting implementation."""
from collections import defaultdict, deque
from time import time
from typing import Dict
from config import config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RateLimiter:
    """
    Simple in-memory rate limiter using sliding window approach.
    
    For production, consider using Redis-based rate limiting.
    """
    
    def __init__(self, max_requests: int = None, window_seconds: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests or config.RATE_LIMIT_PER_MINUTE
        self.window_seconds = window_seconds
        self.requests: Dict[str, deque] = defaultdict(deque)
    
    def is_allowed(self, client_id: str) -> bool:
        """
        Check if request from client is allowed.
        
        Args:
            client_id: Unique identifier for client (e.g., IP address)
            
        Returns:
            True if request is allowed, False if rate limit exceeded
        """
        now = time()
        client_requests = self.requests[client_id]
        
        # Remove old requests outside the window
        while client_requests and client_requests[0] < now - self.window_seconds:
            client_requests.popleft()
        
        # Check if limit exceeded
        if len(client_requests) >= self.max_requests:
            logger.warning(f"Rate limit exceeded for client: {client_id}")
            return False
        
        # Add current request
        client_requests.append(now)
        return True
    
    def get_remaining(self, client_id: str) -> int:
        """
        Get remaining requests for client.
        
        Args:
            client_id: Client identifier
            
        Returns:
            Number of remaining requests
        """
        now = time()
        client_requests = self.requests[client_id]
        
        # Remove old requests
        while client_requests and client_requests[0] < now - self.window_seconds:
            client_requests.popleft()
        
        return max(0, self.max_requests - len(client_requests))
    
    def reset(self, client_id: str):
        """Reset rate limit for a client."""
        if client_id in self.requests:
            del self.requests[client_id]
            logger.info(f"Reset rate limit for client: {client_id}")
    
    def cleanup_old_entries(self):
        """Remove old entries to prevent memory growth."""
        now = time()
        clients_to_remove = []
        
        for client_id, requests in self.requests.items():
            # Remove old timestamps
            while requests and requests[0] < now - self.window_seconds:
                requests.popleft()
            
            # If no recent requests, mark for removal
            if not requests:
                clients_to_remove.append(client_id)
        
        for client_id in clients_to_remove:
            del self.requests[client_id]
        
        if clients_to_remove:
            logger.info(f"Cleaned up {len(clients_to_remove)} inactive clients")

# Global instance
_rate_limiter = None

def get_rate_limiter() -> RateLimiter:
    """Get or create the global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter
