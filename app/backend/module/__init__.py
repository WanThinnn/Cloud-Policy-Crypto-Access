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

# Import Central Authority
try:
    from . import central_authority
    if abe_lib:
        central_authority.abe_lib = abe_lib
    from .central_authority import CentralAuthority, central_authority
    print("✅ Using Central Authority")
except Exception as e:
    print(f"⚠️ Central Authority import failed: {e}")
    CentralAuthority = None
    central_authority = None

# Import File Manager
try:
    from .file_manager import FileManager, file_manager
    print("✅ Using File Manager")
except Exception as e:
    print(f"⚠️ File Manager import failed: {e}")
    FileManager = None
    file_manager = None

__all__ = [
    'ABELibrary', 'abe_lib', 'db', 
    'UserManager', 'user_manager',
    'AttributeBasedAccessControl', 'abac',
    'CentralAuthority', 'central_authority',
    'FileManager', 'file_manager'
]
