from django.conf import settings

def pqc_settings(request):
    """
    Expose PQC settings to templates.
    """
    return {
        'ENABLE_PQC_FEATURES': getattr(settings, 'ENABLE_PQC_FEATURES', True)
    }
