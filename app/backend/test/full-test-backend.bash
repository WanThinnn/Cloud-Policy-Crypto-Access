# Step 1: Health Check
curl -s "http://192.168.1.200:5000/api/health" | jq
curl -X GET http://192.168.1.200:5000/api/health/ready | jq
curl -X GET http://192.168.1.200:5000/api/health/live | jq
# Step 2: SuperAdmin Login
curl -s -X POST "http://192.168.1.200:5000/api/super-admin/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "superadmin1",
    "password": "Admin123!@#"
  }' | jq

# Save admin token:
ADMIN_TOKEN=$(curl -s -X POST "http://192.168.1.200:5000/api/super-admin/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "superadmin1", "password": "Admin123!@#"}' | \
  python3 -c "import json,sys; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)

echo "Admin Token: $ADMIN_TOKEN"

# Step 3: ABE System Setup
# Check ABE status
curl -s "http://192.168.1.200:5000/api/ca/status" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

# Setup ABE (generate master key)
curl -s -X POST "http://192.168.1.200:5000/api/ca/setup" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" | jq

# Get public key
curl -s "http://192.168.1.200:5000/api/ca/public-key" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

# Step 4: Test Schema Management APIs
echo "=== Testing Schema Management ==="

# Get all attribute schemas
echo "Getting all attribute schemas..."
curl -s "http://192.168.1.200:5000/api/super-admin/schema/attributes" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

# Get valid values for specific attributes
echo "Getting valid values for 'role' attribute..."
curl -s "http://192.168.1.200:5000/api/super-admin/schema/attributes/role/valid-values" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

echo "Getting valid values for 'department' attribute..."
curl -s "http://192.168.1.200:5000/api/super-admin/schema/attributes/department/valid-values" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

# Refresh schemas
echo "Refreshing schemas..."
curl -s -X POST "http://192.168.1.200:5000/api/super-admin/schema/refresh" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

# Step 5: Create Test Users with Database-Driven Validation
echo "=== Creating Test Users ==="

# Create User 1 (IT Manager with new schema values)
echo "Creating IT Manager user..."
curl -s -X POST "http://192.168.1.200:5000/api/super-admin/users" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_data": {
      "email": "itmanager001@company.com", 
      "password": "User123!@#",
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
curl -s -X POST "http://192.168.1.200:5000/api/super-admin/users" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_data": {
      "email": "hrstaff002@company.com",
      "password": "User123!@#",
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
curl -s -X POST "http://192.168.1.200:5000/api/super-admin/users" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_data": {
      "email": "contractor003@company.com",
      "password": "User123!@#",
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
curl -s -X POST "http://192.168.1.200:5000/api/super-admin/users" \
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
echo "=== Listing All Users ==="
curl -s "http://192.168.1.200:5000/api/super-admin/users" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

# Step 7: Generate ABE Keys for Users
echo "=== Generating ABE Keys ==="

# Get user list to extract user IDs
USER_IDS=$(curl -s "http://192.168.1.200:5000/api/super-admin/users" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | \
  python3 -c "
import json, sys
data = json.load(sys.stdin)
if 'users' in data:
    ids = [user['id'] for user in data['users'] if user.get('user_type') == 'regular']
    print(' '.join(ids[-3:]))  # Get last 3 regular users (newly created)
" 2>/dev/null)

echo "User IDs: $USER_IDS"

# Generate ABE keys for each user
for USER_ID in $USER_IDS; do
  echo "Generating ABE key for user $USER_ID..."
  curl -s -X POST "http://192.168.1.200:5000/api/ca/users/$USER_ID/private-key" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" | jq
done

# Step 8: Setup ABAC Policies
echo "=== Setting up ABAC Policies ==="

# Setup corporate policies
echo "Setting up corporate ABAC policies..."
curl -s -X POST "http://192.168.1.200:5000/api/abac/setup-corporate-policies" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" | jq

# List ABAC policies
echo "Listing ABAC policies..."
curl -s "http://192.168.1.200:5000/api/abac/policies" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

# Step 9: Test User Login and File Operations
echo "=== Testing User Login and File Operations ==="

# Get a test user for login (first regular user)
TEST_USER_ID=$(echo $USER_IDS | cut -d' ' -f1)
echo "Testing with user ID: $TEST_USER_ID"

# Login as regular user (using username as user ID)
USER_TOKEN=$(curl -s -X POST "http://192.168.1.200:5000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "'"$USER_ID"'", "password": "User123!@#"}' | \
  python3 -c "import json,sys; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)

echo "User Token: $USER_TOKEN"
############
curl -s -X POST "http://192.168.1.200:5000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "'"$USER_ID"'", "password": "User123!@#"}' | jq

if [ ! -z "$USER_TOKEN" ]; then
  # Test file upload
  echo "Testing file upload..."
  echo "This is a test file for ABE encryption" > test_upload.txt
  
  curl -s -X POST "http://192.168.1.200:5000/api/files/upload" \
    -H "Authorization: Bearer $USER_TOKEN" \
    -F "file=@test_upload.txt" \
    -F "access_policy=department:it OR department:hr" | jq
  
  # List user files
  echo "Listing user files..."
  curl -s "http://192.168.1.200:5000/api/files/" \
    -H "Authorization: Bearer $USER_TOKEN" | jq

fi

# Step 10: Test File Versioning
echo "=== Testing File Versioning ==="

if [ ! -z "$USER_TOKEN" ]; then
  # Create a test file for versioning
  echo "Version 1 content" > version_test.txt
  
  echo "Uploading initial file version..."
  UPLOAD_RESULT=$(curl -s -X POST "http://192.168.1.200:5000/api/files/upload" \
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
  
  if [ ! -z "$FILE_ID" ]; then
    echo "File ID for versioning: $FILE_ID"
    
    # Create new version
    echo "Version 2 content - updated!" > version_test_v2.txt
    
    echo "Uploading new version..."
    curl -s -X POST "http://192.168.1.200:5000/api/files/$FILE_ID/versions" \
      -H "Authorization: Bearer $USER_TOKEN" \
      -F "file=@version_test_v2.txt" | jq
    
    # List file versions
    echo "Listing file versions..."
    curl -s "http://192.168.1.200:5000/api/files/$FILE_ID/versions" \
      -H "Authorization: Bearer $USER_TOKEN" | jq
    
    # Test version download
    echo "Testing version download..."
    curl -s "http://192.168.1.200:5000/api/files/$FILE_ID/versions/1/download" \
      -H "Authorization: Bearer $USER_TOKEN" > downloaded_v1.txt
    
    curl -s "http://192.168.1.200:5000/api/files/$FILE_ID/versions/2/download" \
      -H "Authorization: Bearer $USER_TOKEN" > downloaded_v2.txt
    
    echo "Downloaded version 1 content:"
    cat downloaded_v1.txt 2>/dev/null || echo "Download failed"
    
    echo "Downloaded version 2 content:"
    cat downloaded_v2.txt 2>/dev/null || echo "Download failed"
    
    # Clean up test files
    rm -f version_test.txt version_test_v2.txt downloaded_v1.txt downloaded_v2.txt
  fi
fi

# Step 11: Test ABAC Access Control
echo "=== Testing ABAC Access Control ==="

if [ ! -z "$USER_TOKEN" ]; then
  # Test access check
  echo "Testing ABAC access check..."
  curl -s -X POST "http://192.168.1.200:5000/api/abac/check-corporate-access" \
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
fi

# Step 12: System Statistics and Health Checks
echo "=== System Statistics and Health ==="

# Get system statistics
echo "Getting system statistics..."
curl -s "http://192.168.1.200:5000/api/super-admin/stats" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

# Health checks
echo "Performing health checks..."
curl -s "http://192.168.1.200:5000/api/health" | jq
curl -s "http://192.168.1.200:5000/api/ca/health" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq
curl -s "http://192.168.1.200:5000/api/files/health" \
  -H "Authorization: Bearer $USER_TOKEN" | jq
curl -s "http://192.168.1.200:5000/api/abac/health" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

echo "=== Full Backend Test Completed ==="
curl -s "http://192.168.1.200:5000/api/health" | jq
curl -X GET http://192.168.1.200:5000/api/health/ready | jq
curl -X GET http://192.168.1.200:5000/api/health/live | jq
# Step 2: SuperAdmin Login
curl -s -X POST "http://192.168.1.200:5000/api/super-admin/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "superadmin1",
    "password": "Admin123!@#"
  }' | jq

# Save admin token:
ADMIN_TOKEN=$(curl -s -X POST "http://192.168.1.200:5000/api/super-admin/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "superadmin1", "password": "Admin123!@#"}' | \
  python3 -c "import json,sys; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)

echo "Admin Token: $ADMIN_TOKEN"

# Step 3: ABE System Setup
# Check ABE status
curl -s "http://192.168.1.200:5000/api/ca/status" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

# Setup ABE (generate master key)
curl -s -X POST "http://192.168.1.200:5000/api/ca/setup" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" | jq

# Get public key
curl -s "http://192.168.1.200:5000/api/ca/public-key" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq


# Step 4: Test Schema Management APIs
echo "=== Testing Schema Management ==="

# Get all attribute schemas
echo "Getting all attribute schemas..."
curl -s "http://192.168.1.200:5000/api/super-admin/schema/attributes" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

# Get valid values for specific attributes
echo "Getting valid values for 'role' attribute..."
curl -s "http://192.168.1.200:5000/api/super-admin/schema/attributes/role/valid-values" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

echo "Getting valid values for 'department' attribute..."
curl -s "http://192.168.1.200:5000/api/super-admin/schema/attributes/department/valid-values" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

# Refresh schemas
echo "Refreshing schemas..."
curl -s -X POST "http://192.168.1.200:5000/api/super-admin/schema/refresh" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

# Step 5: Create Test Users with Database-Driven Validation
echo "=== Creating Test Users ==="

# Create User 1 (IT Manager with new schema values)
echo "Creating IT Manager user..."
curl -s -X POST "http://192.168.1.200:5000/api/super-admin/users" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_data": {
      "username": "itmanager001",
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
curl -s -X POST "http://192.168.1.200:5000/api/super-admin/users" \
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
curl -s -X POST "http://192.168.1.200:5000/api/super-admin/users" \
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
curl -s -X POST "http://192.168.1.200:5000/api/super-admin/users" \
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
echo "=== Listing All Users ==="
curl -s "http://192.168.1.200:5000/api/super-admin/users" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

# Step 7: Generate ABE Keys for Users
echo "=== Generating ABE Keys ==="

# Get user list to extract user IDs
USER_IDS=$(curl -s "http://192.168.1.200:5000/api/super-admin/users" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | \
  python3 -c "
import json, sys
data = json.load(sys.stdin)
if 'users' in data:
    ids = [user['id'] for user in data['users'] if user.get('user_type') == 'regular']
    print(' '.join(ids[:3]))  # Get first 3 regular users
" 2>/dev/null)

echo "User IDs: $USER_IDS"

# Generate ABE keys for each user
for USER_ID in $USER_IDS; do
  echo "Generating ABE key for user $USER_ID..."
  curl -s -X POST "http://192.168.1.200:5000/api/ca/users/$USER_ID/private-key" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" | jq
done

# Step 8: Setup ABAC Policies
echo "=== Setting up ABAC Policies ==="

# Setup corporate policies
echo "Setting up corporate ABAC policies..."
curl -s -X POST "http://192.168.1.200:5000/api/abac/setup-corporate-policies" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" | jq

# List ABAC policies
echo "Listing ABAC policies..."
curl -s "http://192.168.1.200:5000/api/abac/policies" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

# Step 9: Test User Login and File Operations
echo "=== Testing User Login and File Operations ==="

# Get a test user for login (first regular user)
TEST_USER_ID=$(echo $USER_IDS | cut -d' ' -f1)
echo "Testing with user ID: $TEST_USER_ID"

# Login as regular user (using username as user ID)
echo "Logging in as regular user..."
USER_TOKEN=$(curl -s -X POST "http://192.168.1.200:5000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\": \"$TEST_USER_ID\", \"password\": \"Manager123!\"}" | \
  python3 -c "import json,sys; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)

echo "User Token: $USER_TOKEN"

if [ ! -z "$USER_TOKEN" ]; then
  # Test file upload
  echo "Testing file upload..."
  echo "This is a test file for ABE encryption" > test_upload.txt
  
  curl -s -X POST "http://192.168.1.200:5000/api/files/upload" \
    -H "Authorization: Bearer $USER_TOKEN" \
    -F "file=@test_upload.txt" \
    -F "access_policy=department:it OR department:hr" | jq
  
  # List user files
  echo "Listing user files..."
  curl -s "http://192.168.1.200:5000/api/files/" \
    -H "Authorization: Bearer $USER_TOKEN" | jq
  
  # Clean up test file
  rm -f test_upload.txt
fi

# Step 10: Test File Versioning
echo "=== Testing File Versioning ==="

if [ ! -z "$USER_TOKEN" ]; then
  # Create a test file for versioning
  echo "Version 1 content" > version_test.txt
  
  echo "Uploading initial file version..."
  UPLOAD_RESULT=$(curl -s -X POST "http://192.168.1.200:5000/api/files/upload" \
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
  
  if [ ! -z "$FILE_ID" ]; then
    echo "File ID for versioning: $FILE_ID"
    
    # Create new version
    echo "Version 2 content - updated!" > version_test_v2.txt
    
    echo "Uploading new version..."
    curl -s -X POST "http://192.168.1.200:5000/api/files/$FILE_ID/versions" \
      -H "Authorization: Bearer $USER_TOKEN" \
      -F "file=@version_test_v2.txt" | jq
    
    # List file versions
    echo "Listing file versions..."
    curl -s "http://192.168.1.200:5000/api/files/$FILE_ID/versions" \
      -H "Authorization: Bearer $USER_TOKEN" | jq
    
    # Test version download
    echo "Testing version download..."
    curl -s "http://192.168.1.200:5000/api/files/$FILE_ID/versions/1/download" \
      -H "Authorization: Bearer $USER_TOKEN" > downloaded_v1.txt
    
    curl -s "http://192.168.1.200:5000/api/files/$FILE_ID/versions/2/download" \
      -H "Authorization: Bearer $USER_TOKEN" > downloaded_v2.txt
    
    echo "Downloaded version 1 content:"
    cat downloaded_v1.txt 2>/dev/null || echo "Download failed"
    
    echo "Downloaded version 2 content:"
    cat downloaded_v2.txt 2>/dev/null || echo "Download failed"
    
    # Clean up test files
    rm -f version_test.txt version_test_v2.txt downloaded_v1.txt downloaded_v2.txt
  fi
fi

# Step 11: Test ABAC Access Control
echo "=== Testing ABAC Access Control ==="

if [ ! -z "$USER_TOKEN" ]; then
  # Test access check
  echo "Testing ABAC access check..."
  curl -s -X POST "http://192.168.1.200:5000/api/abac/check-corporate-access" \
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
fi

# Step 12: System Statistics and Health Checks
echo "=== System Statistics and Health ==="

# Get system statistics
echo "Getting system statistics..."
curl -s "http://192.168.1.200:5000/api/super-admin/stats" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

# Health checks
echo "Performing health checks..."
curl -s "http://192.168.1.200:5000/api/health" | jq
curl -s "http://192.168.1.200:5000/api/ca/health" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq
curl -s "http://192.168.1.200:5000/api/files/health" \
  -H "Authorization: Bearer $USER_TOKEN" | jq
curl -s "http://192.168.1.200:5000/api/abac/health" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

echo "=== Full Backend Test Completed ==="

# Step 13: Test User Attribute Changes and Private Key Regeneration
echo "=== Testing User Attribute Changes ==="

if [ ! -z "$ADMIN_TOKEN" ] && [ ! -z "$TEST_USER_ID" ]; then
  
  # Get current user info before changes
  echo "Getting current user info before attribute changes..."
  curl -s "http://192.168.1.200:5000/api/super-admin/users/$TEST_USER_ID" \
    -H "Authorization: Bearer $ADMIN_TOKEN" | jq
  
  # Check if user has private key before attribute change
  echo "Checking private key status before attribute change..."
  if [ ! -z "$USER_TOKEN" ]; then
    curl -s "http://192.168.1.167:5000/api/ca/user/private-key/check" \
      -H "Authorization: Bearer $USER_TOKEN" | jq
  fi
  
  # Update user attributes (this should deactivate old private key)
  echo "Updating user attributes (promoting to director with higher clearance)..."
  curl -s -X PUT "http://192.168.1.167:5000/api/super-admin/users/$TEST_USER_ID/attributes" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
      "attributes": {
        "role": "director",
        "department": "it",
        "clearance_level": "secret",
        "data_access": "super_admin",
        "employment_status": "active",
        "location": "hq_hcm"
      }
    }' | jq
  
  # Get updated user info
  echo "Getting updated user info after attribute changes..."
  curl -s "http://192.168.1.200:5000/api/super-admin/users/$TEST_USER_ID" \
    -H "Authorization: Bearer $ADMIN_TOKEN" | jq
  
  # Check private key status after attribute change (should be deactivated)
  echo "Checking private key status after attribute change..."
  if [ ! -z "$USER_TOKEN" ]; then
    curl -s "http://192.168.1.167:5000/api/ca/user/private-key/check" \
      -H "Authorization: Bearer $USER_TOKEN" | jq
  fi
  
  # User needs to regenerate private key with new attributes
  echo "User regenerating private key with new attributes..."
  if [ ! -z "$USER_TOKEN" ]; then
    curl -s -X POST "http://192.168.1.167:5000/api/ca/user/generate-private-key" \
      -H "Authorization: Bearer $USER_TOKEN" | jq
  fi
  
  # Verify new private key works
  echo "Verifying new private key status..."
  if [ ! -z "$USER_TOKEN" ]; then
    curl -s "http://192.168.1.200:5000/api/ca/user/private-key/check" \
      -H "Authorization: Bearer $USER_TOKEN" | jq
  fi
  
  # Test another attribute change with different values
  echo "Testing another attribute change (department transfer)..."
  curl -s -X PUT "http://192.168.1.200:5000/api/super-admin/users/$TEST_USER_ID/attributes" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
      "attributes": {
        "role": "director",
        "department": "security",
        "clearance_level": "top_secret",
        "data_access": "super_admin",
        "employment_status": "active",
        "location": "hq_hcm"
      }
    }' | jq
  
  # Again, user needs to regenerate key
  echo "User regenerating private key after department transfer..."
  if [ ! -z "$USER_TOKEN" ]; then
    curl -s -X POST "http://192.168.1.200:5000/api/ca/user/generate-private-key" \
      -H "Authorization: Bearer $USER_TOKEN" | jq
  fi
  
  # Test validation error with invalid attribute values
  echo "Testing attribute validation with invalid values..."
  curl -s -X PUT "http://192.168.1.200:5000/api/super-admin/users/$TEST_USER_ID/attributes" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
      "attributes": {
        "role": "invalid_role",
        "department": "invalid_dept"
      }
    }' | jq

fi

# Step 14: Test Password Change and Private Key Re-encryption
echo "=== Testing Password Change and Key Re-encryption ==="

if [ ! -z "$USER_TOKEN" ] && [ ! -z "$TEST_USER_ID" ]; then
  
  # Check current private key status
  echo "Checking private key before password change..."
  curl -s "http://192.168.1.200:5000/api/ca/user/private-key/check" \
    -H "Authorization: Bearer $USER_TOKEN" | jq
  
  # Change user password (this should re-encrypt the private key)
  echo "Changing user password (will re-encrypt private key)..."
  curl -s -X POST "http://192.168.1.200:5000/api/auth/change-password" \
    -H "Authorization: Bearer $USER_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
      "old_password": "Manager123!",
      "new_password": "NewManager456!"
    }' | jq
  
  # Login with new password to get new token
  echo "Logging in with new password..."
  NEW_USER_TOKEN=$(curl -s -X POST "http://192.168.1.200:5000/api/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"username\": \"$TEST_USER_ID\", \"password\": \"NewManager456!\"}" | \
    python3 -c "import json,sys; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)
  
  echo "New User Token: $NEW_USER_TOKEN"
  
  # Check private key status with new token (should still work)
  echo "Checking private key after password change..."
  if [ ! -z "$NEW_USER_TOKEN" ]; then
    curl -s "http://192.168.1.200:5000/api/ca/user/private-key/check" \
      -H "Authorization: Bearer $NEW_USER_TOKEN" | jq
  fi
  
  # Test file operations with re-encrypted key
  echo "Testing file operations with re-encrypted private key..."
  if [ ! -z "$NEW_USER_TOKEN" ]; then
    echo "Test content after password change" > test_after_pwd_change.txt
    
    curl -s -X POST "http://192.168.1.200:5000/api/files/upload" \
      -H "Authorization: Bearer $NEW_USER_TOKEN" \
      -F "file=@test_after_pwd_change.txt" \
      -F "access_policy=department:security AND clearance_level:top_secret" | jq
    
    rm -f test_after_pwd_change.txt
  fi

fi