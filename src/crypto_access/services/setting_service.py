import logging
from django.core.cache import cache
from crypto_access.models import SystemSetting

logger = logging.getLogger(__name__)

class SettingService:
    """Service for managing dynamic system settings with caching."""
    
    CACHE_TIMEOUT = 300  # 5 minutes
    
    @classmethod
    def get_setting(cls, key: str, default_value=None):
        """
        Get a system setting value by key.
        Uses Redis cache for fast retrieval.
        """
        cache_key = f"system_setting_{key}"
        
        # Try to get from cache
        cached_value = cache.get(cache_key)
        if cached_value is not None:
            return cached_value
            
        # If not in cache, query database
        try:
            setting = SystemSetting.objects.get(key=key, is_active=True)
            value = setting.value
            
            # Save to cache
            cache.set(cache_key, value, timeout=cls.CACHE_TIMEOUT)
            return value
            
        except SystemSetting.DoesNotExist:
            logger.warning(f"System setting '{key}' not found or inactive. Using default.")
            return default_value
        except Exception as e:
            logger.error(f"Error retrieving system setting '{key}': {e}")
            return default_value

    @classmethod
    def invalidate_setting_cache(cls, key: str):
        """Invalidate the cache for a specific setting."""
        cache_key = f"system_setting_{key}"
        cache.delete(cache_key)
