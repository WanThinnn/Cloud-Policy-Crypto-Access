"""
Signals for crypto_access app.
Handles automatic key revocation when user attributes change (QĐ13)
"""

import logging
from django.db.models.signals import post_save, pre_save, pre_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models.settings import SystemSetting
from .services.setting_service import SettingService

logger = logging.getLogger(__name__)


@receiver(post_save, sender=SystemSetting)
@receiver(pre_delete, sender=SystemSetting)
def invalidate_setting_cache_handler(sender, instance, **kwargs):
    """Invalidate setting cache when a SystemSetting is modified or deleted."""
    SettingService.invalidate_setting_cache(instance.key)
    logger.info(f"Invalidated cache for system setting: {instance.key}")


@receiver(post_save, sender=User)
def user_created_handler(sender, instance, created, **kwargs):
    """Handle user creation events"""
    if created:
        # Add custom logic when user is created
        pass


@receiver(pre_delete, sender=User)
def user_deleted_handler(sender, instance, **kwargs):
    """Handle user deletion events - revoke all keys"""
    from .models import KeyRevocation, UserAttribute
    
    # Get user's current attributes
    old_attrs = UserAttribute.get_user_attributes(instance)
    
    # TODO: Get actual key_id from CP-ABE key management system
    # For now, generate a placeholder
    key_id = f"privkey_{instance.id}_placeholder"
    
    if old_attrs:
        # Create revocation record WITHOUT linking to user (since user will be deleted)
        # Store username in reason_detail for audit purposes
        KeyRevocation.objects.create(
            user=None,  # Don't link to user since it's being deleted
            key_id=key_id,
            reason='account_termination',
            old_attributes=old_attrs,
            new_attributes={},
            reason_detail=f'User account {instance.username} (ID: {instance.id}) deleted',
            status='completed'
        )
        logger.info(f"[KEY-REVOKE] User {instance.username} deleted - key revoked")


# =============================================================================
# UserAttribute Signals - Trigger key revocation on attribute changes
# =============================================================================

def get_user_attribute_model():
    """Lazy import to avoid circular imports"""
    from .models import UserAttribute
    return UserAttribute


def get_key_revocation_model():
    """Lazy import to avoid circular imports"""
    from .models import KeyRevocation
    return KeyRevocation


@receiver(pre_save)
def capture_old_attribute_value(sender, instance, **kwargs):
    """Capture old attribute value before save for comparison"""
    UserAttribute = get_user_attribute_model()
    
    if sender != UserAttribute:
        return
    
    if instance.pk:
        try:
            old_instance = UserAttribute.objects.get(pk=instance.pk)
            # Store on instance to avoid global dict memory leak
            instance._old_attr_data = {
                'value': old_instance.value,
                'status': old_instance.status,
                'user_id': old_instance.user_id,
                'attribute_name': old_instance.attribute.name if old_instance.attribute else None
            }
        except UserAttribute.DoesNotExist:
            pass


@receiver(post_save)
def handle_attribute_change(sender, instance, created, **kwargs):
    """
    Handle attribute changes - trigger key revocation if needed (QĐ13)
    
    When a user's ABAC attribute changes, their CP-ABE key must be revoked
    and a new key issued with updated attributes.
    """
    UserAttribute = get_user_attribute_model()
    KeyRevocation = get_key_revocation_model()
    
    if sender != UserAttribute:
        return
    
    if created:
        # New attribute added - may need to issue new key
        logger.info(
            f"[ATTR-ADD] New attribute for user {instance.user.username}: "
            f"{instance.attribute.name}={instance.value}"
        )
        return
    
    # Check if value actually changed
    old_data = getattr(instance, '_old_attr_data', None)
    if not old_data:
        return
    
    old_value = old_data.get('value')
    new_value = instance.value
    
    if old_value != new_value:
        logger.warning(
            f"[ATTR-CHANGE] User {instance.user.username}: "
            f"{instance.attribute.name} changed from '{old_value}' to '{new_value}'"
        )
        
        # Get all current attributes for the user
        old_attrs = UserAttribute.get_user_attributes(instance.user)
        old_attrs[instance.attribute.name] = old_value  # Use old value
        
        new_attrs = UserAttribute.get_user_attributes(instance.user)
        
        # TODO: Get actual key_id from CP-ABE key management system
        # For now, generate a placeholder based on user ID
        key_id = f"privkey_{instance.user.id}_placeholder"
        
        # Create revocation record
        KeyRevocation.revoke_user_key(
            user=instance.user,
            key_id=key_id,
            reason='attribute_change',
            old_attributes=old_attrs,
            new_attributes=new_attrs,
            reason_detail=f"{instance.attribute.name}: '{old_value}' -> '{new_value}'",
            revoked_by=instance.updated_by
        )
        
        logger.warning(
            f"[KEY-REVOKE] Key revoked for user {instance.user.username} "
            f"due to attribute change"
        )


@receiver(pre_delete)
def handle_attribute_deletion(sender, instance, **kwargs):
    """Handle attribute deletion - trigger key revocation"""
    UserAttribute = get_user_attribute_model()
    KeyRevocation = get_key_revocation_model()
    
    if sender != UserAttribute:
        return
    
    # Check if user still exists and is not being deleted
    # If user is being deleted, the user_deleted_handler will handle revocation
    try:
        user = instance.user
        if user is None or not User.objects.filter(pk=user.pk).exists():
            logger.info(f"[ATTR-DELETE] Skipping revocation - user is being deleted")
            return
    except User.DoesNotExist:
        return
    
    logger.warning(
        f"[ATTR-DELETE] Attribute {instance.attribute.name} deleted "
        f"for user {instance.user.username}"
    )
    
    # Get current attributes before deletion
    old_attrs = UserAttribute.get_user_attributes(instance.user)
    new_attrs = {k: v for k, v in old_attrs.items() if k != instance.attribute.name}
    
    # TODO: Get actual key_id from CP-ABE key management system
    key_id = f"privkey_{instance.user.id}_placeholder"
    
    KeyRevocation.revoke_user_key(
        user=instance.user,
        key_id=key_id,
        reason='attribute_change',
        old_attributes=old_attrs,
        new_attributes=new_attrs,
        reason_detail=f"Attribute '{instance.attribute.name}' removed"
    )
    
    logger.warning(
        f"[KEY-REVOKE] Key revoked for user {instance.user.username} "
        f"due to attribute deletion"
    )

# =============================================================================
# UserProfile Signals - Trigger key revocation on user_type changes
# =============================================================================

def get_user_profile_model():
    from .models import UserProfile
    return UserProfile

@receiver(pre_save)
def capture_old_user_type(sender, instance, **kwargs):
    """Capture old user_type_ref before save for comparison"""
    UserProfile = get_user_profile_model()
    
    if sender != UserProfile:
        return
        
    if instance.pk:
        try:
            old_instance = UserProfile.objects.get(pk=instance.pk)
            instance._old_user_type_code = old_instance.get_user_type_code()
        except UserProfile.DoesNotExist:
            pass

@receiver(post_save)
def handle_user_type_change(sender, instance, created, **kwargs):
    """Trigger key revocation if user_type changes (e.g., from viewer to contributor)"""
    UserProfile = get_user_profile_model()
    KeyRevocation = get_key_revocation_model()
    
    if sender != UserProfile:
        return
        
    if created:
        return
        
    old_code = getattr(instance, '_old_user_type_code', None)
    new_code = instance.get_user_type_code()
    
    if old_code and old_code != new_code:
        logger.warning(
            f"[USER-TYPE-CHANGE] User {instance.user.username}: "
            f"user_type changed from '{old_code}' to '{new_code}'"
        )
        
        # We need to simulate the ABAC attributes including this new user_type
        # Since it's already saved, get_user_attributes will inject the NEW code
        new_attrs = instance.get_abac_attributes()
        # To get the old attributes for the log, we take current and force the old user_type
        old_attrs = new_attrs.copy()
        old_attrs['user_type'] = old_code
        
        # TODO: Get actual key_id
        key_id = f"privkey_{instance.user.id}_placeholder"
        
        KeyRevocation.revoke_user_key(
            user=instance.user,
            key_id=key_id,
            reason='attribute_change',
            old_attributes=old_attrs,
            new_attributes=new_attrs,
            reason_detail=f"User Type upgraded/downgraded: '{old_code}' -> '{new_code}'"
        )
        
        logger.warning(
            f"[KEY-REVOKE] Key revoked for user {instance.user.username} "
            f"due to user_type change"
        )
