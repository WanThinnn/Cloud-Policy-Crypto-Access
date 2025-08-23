"""
Core ABAC Policies for CP-ABE System
Run this script to populate initial ABAC policies
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from module.abac import abac
import json

def create_core_policies():
    """Create essential ABAC policies for the system"""
    
    policies = [
        # 1. File Upload Restrictions
        {
            "policy_id": "file_upload_size_limits",
            "name": "File Upload Size Restrictions",
            "description": "Limit file upload sizes based on user role",
            "resource": "files",
            "action": "upload",
            "effect": "permit",
            "conditions": {
                "subject_attributes": {
                    "role": ["manager", "it_admin"],
                    "employment_status": "active"
                },
                "resource_attributes": {
                    "file_size_mb": {"max": 100}
                },
                "environment": {
                    "business_hours": True
                }
            },
            "priority": 100
        },
        
        {
            "policy_id": "file_upload_employee_limits", 
            "name": "Employee File Upload Limits",
            "description": "Standard employees have smaller upload limits",
            "resource": "files",
            "action": "upload",
            "effect": "permit",
            "conditions": {
                "subject_attributes": {
                    "role": ["employee", "hr_staff", "finance_staff"],
                    "employment_status": "active"
                },
                "resource_attributes": {
                    "file_size_mb": {"max": 50}
                },
                "environment": {
                    "business_hours": True
                }
            },
            "priority": 90
        },
        
        # 2. File Type Restrictions
        {
            "policy_id": "hr_file_type_restrictions",
            "name": "HR Department File Type Policy",
            "description": "HR can only upload document and image files",
            "resource": "files",
            "action": "upload",
            "effect": "permit", 
            "conditions": {
                "subject_attributes": {
                    "department": "hr",
                    "employment_status": "active"
                },
                "resource_attributes": {
                    "file_type": ["application/pdf", "application/msword", 
                                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                "image/jpeg", "image/png"]
                }
            },
            "priority": 80
        },
        
        # 3. Administrative Access Control
        {
            "policy_id": "user_management_access",
            "name": "User Management Permissions", 
            "description": "Only super admins and HR managers can manage users",
            "resource": "users",
            "action": "manage",
            "effect": "permit",
            "conditions": {
                "subject_attributes": {
                    "OR": [
                        {"user_type": "super_admin"},
                        {"role": "manager", "department": "hr", "clearance_level": ["high", "top_secret"]}
                    ]
                },
                "environment": {
                    "business_hours": True,
                    "requires_mfa": True
                }
            },
            "priority": 150
        },
        
        # 4. Time-based Access Control
        {
            "policy_id": "after_hours_restrictions",
            "name": "After Hours Access Restrictions",
            "description": "Restrict sensitive operations outside business hours",
            "resource": "files",
            "action": "access",
            "effect": "deny",
            "conditions": {
                "subject_attributes": {
                    "clearance_level": ["low", "medium"]
                },
                "resource_attributes": {
                    "sensitivity": ["confidential", "top_secret"]
                },
                "environment": {
                    "business_hours": False
                }
            },
            "priority": 200  # High priority deny
        },
        
        # 5. Cross-department File Sharing
        {
            "policy_id": "cross_dept_sharing_deny",
            "name": "Cross-Department Sharing Restrictions",
            "description": "Deny cross-department sharing of confidential files",
            "resource": "files",
            "action": "share",
            "effect": "deny",
            "conditions": {
                "subject_attributes": {
                    "department": {"not_equals": "resource_owner_department"}
                },
                "resource_attributes": {
                    "classification": ["confidential", "top_secret"],
                    "owner_department": {"different_from_user": True}
                }
            },
            "priority": 180
        },
        
        # 6. Emergency Access Override
        {
            "policy_id": "emergency_access_override",
            "name": "Emergency Access Override",
            "description": "Emergency personnel can override normal restrictions",
            "resource": "files",
            "action": "access",
            "effect": "permit",
            "conditions": {
                "subject_attributes": {
                    "emergency_role": True,
                    "employment_status": "active"
                },
                "environment": {
                    "emergency_declared": True
                }
            },
            "priority": 250  # Highest priority
        },
        
        # 7. IT Department Special Privileges
        {
            "policy_id": "it_admin_system_access",
            "name": "IT Administrator System Access",
            "description": "IT admins have special system access privileges",
            "resource": "system",
            "action": "access",
            "effect": "permit",
            "conditions": {
                "subject_attributes": {
                    "department": "it",
                    "role": ["it_admin", "manager"],
                    "clearance_level": ["high", "top_secret"]
                },
                "resource_attributes": {
                    "resource_type": ["system_logs", "configuration", "technical_documents"]
                }
            },
            "priority": 120
        },
        
        # 8. Finance Data Protection
        {
            "policy_id": "finance_data_protection",
            "name": "Financial Data Access Control",
            "description": "Only finance department can access financial data",
            "resource": "files",
            "action": "access",
            "effect": "deny",
            "conditions": {
                "subject_attributes": {
                    "department": {"not_in": ["finance", "executive"]}
                },
                "resource_attributes": {
                    "data_type": ["financial", "payroll", "budget"]
                }
            },
            "priority": 190
        },
        
        # 9. Executive Override Policy
        {
            "policy_id": "executive_override", 
            "name": "Executive Access Override",
            "description": "Executives can access most resources with audit logging",
            "resource": "files",
            "action": "access",
            "effect": "permit",
            "conditions": {
                "subject_attributes": {
                    "role": ["executive", "ceo"],
                    "employment_status": "active"
                },
                "environment": {
                    "audit_required": True,
                    "mfa_required": True
                }
            },
            "priority": 240
        },
        
        # 10. Default Deny Policy
        {
            "policy_id": "default_deny_all",
            "name": "Default Deny Policy",
            "description": "Deny all access by default if no other policy matches",
            "resource": "all",
            "action": "all",
            "effect": "deny",
            "conditions": {
                # Empty conditions means this applies to everything
            },
            "priority": 1  # Lowest priority - only applies if nothing else matches
        }
    ]
    
    return policies

def populate_policies():
    """Populate the database with core policies"""
    try:
        policies = create_core_policies()
        
        print(f"Creating {len(policies)} core ABAC policies...")
        
        for policy in policies:
            result = abac.create_policy(policy)
            if result['success']:
                print(f"✅ Created policy: {policy['policy_id']}")
            else:
                print(f"❌ Failed to create policy {policy['policy_id']}: {result.get('error')}")
        
        print("\n🎉 ABAC policy initialization completed!")
        
    except Exception as e:
        print(f"❌ Error populating policies: {e}")

if __name__ == "__main__":
    populate_policies()
