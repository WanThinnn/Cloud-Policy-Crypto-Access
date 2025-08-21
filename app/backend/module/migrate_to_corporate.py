#!/usr/bin/env python3
"""
Reset and update attribute schema for Corporate environment
Convert from Medical to Corporate attributes
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from module.super_admin import SuperAdmin
from module.database import db
from datetime import datetime

def reset_attribute_schema():
    """Reset and update attribute schema to Corporate format"""
    print("🔄 Resetting Attribute Schema to Corporate Format...")
    
    try:
        # Initialize SuperAdmin to trigger schema update
        super_admin = SuperAdmin()
        
        # Force update schema by deleting existing one
        schema_ref = db.collection('attribute_schema').document('default')
        schema_ref.delete()
        print("✅ Deleted old medical schema")
        
        # Reinitialize with new corporate schema
        super_admin._initialize_attribute_schema()
        print("✅ Initialized new corporate schema")
        
        # Show new schema
        new_schema = schema_ref.get()
        if new_schema.exists:
            schema_data = new_schema.to_dict()
            print("\n🏢 NEW CORPORATE ATTRIBUTE SCHEMA:")
            print("="*50)
            
            for attr_name, attr_config in schema_data['attributes'].items():
                print(f"📋 {attr_name.upper()}:")
                print(f"   Type: {attr_config['type']}")
                print(f"   Required: {attr_config['required']}")
                print(f"   Values: {attr_config.get('values', 'N/A')}")
                print(f"   Description: {attr_config['description']}")
                print()
        
        return True
        
    except Exception as e:
        print(f"❌ Error resetting schema: {e}")
        return False

def clear_old_users_data():
    """Clear old users data (optional)"""
    print("\n🧹 Clearing old users data...")
    
    try:
        # Get all collections that might have old data
        collections_to_clear = ['users', 'user_attributes', 'super_admin']
        
        for collection_name in collections_to_clear:
            collection_ref = db.collection(collection_name)
            docs = collection_ref.stream()
            
            deleted_count = 0
            for doc in docs:
                doc.reference.delete()
                deleted_count += 1
            
            print(f"✅ Cleared {deleted_count} documents from {collection_name}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error clearing data: {e}")
        return False

def create_sample_corporate_data():
    """Create sample corporate users with correct attributes"""
    print("\n👥 Creating sample corporate users...")
    
    try:
        super_admin = SuperAdmin()
        
        # Create SuperAdmin first
        admin_result = super_admin.create_super_admin(
            username="superadmin",
            email="admin@company.com", 
            password="SuperAdmin123!"
        )
        
        if admin_result['success']:
            admin_id = admin_result['admin_id']
            print(f"✅ Created SuperAdmin with ID: {admin_id}")
            
            # Sample corporate users
            sample_users = [
                {
                    "user_data": {
                        "username": "john_manager",
                        "email": "john@company.com",
                        "password": "Manager123!",
                        "full_name": "John Smith",
                        "phone": "+84123456789",
                        "position": "IT Manager"
                    },
                    "user_attributes": {
                        "role": "manager",
                        "department": "it",
                        "clearance_level": "high",
                        "specialization": ["management", "technical"],
                        "experience_years": 8,
                        "location": "hanoi",
                        "shift": "day",
                        "data_access": "confidential"
                    }
                },
                {
                    "user_data": {
                        "username": "sarah_hr",
                        "email": "sarah@company.com", 
                        "password": "HRStaff456!",
                        "full_name": "Sarah Johnson",
                        "phone": "+84987654321",
                        "position": "HR Specialist"
                    },
                    "user_attributes": {
                        "role": "hr_staff",
                        "department": "hr",
                        "clearance_level": "medium",
                        "specialization": ["customer_service"],
                        "experience_years": 5,
                        "location": "hcm",
                        "shift": "day", 
                        "data_access": "internal"
                    }
                },
                {
                    "user_data": {
                        "username": "mike_finance",
                        "email": "mike@company.com",
                        "password": "Finance789!",
                        "full_name": "Mike Wilson", 
                        "phone": "+84555123456",
                        "position": "Finance Analyst"
                    },
                    "user_attributes": {
                        "role": "finance_staff",
                        "department": "finance",
                        "clearance_level": "high",
                        "specialization": ["analytics"],
                        "experience_years": 6,
                        "location": "hanoi",
                        "shift": "day",
                        "data_access": "confidential"
                    }
                }
            ]
            
            # Create sample users
            for i, user_data in enumerate(sample_users):
                result = super_admin.create_user_account(
                    admin_id=admin_id,
                    user_data=user_data["user_data"],
                    user_attributes=user_data["user_attributes"]
                )
                
                if result['success']:
                    print(f"✅ Created user: {user_data['user_data']['username']} (ID: {result['user_id']})")
                else:
                    print(f"❌ Failed to create user: {result['error']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating sample data: {e}")
        return False

def main():
    print("🏢 CORPORATE SCHEMA MIGRATION TOOL")
    print("="*50)
    print("This tool will:")
    print("1. Reset attribute schema from Medical to Corporate")
    print("2. Clear old users data (optional)")
    print("3. Create sample corporate users")
    print()
    
    # Ask for confirmation
    confirm = input("Do you want to proceed? This will delete existing data! (yes/no): ")
    if confirm.lower() != 'yes':
        print("❌ Migration cancelled")
        return
    
    # Step 1: Reset schema
    print("\n" + "="*50)
    if not reset_attribute_schema():
        print("❌ Schema reset failed!")
        return
    
    # Step 2: Clear old data (optional)
    clear_data = input("\nClear existing users data? (yes/no): ")
    if clear_data.lower() == 'yes':
        if not clear_old_users_data():
            print("❌ Data clearing failed!")
            return
    
    # Step 3: Create sample data
    create_samples = input("\nCreate sample corporate users? (yes/no): ")
    if create_samples.lower() == 'yes':
        if not create_sample_corporate_data():
            print("❌ Sample data creation failed!")
            return
    
    print("\n" + "="*50)
    print("🎉 MIGRATION COMPLETED SUCCESSFULLY!")
    print("="*50)
    print("✅ Schema updated to Corporate format")
    print("✅ SuperAdmin ID format: 2152xxxx")
    print("✅ Employee ID format: 2252xxxx") 
    print("✅ System ready for corporate use!")
    print("\nNew Corporate Attributes:")
    print("- Roles: employee, manager, it_admin, hr_staff, finance_staff, executive")
    print("- Departments: it, hr, finance, sales, marketing, operations")
    print("- Clearance: low, medium, high, top_secret")
    print("- Locations: hanoi, hcm, remote, hybrid")
    print("- Data Access: public, internal, confidential, restricted, top_secret")

if __name__ == "__main__":
    main()
