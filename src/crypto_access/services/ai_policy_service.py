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
import os
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
        import os
        from django.conf import settings
        
        prompt_path = os.path.join(settings.BASE_DIR, '..', 'config', 'prompts', 'ai_policy_system.md')
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                prompt_template = f.read()
        except FileNotFoundError:
            logger.error(f"AI System Prompt file not found at {prompt_path}")
            return ""
            
        return prompt_template.replace('{attributes_schema}', json.dumps(attributes_schema, indent=2))

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
        
        
        keep_alive = os.environ.get('OLLAMA_KEEP_ALIVE', '-1')
        try:
            keep_alive = int(keep_alive)
        except ValueError:
            pass

        response = requests.post(
            f"{self.base_url}/api/chat",
            json={
                "model": self.model,
                "keep_alive": keep_alive,
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
