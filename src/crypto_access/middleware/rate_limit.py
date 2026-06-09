import time
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import render
import logging

logger = logging.getLogger(__name__)

class GlobalRateLimitMiddleware:
    """
    Middleware to rate limit requests globally per IP address.
    Limit: 60 requests per minute per IP.
    """
    RATE_LIMIT = 60
    RATE_LIMIT_WINDOW = 60  # seconds

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Exclude static files and media
        if request.path.startswith('/static/') or request.path.startswith('/media/') or request.path.startswith('/health/'):
            return self.get_response(request)

        # Get client IP
        ip = self.get_client_ip(request)
        if ip:
            cache_key = f"rate_limit_{ip}"
            
            # We use a simple counter with expiration
            # Since memcached/redis add/incr operations are atomic
            try:
                # Get current count
                count = cache.get(cache_key)
                if count is None:
                    cache.set(cache_key, 1, self.RATE_LIMIT_WINDOW)
                else:
                    if count >= self.RATE_LIMIT:
                        logger.warning(f"Rate limit exceeded for IP: {ip}")
                        # Return 429
                        return self.handle_rate_limit_exceeded(request)
                    
                    # Increment counter
                    try:
                        cache.incr(cache_key)
                    except ValueError:
                        # Fallback if incr fails
                        cache.set(cache_key, count + 1, self.RATE_LIMIT_WINDOW)
            except Exception as e:
                # If cache fails (e.g. Redis down), allow request but log error
                logger.error(f"Rate limiting cache error: {e}")

        response = self.get_response(request)
        return response

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def handle_rate_limit_exceeded(self, request):
        if request.path.startswith('/api/') or request.headers.get('Accept') == 'application/json':
            return JsonResponse({
                'error': 'Too many requests. Please try again later.'
            }, status=429)
        else:
            return render(request, 'errors/429.html', status=429)
