"""
Base settings shared across all environments.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # points to src/
PROJECT_ROOT = BASE_DIR.parent  # points to project root

# Load environment variables from .env file in project root
load_dotenv(PROJECT_ROOT / '.env')


# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third-party apps
    'tailwind',
    'theme',
    'corsheaders',
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    
    # Local apps
    'crypto_access.apps.CryptoAccessConfig',
    
    # Third party widget
    'django_json_widget',
]

# Tailwind CSS Configuration
TAILWIND_APP_NAME = 'theme'
# Configure NPM Path dynamically for Windows, macOS, and Linux
import platform
import shutil
if platform.system() == "Windows":
    NPM_BIN_PATH = r"C:\Program Files\nodejs\npm.cmd"
else:
    NPM_BIN_PATH = shutil.which("npm") or "npm"

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'crypto_access.middleware.rate_limit.GlobalRateLimitMiddleware',  # Rate Limiting
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Serve static files
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    # JWT Middleware - Process JWT tokens before ABAC
    'crypto_access.middleware.jwt_middleware.JWTAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # ABAC Middleware for access control - Must be AFTER JWT middleware
    'crypto_access.middleware.abac_middleware.ABACContextMiddleware',
    'crypto_access.middleware.abac_middleware.ABACMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'crypto_access.context_processors.pqc_settings',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Password hashers - Using Dual-Hash (SHA3-512 client + Argon2id server)
# DualHashArgon2PasswordHasher provides backward compatibility for existing passwords
PASSWORD_HASHERS = [
    'crypto_access.hashers.DualHashArgon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
]

# WebAuthn / Passkey Configuration
WEBAUTHN_RP_ID = os.environ.get('WEBAUTHN_RP_ID', 'localhost')
WEBAUTHN_RP_NAME = os.environ.get('WEBAUTHN_RP_NAME', 'Cloud Policy Crypto Access')
WEBAUTHN_ORIGIN = os.environ.get('WEBAUTHN_ORIGIN', 'http://localhost:8000')


# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Ho_Chi_Minh'
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# WhiteNoise configuration for static files
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'crypto_access.authentication.CookieJWTAuthentication',
        # Removed SessionAuthentication to avoid CSRF issues with API calls
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 100,
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '60/min',
        'user': '1000/day',
        'cpabe_decrypt': '10/min',
        'cpabe_encrypt': '5/min',
    }
}

# Simple JWT Configuration
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': os.environ.get('DJANGO_SECRET_KEY', 'insecure-dev-key-do-not-use-in-production'),
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    
    'JTI_CLAIM': 'jti',
}

# SQL DB Master Field Encryption Key
FIELD_ENCRYPTION = os.environ.get('FIELD_ENCRYPTION', 'False').lower() in ('true', '1', 't')
MASTER_FIELD_ENCRYPTION_KEY = os.environ.get('MASTER_FIELD_ENCRYPTION_KEY')

# Global toggle for Post-Quantum Cryptography (ML-DSA) features
ENABLE_PQC_FEATURES = os.environ.get('ENABLE_PQC_FEATURES', 'True').lower() in ('true', '1', 't')

# AI Policy Assistant Configuration
AI_FEATURES_ENABLED = os.environ.get('AI_FEATURES_ENABLED', 'False').lower() in ('true', '1', 't')
OLLAMA_BASE_URL = os.environ.get('OLLAMA_BASE_URL', 'https://ollama-tls.cyberfortress.local:11434')
OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'qwen2.5-coder:3b')
OLLAMA_CACERT = os.environ.get('OLLAMA_CACERT', '/certs/CyberFortress-RootCA.crt')

# Vault ABE Plugin Integration Toggle
USE_VAULT_ABE_PLUGIN = os.environ.get('USE_VAULT_ABE_PLUGIN', 'False').lower() in ('true', '1', 't')
CPABE_SCHEME = os.environ.get('CPABE_SCHEME', 'ac17')

# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# WebAuthn Configuration
WEBAUTHN_RP_ID = os.environ.get('WEBAUTHN_RP_ID', 'cloudsafe.cyberfortress.local')
WEBAUTHN_RP_NAME = os.environ.get('WEBAUTHN_RP_NAME', 'Cloud Policy Crypto Access')
WEBAUTHN_ORIGIN = os.environ.get('WEBAUTHN_ORIGIN', 'https://cloudsafe.cyberfortress.local')

# Logging configuration
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'production')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
        'ecs_formatter': {
            '()': 'ecs_logging.StdlibFormatter',
            'extra': {
                'service.name': 'crypto-access',
                'environment': ENVIRONMENT,
            }
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file_system': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'crypto-access-system.json',
            'maxBytes': 1024 * 1024 * 15,  # 15MB
            'backupCount': 10,
            'formatter': 'ecs_formatter',
        },
        'file_auth': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'crypto-access-auth.json',
            'maxBytes': 1024 * 1024 * 15,
            'backupCount': 10,
            'formatter': 'ecs_formatter',
        },
        'file_storage': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'crypto-access-storage.json',
            'maxBytes': 1024 * 1024 * 15,
            'backupCount': 10,
            'formatter': 'ecs_formatter',
        },
        'file_audit': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'crypto-access-audit.json',
            'maxBytes': 1024 * 1024 * 15,
            'backupCount': 10,
            'formatter': 'ecs_formatter',
        },
        'file_policy': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'crypto-access-policy.json',
            'maxBytes': 1024 * 1024 * 15,
            'backupCount': 10,
            'formatter': 'ecs_formatter',
        },
        'file_attributes': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'crypto-access-attributes.json',
            'maxBytes': 1024 * 1024 * 15,
            'backupCount': 10,
            'formatter': 'ecs_formatter',
        },
        'file_user': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'crypto-access-user.json',
            'maxBytes': 1024 * 1024 * 15,
            'backupCount': 10,
            'formatter': 'ecs_formatter',
        },
    },
    'root': {
        'handlers': ['console', 'file_system'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file_system'],
            'level': 'INFO',
            'propagate': False,
        },
        'crypto_access.auth': {
            'handlers': ['console', 'file_auth'],
            'level': 'INFO',
            'propagate': False,
        },
        'crypto_access.storage': {
            'handlers': ['console', 'file_storage'],
            'level': 'INFO',
            'propagate': False,
        },
        'crypto_access.audit': {
            'handlers': ['console', 'file_audit'],
            'level': 'INFO',
            'propagate': False,
        },
        'crypto_access.policy': {
            'handlers': ['console', 'file_policy'],
            'level': 'INFO',
            'propagate': False,
        },
        'crypto_access.attributes': {
            'handlers': ['console', 'file_attributes'],
            'level': 'INFO',
            'propagate': False,
        },
        'crypto_access.user': {
            'handlers': ['console', 'file_user'],
            'level': 'INFO',
            'propagate': False,
        },
        'crypto_access.system': {
            'handlers': ['console', 'file_system'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# CORS Configuration (restrictive by default; development.py overrides to allow all origins)
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOW_CREDENTIALS = True

# CSRF Configuration  
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]
CSRF_COOKIE_HTTPONLY = False  # Allow JavaScript to read the CSRF token
CSRF_COOKIE_SAMESITE = 'Lax'

# ABAC Protected Routes Configuration
ABAC_PROTECTED_ROUTES = [
    # Specific patterns must come FIRST (before generic /api/storage/files/)
    {
        'pattern': r'^/api/storage/files/upload/',
        'resource': 'document',
        'methods': {
            'POST': 'upload',
        }
    },
    {
        'pattern': r'^/api/storage/files/create_folder/',
        'resource': 'document',
        'methods': {
            'POST': 'upload',  # Creating folder requires upload permission
        }
    },
    {
        'pattern': r'^/api/storage/files/browse/',
        'resource': 'document',
        'methods': {
            'GET': 'read',  # Browse requires 'read' permission
        }
    },
    {
        'pattern': r'^/api/storage/files/download_by_path/',
        'resource': 'document',
        'methods': {
            'GET': 'download',
        }
    },
    {
        'pattern': r'^/api/storage/files/preview_by_path/',
        'resource': 'document',
        'methods': {
            'GET': 'read',
        }
    },
    {
        'pattern': r'^/api/storage/files/delete_by_path/',
        'resource': 'document',
        'methods': {
            'DELETE': 'delete',
        }
    },
    {
        'pattern': r'^/api/storage/files/\d+/download/',
        'resource': 'document',
        'methods': {
            'GET': 'download',
        }
    },
    # Generic pattern LAST as fallback
    {
        'pattern': r'^/api/storage/files/\d+/',
        'resource': 'document',
        'methods': {
            'GET': 'read',
            'PUT': 'update',
            'PATCH': 'update',
            'DELETE': 'delete',
        }
    },
    {
        'pattern': r'^/api/admin/users/',
        'resource': 'user',
        'methods': {
            'GET': '*',
            'POST': '*',
            'PUT': '*',
            'PATCH': '*',
            'DELETE': '*',
        }
    },
    {
        'pattern': r'^/api/admin/user-types/',
        'resource': 'attribute',
        'methods': {
            'GET': '*',
            'POST': '*',
            'PUT': '*',
            'PATCH': '*',
            'DELETE': '*',
        }
    },
    {
        'pattern': r'^/api/admin/attributes/',
        'resource': 'attribute',
        'methods': {
            'GET': '*',
            'POST': '*',
            'PUT': '*',
            'PATCH': '*',
            'DELETE': '*',
        }
    },
    {
        'pattern': r'^/api/admin/policies/',
        'resource': 'policy',
        'methods': {
            'GET': '*',
            'POST': '*',
            'PUT': '*',
            'PATCH': '*',
            'DELETE': '*',
        }
    },
    {
        'pattern': r'^/api/admin/audit-logs/',
        'resource': 'audit',
        'methods': {
            'GET': 'read',
            'POST': '*',
            'PUT': '*',
            'PATCH': '*',
            'DELETE': '*',
        }
    },
    {
        'pattern': r'^/api/admin/key-revocations/',
        'resource': 'key',
        'methods': {
            'GET': '*',
            'POST': '*',
            'PUT': '*',
            'PATCH': '*',
            'DELETE': '*',
        }
    },
]
