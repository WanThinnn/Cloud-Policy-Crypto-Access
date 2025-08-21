"""
Module package for Hybrid CP-ABE components
"""

# Import từ file hybrid-cp-abe.py (với dấu gạch ngang)
try:
    import importlib.util
    import os
    
    # Load module từ file với tên có dấu gạch ngang
    spec = importlib.util.spec_from_file_location(
        "hybrid_cp_abe", 
        os.path.join(os.path.dirname(__file__), "hybrid-cp-abe.py")
    )
    
    if spec and spec.loader:
        hybrid_cp_abe = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(hybrid_cp_abe)
        
        # Export classes
        ABELibrary = hybrid_cp_abe.ABELibrary
        abe_lib = hybrid_cp_abe.abe_lib
        print("✅ ABE library loaded successfully")
    else:
        print("⚠️ Could not load hybrid-cp-abe spec")
        ABELibrary = None
        abe_lib = None
        
except Exception as e:
    print(f"⚠️ ABE library import failed: {e}")
    ABELibrary = None
    abe_lib = None

# Import database
from .database import db

# Import user management
from .user_management import UserManager, user_manager

# Import ABAC
from .abac import AttributeBasedAccessControl, abac

# Import Central Authority - dùng stub nếu ABE không có
try:
    if abe_lib and abe_lib.is_loaded():
        from . import central_authority
        central_authority.abe_lib = abe_lib
        from .central_authority import CentralAuthority, central_authority
        print("✅ Using full Central Authority with ABE")
    else:
        from .central_authority_stub import CentralAuthority, central_authority
        print("⚠️ Using stub Central Authority (ABE not available)")
except Exception as e:
    print(f"⚠️ Using stub Central Authority due to error: {e}")
    from .central_authority_stub import CentralAuthority, central_authority

# Import File Manager - dùng stub nếu central_authority không có
try:
    if abe_lib and abe_lib.is_loaded():
        from .file_manager import FileManager, file_manager
        print("✅ Using full File Manager with ABE")
    else:
        from .file_manager_stub import FileManager, file_manager
        print("⚠️ Using stub File Manager (ABE not available)")
except Exception as e:
    print(f"⚠️ Using stub File Manager due to error: {e}")
    from .file_manager_stub import FileManager, file_manager

__all__ = [
    'ABELibrary', 'abe_lib', 'db', 
    'UserManager', 'user_manager',
    'AttributeBasedAccessControl', 'abac',
    'CentralAuthority', 'central_authority',
    'FileManager', 'file_manager'
]
