#!/usr/bin/env python3
"""
Script to create attribute schemas in database
"""
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from module.database import db
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_attribute_schemas():
    """
    Create attribute schema documents in Firestore
    """
    try:
        # Define attribute schemas
        schemas = {
            'user_attribute_schemas': {
                'version': '1.0.0',
                'last_updated': datetime.utcnow(),
                'updated_by': 'system_init',
                'schemas': {
                    'role': {
                        'type': 'enum',
                        'description': 'User role in the organization',
                        'valid_values': [
                            'employee',
                            'manager', 
                            'it_admin',
                            'hr_staff',
                            'finance_staff',
                            'executive',
                            'senior_employee',
                            'intern',
                            'contractor'
                        ],
                        'required': True,
                        'default': 'employee'
                    },
                    'department': {
                        'type': 'enum',
                        'description': 'Department where user works',
                        'valid_values': [
                            'it',
                            'hr',
                            'finance',
                            'marketing',
                            'sales',
                            'operations',
                            'legal',
                            'security',
                            'research',
                            'development'
                        ],
                        'required': True,
                        'default': None
                    },
                    'clearance_level': {
                        'type': 'enum',
                        'description': 'Security clearance level',
                        'valid_values': [
                            'public',
                            'internal',
                            'confidential', 
                            'restricted',
                            'secret',
                            'top_secret'
                        ],
                        'required': True,
                        'default': 'internal',
                        'hierarchy': ['public', 'internal', 'confidential', 'restricted', 'secret', 'top_secret']
                    },
                    'data_access': {
                        'type': 'enum',
                        'description': 'Data access level',
                        'valid_values': [
                            'read_only',
                            'standard',
                            'advanced',
                            'admin',
                            'super_admin'
                        ],
                        'required': True,
                        'default': 'standard'
                    },
                    'employment_status': {
                        'type': 'enum',
                        'description': 'Employment status',
                        'valid_values': [
                            'active',
                            'inactive',
                            'suspended',
                            'terminated',
                            'on_leave'
                        ],
                        'required': False,
                        'default': 'active'
                    },
                    'location': {
                        'type': 'enum',
                        'description': 'Work location',
                        'valid_values': [
                            'hq_hcm',
                            'branch_hanoi',
                            'branch_danang',
                            'remote',
                            'hybrid'
                        ],
                        'required': False,
                        'default': 'hq_hcm'
                    }
                }
            }
        }
        
        # Save schemas to Firestore
        schemas_collection = db.collection('system_schemas')
        
        for schema_name, schema_data in schemas.items():
            schemas_collection.document(schema_name).set(schema_data)
            logger.info(f"Created schema: {schema_name}")
        
        logger.info("Attribute schemas created successfully")
        return {
            'success': True,
            'schemas_created': list(schemas.keys())
        }
        
    except Exception as e:
        logger.error(f"Failed to create schemas: {e}")
        return {
            'success': False,
            'error': str(e)
        }

if __name__ == "__main__":
    result = create_attribute_schemas()
    print(f"Schema creation result: {result}")
