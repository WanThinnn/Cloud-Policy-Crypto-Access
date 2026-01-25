"""
Admin URLs for ABAC attribute and policy management
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from ..views import attributes, policy, users

# Create router for ViewSets
router = DefaultRouter()
router.register(r'user-types', attributes.UserTypeViewSet, basename='user-types')
router.register(r'attributes', attributes.AttributeDefinitionViewSet, basename='attributes')
router.register(r'policies', policy.AccessPolicyViewSet, basename='policies')
router.register(r'users', users.UserManagementViewSet, basename='users')

urlpatterns = [
    # ViewSet routes
    path('', include(router.urls)),
    
    # User attributes management
    path('users/<int:user_id>/attributes/', attributes.list_user_attributes, name='list_user_attributes'),
    path('users/<int:user_id>/attributes/assign/', attributes.assign_user_attribute, name='assign_user_attribute'),
    path('users/<int:user_id>/attributes/bulk/', attributes.bulk_assign_user_attributes, name='bulk_assign_user_attributes'),
    path('users/<int:user_id>/attributes/<int:attribute_id>/', attributes.delete_user_attribute, name='delete_user_attribute'),
    
    # List users with attributes
    path('users-with-attributes/', attributes.list_users_with_attributes, name='list_users_with_attributes'),
    
    # Policy builder attributes (dynamic from database)
    path('policy-builder-attributes/', attributes.get_policy_builder_attributes, name='policy_builder_attributes'),
    
    # Template pages (HTML)
    path('pages/user-types/', attributes.user_types_page, name='user_types_page'),
    path('pages/attributes/', attributes.attributes_page, name='attributes_page'),
    path('pages/user-attributes/', attributes.user_attributes_page, name='user_attributes_page'),
    path('pages/policies/', policy.policies_page, name='policies_page'),
    path('pages/users/', users.users_page, name='users_page'),
]
