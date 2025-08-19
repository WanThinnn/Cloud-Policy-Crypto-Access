"""
Module package for Hybrid CP-ABE components
"""

# Import từ file hybrid-cp-abe.py (với dấu gạch ngang)
import importlib.util
import os

# Load module từ file với tên có dấu gạch ngang
spec = importlib.util.spec_from_file_location(
    "hybrid_cp_abe", 
    os.path.join(os.path.dirname(__file__), "hybrid-cp-abe.py")
)
hybrid_cp_abe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hybrid_cp_abe)

# Export classes
ABELibrary = hybrid_cp_abe.ABELibrary
abe_lib = hybrid_cp_abe.abe_lib

# Import database
from .database import db

# Import user management
from .user_management import UserManager, user_manager

__all__ = ['ABELibrary', 'abe_lib', 'db', 'UserManager', 'user_manager']
