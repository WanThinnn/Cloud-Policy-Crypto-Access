from django.apps import AppConfig


class CryptoAccessConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'crypto_access'
    verbose_name = 'Cloud Policy Crypto Access Management'

    def ready(self):
        """Import signals when app is ready"""
        import crypto_access.signals  # noqa
