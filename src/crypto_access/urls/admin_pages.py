"""
Admin Page URLs (HTML templates without /api/ prefix)
"""

from django.urls import path
from django.shortcuts import render
from crypto_access.views import attributes, policy

app_name = 'admin_pages'

def files_page(request):
    """Render document management page"""
    return render(request, 'documents/files.html')

urlpatterns = [
    # Admin template pages (HTML)
    path('user-types/', attributes.user_types_page, name='user_types_page'),
    path('attributes/', attributes.attributes_page, name='attributes_page'),
    path('user-attributes/', attributes.user_attributes_page, name='user_attributes_page'),
    path('policies/', policy.policies_page, name='policies_page'),
    path('files/', files_page, name='files_page'),
]
