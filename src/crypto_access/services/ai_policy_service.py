"""
Local AI Policy Assistant Service
Uses Ollama (local LLM) to generate ABAC + CP-ABE policies from natural language.
"""
import json
import logging
import requests
from django.conf import settings
from django.core.cache import cache
from crypto_access.models import AttributeDefinition, UserType

logger = logging.getLogger('crypto_access.system')

# JSON Schema for structured output enforcement
POLICY_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "subject_condition": {"type": "string"},
        "cpabe_policy": {"type": "string"},
        "resources": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": ["document", "key", "user", "policy", "attribute", "audit", "*"]
            }
        },
        "action": {
            "type": "string",
            "enum": ["read", "write", "update", "delete", "upload", "download", "encrypt", "decrypt", "*"]
        },
        "effect": {
            "type": "string",
            "enum": ["allow", "deny"]
        },
        "explanation": {"type": "string"}
    },
    "required": ["subject_condition", "cpabe_policy", "resources", "action", "effect", "explanation"]
}

class AIPolicyService:
    def __init__(self):
        self.base_url = getattr(settings, 'OLLAMA_BASE_URL', 'http://ollama.cyberfortress.local:11434')
        self.model = getattr(settings, 'OLLAMA_MODEL', 'qwen2.5-coder:3b')
        self.enabled = getattr(settings, 'AI_FEATURES_ENABLED', False)
        self.ca_cert = getattr(settings, 'OLLAMA_CACERT', False)
    
    def is_available(self):
        """Check if Ollama service is running and model is loaded."""
        if not self.enabled:
            return False
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=3, verify=self.ca_cert)
            if resp.status_code == 200:
                models = [m['name'] for m in resp.json().get('models', [])]
                return any(self.model in m for m in models)
        except requests.ConnectionError:
            return False
        return False
    
    def _build_system_prompt(self, attributes_schema):
        """Build system prompt with dynamic attribute schema from DB."""
        return f"""You are a security policy generator for a CP-ABE (Ciphertext-Policy Attribute-Based Encryption) system.

AVAILABLE ATTRIBUTES AND VALUES:
{json.dumps(attributes_schema, indent=2)}

RULES:
1. subject_condition uses Python syntax with "r.sub." prefix: r.sub.department == 'it'
2. Use "and" / "or" for boolean logic, NOT "&&" / "||"  
3. Use "==" for equality, "in" for list membership
4. cpabe_policy uses "attribute:value" format with "and" / "or"
5. STRICT RULE: ONLY use attributes and values EXACTLY as they appear in the schema above.
6. If the user requests an attribute or value that is NOT in the schema (e.g., "phòng xuất nhập khẩu" but it's missing), you MUST set subject_condition and cpabe_policy to an empty string "", and explain what is missing in the explanation field.
7. Wrap compound expressions in parentheses
8. Extract resources, action, and effect from the prompt based on the allowed enums.
   - For Action, pick EXACTLY ONE. If multiple are implied (e.g. read and download), pick the higher privilege one (download).
   - "quản lý" or "manage" means action = "*".
   If not specified in the prompt, default to resources=['document'], action='read', effect='allow'.
9. CP-ABE mathematically DOES NOT support negation. DO NOT use "not", "!=", or "not in" anywhere. If you need negation (e.g., "except X"), you MUST positively list all remaining allowed values from the schema. For example, if status is ['active', 'inactive', 'terminated'] and prompt says "except terminated", use `r.sub.status in ['active', 'inactive']` for subject_condition and `(status:active or status:inactive)` for cpabe_policy.

EXAMPLES:
Input: "Allow IT department staff to view documents"
Output: {{"subject_condition": "r.sub.department == 'it'", "cpabe_policy": "department:it", "resources": ["document"], "action": "read", "effect": "allow", "explanation": "Allows users in IT department to read documents."}}

Input: "Allow managers or directors with secret clearance"  
Output: {{"subject_condition": "r.sub.role in ['manager', 'director'] and r.sub.clearance_level == 'secret'", "cpabe_policy": "((role:manager or role:director) and clearance_level:secret)", "resources": ["document"], "action": "read", "effect": "allow", "explanation": "Allows managers or directors who have secret clearance level"}}

Input: "Allow data owners to edit documents, except those who are terminated or inactive"
Output: {{"subject_condition": "r.sub.user_type == 'data_owner' and r.sub.employment_status in ['active', 'on_leave']", "cpabe_policy": "(user_type:data_owner and (employment_status:active or employment_status:on_leave))", "resources": ["document"], "action": "write", "effect": "allow", "explanation": "Allows data owners to edit, excluding terminated and inactive users by explicitly allowing active and on_leave."}}"""

    def _get_attributes_schema(self):
        """Fetch current attribute definitions from database with caching."""
        cache_key = "ai_policy_attributes_schema"
        schema = cache.get(cache_key)
        
        if schema is None:
            schema = []
            # Get attribute definitions
            for attr in AttributeDefinition.objects.filter(is_active=True):
                entry = {"name": attr.name, "type": attr.data_type}
                if attr.allowed_values:
                    entry["allowed_values"] = attr.allowed_values
                schema.append(entry)
            # Include user types
            user_types = list(UserType.objects.filter(is_active=True).values_list('code', flat=True))
            if user_types:
                schema.insert(0, {"name": "user_type", "type": "enum", "allowed_values": user_types})
                
            # Cache for 5 minutes. Admin usually generates policies right after creating attributes.
            cache.set(cache_key, schema, timeout=300)
            
        return schema
    
    def generate_policy(self, user_prompt: str) -> dict:
        """Generate ABAC + CP-ABE policy from natural language."""
        if not self.enabled:
            raise RuntimeError("AI features are not enabled")
            
        schema = self._get_attributes_schema()
        system_prompt = self._build_system_prompt(schema)
        
        response = requests.post(
            f"{self.base_url}/api/chat",
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "format": POLICY_OUTPUT_SCHEMA,  # Structured output enforcement
                "stream": False,
                "options": {
                    "temperature": 0.1,  # Low temp for determinism
                    "num_predict": 300   # Limit max tokens to prevent infinite generation
                }
            },
            timeout=120,
            verify=self.ca_cert
        )
        response.raise_for_status()
        
        result = json.loads(response.json()["message"]["content"])
        return result

# Singleton
ai_policy_service = AIPolicyService()
