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
from .admin_routes import admin_api
from .files_routes import files_api
from .abac_routes import abac_api
from .ca_routes import ca_api

# Thêm routes modules mới ở đây khi có
# from .analytics_routes import analytics_api
# from .payment_routes import payment_api
# from .notification_routes import notification_api

# List tất cả blueprints để dễ register
all_blueprints = [
    abe_api,        # Core ABE functionality
    auth_api,       # User authentication
    files_api,      # File management
    admin_api,      # Admin operations (future)
    abac_api,       # Attribute-Based Access Control
    ca_api,         # Central Authority for CP-ABE
    # analytics_api,  # Analytics & reporting (future)
    # payment_api,    # Payment processing (future)
    # notification_api, # Push notifications (future)
]

# Blueprints by category for selective loading
core_blueprints = [abe_api, auth_api]
management_blueprints = [files_api, admin_api]
# business_blueprints = [analytics_api, payment_api]

__all__ = [
    'all_blueprints', 
    'core_blueprints', 
    'management_blueprints',
    'abe_api', 
    'auth_api', 
    'files_api',
    'admin_api'
]
