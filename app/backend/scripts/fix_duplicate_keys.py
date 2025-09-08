#!/usr/bin/env python3
"""
Script to fix duplicate private keys issue
Migrates all user private keys from 'abe_keys' to 'user_private_keys' collection
Ensures each user has only ONE active private key
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from module.database import db
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_duplicate_keys():
    """
    Fix the duplicate private keys issue by:
    1. Moving all user private keys from 'abe_keys' to 'user_private_keys'
    2. Ensuring each user has only ONE active key
    3. Deactivating duplicates (keeping the most recent)
    """
    
    try:
        # Collections
        abe_keys_collection = db.collection('abe_keys')
        user_private_keys_collection = db.collection('user_private_keys')
        
        # 1. Find all user private keys in abe_keys collection
        user_keys_in_abe = abe_keys_collection.where('user_id', '!=', None).get()
        
        logger.info(f"Found {len(user_keys_in_abe)} user private keys in abe_keys collection")
        
        migrated_users = set()
        
        for key_doc in user_keys_in_abe:
            key_data = key_doc.to_dict()
            user_id = key_data.get('user_id')
            
            if not user_id:
                continue
                
            # Check if user already has a key in user_private_keys collection
            existing_keys = user_private_keys_collection.where('user_id', '==', user_id).get()
            
            if existing_keys:
                logger.info(f"User {user_id} already has {len(existing_keys)} keys in user_private_keys")
                
                # Keep only the most recent key active
                all_keys = []
                for existing_key in existing_keys:
                    existing_data = existing_key.to_dict()
                    all_keys.append({
                        'doc': existing_key,
                        'data': existing_data,
                        'created_at': existing_data.get('created_at', datetime.min),
                        'source': 'user_private_keys'
                    })
                
                # Add the key from abe_keys
                all_keys.append({
                    'doc': key_doc,
                    'data': key_data,
                    'created_at': key_data.get('created_at', datetime.min),
                    'source': 'abe_keys'
                })
                
                # Sort by creation time (most recent first)
                all_keys.sort(key=lambda x: x['created_at'], reverse=True)
                
                # Keep the most recent active, deactivate others
                for i, key_info in enumerate(all_keys):
                    if i == 0:
                        # Most recent - keep active
                        if key_info['source'] == 'abe_keys':
                            # Migrate to user_private_keys
                            new_key_data = key_info['data'].copy()
                            new_key_data['is_active'] = True
                            new_key_data['migrated_from'] = 'abe_keys'
                            new_key_data['migrated_at'] = datetime.utcnow()
                            
                            new_doc_id = f"privkey_{user_id}_{int(datetime.utcnow().timestamp())}"
                            user_private_keys_collection.document(new_doc_id).set(new_key_data)
                            logger.info(f"Migrated active key for user {user_id}")
                        else:
                            # Already in user_private_keys, ensure it's active
                            key_info['doc'].reference.update({'is_active': True})
                            logger.info(f"Ensured key is active for user {user_id}")
                    else:
                        # Older keys - deactivate
                        if key_info['source'] == 'abe_keys':
                            # Delete from abe_keys (it's being replaced)
                            key_info['doc'].reference.delete()
                            logger.info(f"Deleted old key from abe_keys for user {user_id}")
                        else:
                            # Deactivate in user_private_keys
                            key_info['doc'].reference.update({
                                'is_active': False,
                                'deactivated_at': datetime.utcnow(),
                                'deactivation_reason': 'duplicate_cleanup'
                            })
                            logger.info(f"Deactivated duplicate key for user {user_id}")
                
                # Delete the original from abe_keys if not already deleted
                try:
                    key_doc.reference.delete()
                except:
                    pass  # May already be deleted
                    
            else:
                # No existing key, migrate this one
                new_key_data = key_data.copy()
                new_key_data['is_active'] = True
                new_key_data['migrated_from'] = 'abe_keys'
                new_key_data['migrated_at'] = datetime.utcnow()
                
                new_doc_id = f"privkey_{user_id}_{int(datetime.utcnow().timestamp())}"
                user_private_keys_collection.document(new_doc_id).set(new_key_data)
                
                # Delete from abe_keys
                key_doc.reference.delete()
                
                logger.info(f"Migrated key for user {user_id} from abe_keys to user_private_keys")
            
            migrated_users.add(user_id)
        
        # 2. Verify no duplicates remain
        logger.info(f"Migration complete. Processed {len(migrated_users)} users")
        
        # Verify each user has only one active key
        for user_id in migrated_users:
            active_keys = user_private_keys_collection.where('user_id', '==', user_id).where('is_active', '==', True).get()
            logger.info(f"User {user_id} now has {len(active_keys)} active keys")
            
            if len(active_keys) > 1:
                logger.warning(f"User {user_id} still has {len(active_keys)} active keys!")
        
        logger.info("✅ Migration completed successfully!")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise

if __name__ == "__main__":
    print("🔧 Fixing duplicate private keys...")
    fix_duplicate_keys()
    print("✅ Done!")
