"""
Admin Page URLs (HTML templates without /api/ prefix)
"""

from django.urls import path
from crypto_access.views import attributes, policy

app_name = 'admin_pages'

urlpatterns = [
    # Admin template pages (HTML)
    path('user-types/', attributes.user_types_page, name='user_types_page'),
    path('attributes/', attributes.attributes_page, name='attributes_page'),
    path('user-attributes/', attributes.user_attributes_page, name='user_attributes_page'),
    path('policies/', policy.policies_page, name='policies_page'),
]
