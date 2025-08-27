"""
Schema validation module for user attributes
"""
import logging
from typing import Dict, List, Any, Optional
from module.database import db

logger = logging.getLogger(__name__)

class AttributeSchemaValidator:
    """
    Validates user attributes against database schemas
    """
    
    def __init__(self):
        self.schemas_collection = db.collection('system_schemas')
        self._cached_schemas = None
        
    def _load_schemas(self) -> Dict[str, Any]:
        """
        Load schemas from database with caching
        """
        try:
            if self._cached_schemas is None:
                schema_doc = self.schemas_collection.document('user_attribute_schemas').get()
                
                if not schema_doc.exists:
                    logger.error("User attribute schemas not found in database")
                    return {}
                
                self._cached_schemas = schema_doc.to_dict()
                logger.info("Loaded attribute schemas from database")
            
            return self._cached_schemas
            
        except Exception as e:
            logger.error(f"Failed to load schemas: {e}")
            return {}
    
    def validate_attributes(self, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate user attributes against database schemas
        
        Args:
            attributes: Dict of user attributes to validate
            
        Returns:
            Validation result with success status and details
        """
        try:
            schemas = self._load_schemas()
            
            if not schemas:
                return {
                    'success': False,
                    'error': 'Schema validation unavailable - schemas not loaded'
                }
            
            schema_definitions = schemas.get('attributes', {})
            errors = []
            warnings = []
            
            # Validate each attribute
            for attr_name, attr_value in attributes.items():
                if attr_name in schema_definitions:
                    validation_result = self._validate_single_attribute(
                        attr_name, attr_value, schema_definitions[attr_name]
                    )
                    
                    if not validation_result['valid']:
                        errors.extend(validation_result['errors'])
                    
                    if validation_result.get('warnings'):
                        warnings.extend(validation_result['warnings'])
                else:
                    warnings.append(f"Unknown attribute '{attr_name}' - not defined in schema")
            
            # Check for required attributes
            for attr_name, schema_def in schema_definitions.items():
                if schema_def.get('required', False) and attr_name not in attributes:
                    default_value = schema_def.get('default')
                    if default_value is not None:
                        warnings.append(f"Missing required attribute '{attr_name}' - will use default: {default_value}")
                    else:
                        errors.append(f"Missing required attribute '{attr_name}'")
            
            return {
                'success': len(errors) == 0,
                'valid': len(errors) == 0,
                'errors': errors,
                'warnings': warnings,
                'validated_attributes': attributes
            }
            
        except Exception as e:
            logger.error(f"Attribute validation failed: {e}")
            return {
                'success': False,
                'error': f'Validation error: {str(e)}'
            }
    
    def _validate_single_attribute(self, attr_name: str, attr_value: Any, schema_def: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a single attribute against its schema definition
        """
        errors = []
        warnings = []
        
        attr_type = schema_def.get('type', 'string')
        
        if attr_type == 'enum':
            valid_values = schema_def.get('valid_values', [])
            
            if attr_value not in valid_values:
                errors.append(
                    f"Invalid value for {attr_name}: {attr_value}. "
                    f"Valid values: {valid_values}"
                )
        
        elif attr_type == 'string':
            if not isinstance(attr_value, str):
                errors.append(f"Attribute '{attr_name}' must be a string, got {type(attr_value).__name__}")
        
        elif attr_type == 'number':
            if not isinstance(attr_value, (int, float)):
                errors.append(f"Attribute '{attr_name}' must be a number, got {type(attr_value).__name__}")
        
        elif attr_type == 'boolean':
            if not isinstance(attr_value, bool):
                errors.append(f"Attribute '{attr_name}' must be a boolean, got {type(attr_value).__name__}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def get_valid_values(self, attribute_name: str) -> List[str]:
        """
        Get valid values for a specific attribute
        """
        try:
            schemas = self._load_schemas()
            schema_definitions = schemas.get('attributes', {})
            
            if attribute_name in schema_definitions:
                attr_schema = schema_definitions[attribute_name]
                return attr_schema.get('valid_values', [])
            
            return []
            
        except Exception as e:
            logger.error(f"Failed to get valid values for {attribute_name}: {e}")
            return []
    
    def get_all_schemas(self) -> Dict[str, Any]:
        """
        Get all attribute schemas
        """
        return self._load_schemas()
    
    def refresh_schemas(self):
        """
        Force refresh of cached schemas
        """
        self._cached_schemas = None
        logger.info("Schema cache cleared - will reload on next validation")

# Global validator instance
attribute_validator = AttributeSchemaValidator()
