"""
Settings package for config project.
Automatically imports the appropriate settings based on DJANGO_SETTINGS_MODULE.
"""

import os

# Default to development settings if not specified
env = os.environ.get('DJANGO_ENV', 'development')

if env == 'production':
    from .production import *
elif env == 'development':
    from .development import *
else:
    from .base import *
