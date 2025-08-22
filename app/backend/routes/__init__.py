"""
Routes package for organizing API endpoints by modules

Cấu trúc này cho phép:
1. Tách biệt routes theo chức năng
2. Dễ dàng thêm modules mới
3. Quản lý versions API
4. Cấu hình riêng cho từng module
"""
from .abe_routes import abe_api
from .auth_routes import auth_api
from .files_routes import files_api
from .abac_routes import abac_api
from .ca_routes import ca_api
from .super_admin_routes import super_admin_api

# Thêm routes modules mới ở đây khi có
# from .analytics_routes import analytics_api
# from .payment_routes import payment_api
# from .notification_routes import notification_api

# List tất cả blueprints để dễ register
all_blueprints = [
    abe_api,        # Core ABE functionality
    auth_api,       # User authentication
    files_api,      # File management
    abac_api,       # Attribute-Based Access Control
    ca_api,         # Central Authority for CP-ABE
    super_admin_api, # Super Admin management - ONLY ADMIN SYSTEM
    # analytics_api,  # Analytics & reporting (future)
    # payment_api,    # Payment processing (future)
    # notification_api, # Push notifications (future)
]

# Blueprints by category for selective loading
core_blueprints = [abe_api, auth_api]
management_blueprints = [files_api, super_admin_api]  # Only SuperAdmin
# business_blueprints = [analytics_api, payment_api]

__all__ = [
    'all_blueprints', 
    'core_blueprints', 
    'management_blueprints',
    'abe_api', 
    'auth_api', 
    'files_api',
    'super_admin_api'  # Only SuperAdmin, no admin_api
]
