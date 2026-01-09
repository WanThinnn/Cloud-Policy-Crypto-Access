"""
Signals for crypto_access app.
"""

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.contrib.auth.models import User


@receiver(post_save, sender=User)
def user_created_handler(sender, instance, created, **kwargs):
    """Handle user creation events"""
    if created:
        # Add custom logic when user is created
        pass


@receiver(pre_delete, sender=User)
def user_deleted_handler(sender, instance, **kwargs):
    """Handle user deletion events"""
    # Add custom cleanup logic
    pass
