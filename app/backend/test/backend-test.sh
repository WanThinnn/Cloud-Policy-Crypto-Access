#!/bin/bash

# Cloud Firestore Crypto Access Backend - Complete Test Script
# This script tests all API endpoints step by step with individual curl commands

# Configuration
SERVER_URL="http://localhost:5000"

echo "=========================================="
echo "Cloud Firestore Crypto Access Backend Test"
echo "=========================================="
echo "Server: $SERVER_URL"
echo "Date: $(date)"
echo ""

# Step 1: Health Check
echo "=== Step 1: Health Check ==="
curl -s "$SERVER_URL/api/health" | jq

curl -X GET "$SERVER_URL/api/health/ready" | jq

curl -X GET "$SERVER_URL/api/health/live" | jq

# Step 2: Super Admin Login
echo "=== Step 2: Super Admin Login ==="
curl -s -X POST "$SERVER_URL/api/super-admin/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "superadmin1",
    "password": "Admin123!@#"
  }' | jq

# Save admin token:
ADMIN_TOKEN=$(curl -s -X POST "$SERVER_URL/api/super-admin/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "superadmin1", "password": "Admin123!@#"}' | \
  python3 -c "import json,sys; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)

echo "Admin Token: $ADMIN_TOKEN"

# Step 3: ABE System Setup
echo "=== Step 3: ABE System Setup ==="
# Check ABE status
curl -s "$SERVER_URL/api/ca/status" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

# Setup ABE (generate master key)
curl -s -X POST "$SERVER_URL/api/ca/setup" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" | jq

# Get public key
curl -s "$SERVER_URL/api/ca/public-key" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

# Step 4: Test Schema Management APIs
echo "=== Step 4: Testing Schema Management ==="

# Get all attribute schemas
echo "Getting all attribute schemas..."
curl -s "$SERVER_URL/api/super-admin/schema/attributes" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

# Get valid values for specific attributes
echo "Getting valid values for 'role' attribute..."
curl -s "$SERVER_URL/api/super-admin/schema/attributes/role/valid-values" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

echo "Getting valid values for 'department' attribute..."
curl -s "$SERVER_URL/api/super-admin/schema/attributes/department/valid-values" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

# Refresh schemas
echo "Refreshing schemas..."
curl -s -X POST "$SERVER_URL/api/super-admin/schema/refresh" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

# Step 5: Create Test Users with Database-Driven Validation
echo "=== Step 5: Creating Test Users ==="

# Create User 1 (IT Manager with new schema values)
echo "Creating IT Manager user..."
curl -s -X POST "$SERVER_URL/api/super-admin/users" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_data": {
      "email": "itmanager001@company.com", 
      "password": "Manager123!",
      "full_name": "IT Manager Test"
    },
    "user_attributes": {
      "role": "manager",
      "department": "it",
      "clearance_level": "confidential",
      "data_access": "admin", 
      "employment_status": "active",
      "location": "hq_hcm"
    }
  }' | jq

# Create User 2 (HR Staff)
echo "Creating HR Staff user..."
curl -s -X POST "$SERVER_URL/api/super-admin/users" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_data": {
      "username": "hrstaff001",
      "email": "hrstaff001@company.com",
      "password": "HrStaff123!",
      "full_name": "HR Staff Test"
    },
    "user_attributes": {
      "role": "hr_staff",
      "department": "hr", 
      "clearance_level": "internal",
      "data_access": "standard",
      "employment_status": "active",
      "location": "branch_hanoi"
    }
  }' | jq

# Create User 3 (Contractor - testing new role value)
echo "Creating Contractor user..."
curl -s -X POST "$SERVER_URL/api/super-admin/users" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_data": {
      "username": "contractor001", 
      "email": "contractor001@company.com",
      "password": "Contract123!",
      "full_name": "Contractor Test"
    },
    "user_attributes": {
      "role": "contractor",
      "department": "development",
      "clearance_level": "public",
      "data_access": "read_only",
      "employment_status": "active",
      "location": "remote"
    }
  }' | jq

# Test validation with invalid values
echo "Testing validation with invalid attributes..."
curl -s -X POST "$SERVER_URL/api/super-admin/users" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_data": {
      "username": "invaliduser",
      "email": "invalid@company.com",
      "password": "Invalid123!",
      "full_name": "Invalid User"
    },
    "user_attributes": {
      "role": "invalid_role",
      "department": "invalid_dept",
      "clearance_level": "invalid_level",
      "data_access": "invalid_access",
      "employment_status": "invalid_status"
    }
  }' | jq

# Step 6: List All Users
echo "=== Step 6: Listing All Users ==="
curl -s "$SERVER_URL/api/super-admin/users" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

# Step 7: Generate ABE Keys for Users
echo "=== Step 7: Generating ABE Keys ==="

# Get user list to extract user IDs
USER_IDS=$(curl -s "$SERVER_URL/api/super-admin/users" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | \
  python3 -c "
import json, sys
data = json.load(sys.stdin)
if 'users' in data:
    ids = [user['id'] for user in data['users'] if user.get('user_type') == 'regular']
    print(' '.join(ids[:3]))  # Get first 3 regular users
" 2>/dev/null)

echo "User IDs: $USER_IDS"

# Generate ABE keys for each user (individual commands)
USER_ID_1=$(echo $USER_IDS | cut -d' ' -f1)
USER_ID_2=$(echo $USER_IDS | cut -d' ' -f2) 
USER_ID_3=$(echo $USER_IDS | cut -d' ' -f3)

echo "Generating ABE key for user $USER_ID_1..."
curl -s -X POST "$SERVER_URL/api/ca/users/$USER_ID_1/private-key" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" | jq

echo "Generating ABE key for user $USER_ID_2..."
curl -s -X POST "$SERVER_URL/api/ca/users/$USER_ID_2/private-key" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" | jq

echo "Generating ABE key for user $USER_ID_3..."
curl -s -X POST "$SERVER_URL/api/ca/users/$USER_ID_3/private-key" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" | jq

# Step 8: Setup ABAC Policies
echo "=== Step 8: Setting up ABAC Policies ==="

# Setup corporate policies
echo "Setting up corporate ABAC policies..."
curl -s -X POST "$SERVER_URL/api/abac/setup-corporate-policies" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" | jq

# List ABAC policies
echo "Listing ABAC policies..."
curl -s "$SERVER_URL/api/abac/policies" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

# Step 9: Test User Login and File Operations
echo "=== Step 9: Testing User Login and File Operations ==="

# Get first user for testing
TEST_USER_ID=$(echo $USER_IDS | cut -d' ' -f1)
echo "Testing with user ID: $TEST_USER_ID"

# First login attempt (should require password change)
echo "First login attempt..."
curl -s -X POST "$SERVER_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "22520001", "password": "User123!@#"}' | jq

# Since it's first login, change password
echo "Changing password for first-time user..."
curl -s -X POST "$SERVER_URL/api/auth/change-password" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "22520001",
    "old_password": "User123!!@#",
    "new_password": "User123!@#"
  }' | jq

# Login again with new password
echo "Logging in with new password..."
curl -s -X POST "$SERVER_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "22520001", "password": "User123!@#"}' | jq

USER_TOKEN=$(curl -s -X POST "$SERVER_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "22520001", "password": "User123!@#!"}' | \
  python3 -c "import json,sys; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)

echo "User Token: $USER_TOKEN"

# Step 10: File Operations
echo "=== Step 10: File Operations ==="

# Create test file
echo "This is a test file for ABE encryption" > test_upload.txt

echo "Uploading test file..."
curl -s -X POST "$SERVER_URL/api/files/upload" \
  -H "Authorization: Bearer $USER_TOKEN" \
  -F "file=@test_upload.txt" \
  -F "access_policy=department:it OR department:hr" | jq

echo "Listing user files..."
curl -s "$SERVER_URL/api/files/" \
  -H "Authorization: Bearer $USER_TOKEN" | jq

echo "Checking files health..."
curl -s "$SERVER_URL/api/files/health" \
  -H "Authorization: Bearer $USER_TOKEN" | jq

# Step 11: Test File Versioning
echo "=== Step 11: Testing File Versioning ==="

# Create a test file for versioning
echo "Version 1 content" > version_test.txt

echo "Uploading initial file version..."
UPLOAD_RESULT=$(curl -s -X POST "$SERVER_URL/api/files/upload" \
  -H "Authorization: Bearer $USER_TOKEN" \
  -F "file=@version_test.txt" \
  -F "access_policy=department:it OR department:hr")

echo "$UPLOAD_RESULT" | jq

# Extract file ID for versioning test
FILE_ID=$(echo "$UPLOAD_RESULT" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('file', {}).get('id', ''))
except:
    pass
" 2>/dev/null)

echo "File ID for versioning: $FILE_ID"

# Create new version
echo "Version 2 content - updated!" > version_test_v2.txt

echo "Uploading new version..."
VERSION_RESULT=$(curl -s -X POST "$SERVER_URL/api/file-versioning/file/$FILE_ID/version" \
  -H "Authorization: Bearer $USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "file_data": "'$(base64 -w 0 version_test_v2.txt)'",
    "version_type": "MINOR",
    "change_description": "Updated content for version 2"
  }')

echo "$VERSION_RESULT" | jq

# Extract version ID for download testing
VERSION_ID=$(echo "$VERSION_RESULT" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('version', {}).get('id', ''))
except:
    pass
" 2>/dev/null)

echo "New Version ID: $VERSION_ID"

echo "Listing file versions..."
VERSIONS_LIST=$(curl -s "$SERVER_URL/api/file-versioning/file/$FILE_ID/versions" \
  -H "Authorization: Bearer $USER_TOKEN")

echo "$VERSIONS_LIST" | jq

# Extract version IDs for download
VERSION_IDS=$(echo "$VERSIONS_LIST" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    versions = data.get('versions', [])
    ids = [v.get('id', '') for v in versions[:2]]  # Get first 2 versions
    print(' '.join(ids))
except:
    pass
" 2>/dev/null)

echo "Version IDs for download: $VERSION_IDS"

VERSION_1_ID=$(echo $VERSION_IDS | cut -d' ' -f1)
VERSION_2_ID=$(echo $VERSION_IDS | cut -d' ' -f2)

echo "Testing version download..."
if [ ! -z "$VERSION_1_ID" ]; then
  curl -s "$SERVER_URL/api/file-versioning/version/$VERSION_1_ID/download" \
    -H "Authorization: Bearer $USER_TOKEN" > downloaded_v1.txt
fi

if [ ! -z "$VERSION_2_ID" ]; then
  curl -s "$SERVER_URL/api/file-versioning/version/$VERSION_2_ID/download" \
    -H "Authorization: Bearer $USER_TOKEN" > downloaded_v2.txt
fi

echo "Downloaded version 1 content:"
cat downloaded_v1.txt 2>/dev/null || echo "Download failed"

echo "Downloaded version 2 content:"
cat downloaded_v2.txt 2>/dev/null || echo "Download failed"

# Step 12: Test Additional File Management Features
echo "=== Step 12: Testing Additional File Management Features ==="

# Test file access logs (requires user_id parameter)
echo "Getting file access logs..."
curl -s "$SERVER_URL/api/files/$FILE_ID/access-logs?user_id=22520001" \
  -H "Authorization: Bearer $USER_TOKEN" | jq

# Test updating file policy 
echo "Updating file access policy..."
curl -s -X PUT "$SERVER_URL/api/files/$FILE_ID/policy" \
  -H "Authorization: Bearer $USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "22520001",
    "new_policy": "department:it AND clearance_level:confidential"
  }' | jq

# Test versioning service health
echo "Checking file versioning service health..."
curl -s "$SERVER_URL/api/file-versioning/versions/health" | jq

# Test file deletion (optional - creates a temporary file to delete)
echo "Testing file deletion..."
echo "Temporary file for deletion test" > temp_delete_test.txt
DELETE_UPLOAD_RESULT=$(curl -s -X POST "$SERVER_URL/api/files/upload" \
  -H "Authorization: Bearer $USER_TOKEN" \
  -F "file=@temp_delete_test.txt" \
  -F "access_policy=department:it")

DELETE_FILE_ID=$(echo "$DELETE_UPLOAD_RESULT" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('file', {}).get('id', ''))
except:
    pass
" 2>/dev/null)

if [ ! -z "$DELETE_FILE_ID" ]; then
  echo "Deleting test file $DELETE_FILE_ID..."
  curl -s -X DELETE "$SERVER_URL/api/files/$DELETE_FILE_ID?user_id=22520001" \
    -H "Authorization: Bearer $USER_TOKEN" | jq
fi

# Step 13: Test ABAC Access Control
echo "=== Step 13: Testing ABAC Access Control ==="

echo "Testing ABAC access check..."
curl -s -X POST "$SERVER_URL/api/abac/check-corporate-access" \
  -H "Authorization: Bearer $USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "resource_type": "file",
    "resource_id": "test_resource",
    "action": "read",
    "context": {
      "time": "business_hours",
      "location": "office"
    }
  }' | jq

# Step 14: ABE Operations
echo "=== Step 14: ABE Operations ==="

echo "Testing ABE encryption..."
curl -s -X POST "$SERVER_URL/api/abe/encrypt" \
  -H "Content-Type: application/json" \
  -d '{
    "data": "This is sensitive test data",
    "policy": "role:manager AND department:it"
  }' | jq

echo "Checking user private key status..."
curl -s "$SERVER_URL/api/ca/user/private-key/check" \
  -H "Authorization: Bearer $USER_TOKEN" | jq

echo "Generating user private key (JWT mode - will force regenerate if attributes changed)..."
curl -s -X POST "$SERVER_URL/api/ca/user/generate-private-key" \
  -H "Authorization: Bearer $USER_TOKEN" | jq

# Step 15: System Statistics and Health Checks
echo "=== Step 15: System Statistics and Health Checks ==="

echo "Getting system statistics..."
curl -s "$SERVER_URL/api/super-admin/stats" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

echo "Final health checks..."
curl -s "$SERVER_URL/api/health" | jq

echo "CA health..."
curl -s "$SERVER_URL/api/ca/health" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

echo "Files health..."
curl -s "$SERVER_URL/api/files/health" \
  -H "Authorization: Bearer $USER_TOKEN" | jq

echo "ABAC health..."
curl -s "$SERVER_URL/api/abac/health" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

# Step 16: Cleanup
echo "=== Step 16: Cleanup ==="
rm -f test_upload.txt version_test.txt version_test_v2.txt downloaded_v1.txt downloaded_v2.txt temp_delete_test.txt

echo "=========================================="
echo "Backend Test Completed Successfully!"
echo "=========================================="
