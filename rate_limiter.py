"""
Token bucket rate limiter for API calls.
"""
import asyncio
import time
from collections import deque
from typing import Optional
from threading import Lock
from loguru import logger

class RateLimiter:
    """Token bucket rate limiter implementation."""
    
    def __init__(self, requests_per_second: int = 5, burst_size: int = 10):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_second: Maximum requests per second
            burst_size: Maximum burst size
        """
        self.requests_per_second = requests_per_second
        self.burst_size = burst_size
        self.tokens = burst_size
        self.last_refill = time.time()
        self.lock = asyncio.Lock()
        self.request_history = deque(maxlen=100)
        self.total_requests = 0
        self.failed_requests = 0
    
    async def acquire(self) -> bool:
        """
        Acquire a token from the bucket.
        
        Returns:
            True if token was acquired
            
        Raises:
            asyncio.TimeoutError: If timeout waiting for token
        """
        async with self.lock:
            self._refill_tokens()
            
            if self.tokens >= 1:
                self.tokens -= 1
                self.total_requests += 1
                self.request_history.append(time.time())
                return True
            
            # Calculate wait time
            wait_time = (1.0 / self.requests_per_second)
            logger.debug(f"Rate limited, waiting {wait_time:.2f}s")
            
            # Release lock and wait
        await asyncio.sleep(wait_time)
        
        # Try again recursively
        return await self.acquire()
    
    def _refill_tokens(self):
        """Refill tokens based on time elapsed."""
        now = time.time()
        elapsed = now - self.last_refill
        
        # Add tokens based on elapsed time
        new_tokens = elapsed * self.requests_per_second
        self.tokens = min(self.burst_size, self.tokens + new_tokens)
        self.last_refill = now
    
    def get_stats(self) -> dict:
        """
        Get rate limiter statistics.
        
        Returns:
            Dictionary with statistics
        """
        if self.request_history:
            recent_requests = list(self.request_history)[-10:]
            if recent_requests:
                time_span = time.time() - recent_requests[0]
                current_rate = len(recent_requests) / time_span if time_span > 0 else 0
            else:
                current_rate = 0
        else:
            current_rate = 0
        
        return {
            "total_requests": self.total_requests,
            "failed_requests": self.failed_requests,
            "current_tokens": self.tokens,
            "current_rate": round(current_rate, 2),
            "max_rate": self.requests_per_second
        }
    
    def record_failure(self):
        """Record a failed request."""
        self.failed_requests += 1
    
    def reset(self):
        """Reset the rate limiter."""
        self.tokens = self.burst_size
        self.last_refill = time.time()
        self.request_history.clear()
        self.total_requests = 0
        self.failed_requests = 0