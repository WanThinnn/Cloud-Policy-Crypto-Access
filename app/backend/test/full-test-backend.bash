# Step 1: Health Check
curl -s "http://192.168.1.2:5000/api/health" | jq
curl -X GET http://192.168.1.2:5000/api/health/ready | jq
curl -X GET http://192.168.1.2:5000/api/health/live | jq
# Step 2: SuperAdmin Login
curl -s -X POST "http://192.168.1.2:5000/api/super-admin/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "superadmin1",
    "password": "Admin123!@#"
  }' | jq

# Save admin token:
ADMIN_TOKEN=$(curl -s -X POST "http://192.168.1.2:5000/api/super-admin/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "superadmin1", "password": "Admin123!@#"}' | \
  python3 -c "import json,sys; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)

echo "Admin Token: $ADMIN_TOKEN"

# Step 3: ABE System Setup
# Check ABE status
curl -s "http://192.168.1.2:5000/api/ca/status" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

# Setup ABE (generate master key)
curl -s -X POST "http://192.168.1.2:5000/api/ca/setup" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" | jq

# Get public key
curl -s "http://192.168.1.2:5000/api/ca/public-key" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq


# Step 4: Create User 1 (IT Manager)
curl -s -X POST "http://192.168.1.2:5000/api/super-admin/users" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_data": {
      "email": "user123@company.com",
      "password": "User123!@#",
      "full_name": "IT Manager User"
    },
    "user_attributes": {
      "department": "it",
      "role": "manager",
      "clearance_level": "high",
      "data_access": "confidential"
    }
  }' | jq

# Save User 1 ID:
USER1_ID=$(curl -s -X GET "http://192.168.1.2:5000/api/super-admin/users" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_data": {
      "email": "user123@company.com",
      "password": "User123!@#",
      "full_name": "IT Manager User 2"
    },
    "user_attributes": {
      "department": "it",
      "role": "manager", 
      "clearance_level": "high",
      "data_access": "confidential"
    }
  }' | python3 -c "import json,sys; print(json.load(sys.stdin).get('user',{}).get('id',''))" 2>/dev/null)

echo "User 1 ID: $USER1_ID"

# Step 5: Create User 2 (HR Staff)
curl -s -X POST "http://192.168.1.2:5000/api/super-admin/users" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_data": {
      "email": "user345@company.com",
      "password": "User123!@#", 
      "full_name": "HR Staff User"
    },
    "user_attributes": {
      "department": "hr",
      "role": "hr_staff",
      "clearance_level": "medium",
      "data_access": "internal"
    }
  }' | jq

# Save User 2 ID:
export USER2_ID=22520006
echo "User 2 ID: $USER2_ID"


# Step 6: User 1 Login
curl -s -X POST "http://192.168.1.2:5000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "'$USER1_ID'",
    "password": "User123!@#"
  }' | jq


# Save User 1 Token:
USER1_TOKEN=$(curl -s -X POST "http://192.168.1.2:5000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "'$USER1_ID'", "password": "User123!@#"}' | \
  python3 -c "import json,sys; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)

echo "User 1 Token: ${USER1_TOKEN:0:50}..."


# Step 7: User 2 Login
curl -s -X POST "http://192.168.1.2:5000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "'$USER2_ID'",
    "password": "User123!@#"
  }' | jq

# Save User 2 Token:
USER2_TOKEN=$(curl -s -X POST "http://192.168.1.2:5000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "'$USER2_ID'", "password": "User123!@#"}' | \
  python3 -c "import json,sys; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)

echo "User 2 Token: ${USER2_TOKEN:0:50}..."

# Step 8: Check User Sessions
# User 1 session
curl -s "http://192.168.1.2:5000/api/auth/session" \
  -H "Authorization: Bearer $USER1_TOKEN" | jq

# User 2 session
curl -s "http://192.168.1.2:5000/api/auth/session" \
  -H "Authorization: Bearer $USER2_TOKEN" | jq


# Step 9: Generate Private Keys (First Time)
# User 1 generate private key
echo "=== User 1 Generate Private Key ==="
curl -s -X POST "http://192.168.1.2:5000/api/ca/user/generate-private-key" \
  -H "Authorization: Bearer $USER1_TOKEN" | jq

# User 2 generate private key
echo "=== User 2 Generate Private Key ==="
curl -s -X POST "http://192.168.1.2:5000/api/ca/user/generate-private-key" \
  -H "Authorization: Bearer $USER2_TOKEN" | jq

# Step 10: Check Private Key Status
# User 1 private key status
curl -s "http://192.168.1.2:5000/api/ca/user/private-key/check" \
  -H "Authorization: Bearer $USER1_TOKEN" | jq

# User 2 private key status
curl -s "http://192.168.1.2:5000/api/ca/user/private-key/check" \
  -H "Authorization: Bearer $USER2_TOKEN" | jq

# Step 11: Try Regenerate Private Keys (Should Keep Existing)
# User 1 try regenerate
echo "=== User 1 Try Regenerate (Should Keep) ==="
curl -s -X POST "http://192.168.1.2:5000/api/ca/user/generate-private-key" \
  -H "Authorization: Bearer $USER1_TOKEN" | jq

# User 2 try regenerate  
echo "=== User 2 Try Regenerate (Should Keep) ==="
curl -s -X POST "http://192.168.1.2:5000/api/ca/user/generate-private-key" \
  -H "Authorization: Bearer $USER2_TOKEN" | jq

# Step 12: Update User Attributes
# Update User 1 to top_secret clearance
echo "=== Update User 1 Attributes ==="
curl -s -X PUT "http://192.168.1.2:5000/api/super-admin/users/$USER1_ID/attributes" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "attributes": {
      "department": "it",
      "role": "manager",
      "clearance_level": "top_secret",
      "data_access": "top_secret"
    }
  }' | jq

# Update User 2 to high clearance
echo "=== Update User 2 Attributes ==="
curl -s -X PUT "http://192.168.1.2:5000/api/super-admin/users/$USER2_ID/attributes" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "attributes": {
      "department": "hr", 
      "role": "hr_staff",
      "clearance_level": "high",
      "data_access": "restricted"
    }
  }' | jq

# Step 13: Users Re-login with Updated Attributes
# User 1 re-login
NEW_USER1_TOKEN=$(curl -s -X POST "http://192.168.1.2:5000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "'$USER1_ID'", "password": "User123!@#"}' | \
  python3 -c "import json,sys; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)

echo "User 1 New Token: ${NEW_USER1_TOKEN:0:50}..."

# User 2 re-login
NEW_USER2_TOKEN=$(curl -s -X POST "http://192.168.1.2:5000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "'$USER2_ID'", "password": "User123!@#"}' | \
  python3 -c "import json,sys; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)

echo "User 2 New Token: ${NEW_USER2_TOKEN:0:50}..."

# Step 14: Check Updated Sessions
# User 1 updated session
curl -s "http://192.168.1.2:5000/api/auth/session" \
  -H "Authorization: Bearer $NEW_USER1_TOKEN" | jq '.user.attributes'

# User 2 updated session
curl -s "http://192.168.1.2:5000/api/auth/session" \
  -H "Authorization: Bearer $NEW_USER2_TOKEN" | jq '.user.attributes'

# Step 15: Generate Private Keys with Updated Attributes
# User 1 generate key with updated attributes (should generate new)
echo "=== User 1 Generate Key with Updated Attributes ==="
curl -s -X POST "http://192.168.1.2:5000/api/ca/user/generate-private-key" \
  -H "Authorization: Bearer $NEW_USER1_TOKEN" | jq

# User 2 generate key with updated attributes (should generate new)
echo "=== User 2 Generate Key with Updated Attributes ==="
curl -s -X POST "http://192.168.1.2:5000/api/ca/user/generate-private-key" \
  -H "Authorization: Bearer $NEW_USER2_TOKEN" | jq


# Step 16: Create Test Files
# Create test files
echo "TOP SECRET IT DOCUMENT - Only accessible by IT staff with top_secret clearance" > file1_topsecret.txt
echo "HR DOCUMENT - Accessible by HR staff with high clearance or above" > file2_hr.txt

# Step 17: Upload Files with Different Policies
# File 1: Only for top_secret IT (User 2 cannot access)
echo "=== Upload File 1 (Restrictive Policy) ==="
curl -s -X POST "http://192.168.1.2:5000/api/files/upload" \
  -H "Authorization: Bearer $NEW_USER1_TOKEN" \
  -F "file=@file1_topsecret.txt" \
  -F "access_policy=clearance_level:top_secret AND department:it" \
  -F "description=Top Secret IT Document" | jq

# Save File 1 ID
export FILE1_ID=
echo "File 1 ID: $FILE1_ID"

# File 2: For HR staff with high clearance (User 2 can access)  
echo "=== Upload File 2 (Accessible Policy) ==="
curl -s -X POST "http://192.168.1.2:5000/api/files/upload" \
  -H "Authorization: Bearer $NEW_USER1_TOKEN" \
  -F "file=@file2_hr.txt" \
  -F "access_policy=department:hr AND clearance_level:high" \
  -F "description=HR Document for High Clearance" | jq

# Save File 2 ID
export FILE2_ID=
echo "File 2 ID: $FILE2_ID"

# Step 18: List Files
# User 1 list own files
echo "=== User 1 Files (Owner) ==="
curl -s "http://192.168.1.2:5000/api/files/?include_shared=false" \
  -H "Authorization: Bearer $NEW_USER1_TOKEN" | jq '.files[] | {filename, file_id, access_policy}'

# User 2 list accessible files
echo "=== User 2 Accessible Files ==="
curl -s "http://192.168.1.2:5000/api/files/?include_shared=true" \
  -H "Authorization: Bearer $NEW_USER2_TOKEN" | jq '.files[] | {filename, file_id, is_owner}'


# Step 19: Test File Downloads
# User 2 try download File 1 (should be DENIED)
echo "=== User 2 Download File 1 (Should be DENIED) ==="
curl -s "http://192.168.1.2:5000/api/files/$FILE1_ID/download" \
  -H "Authorization: Bearer $NEW_USER2_TOKEN" | jq

# User 2 try download File 2 (should be ALLOWED)
echo "=== User 2 Download File 2 (Should be ALLOWED) ==="
curl -s "http://192.168.1.2:5000/api/files/$FILE2_ID/download" \
  -H "Authorization: Bearer $NEW_USER2_TOKEN"

# Step 20: Test File Info Access
# User 2 get File 1 info (might be denied)
curl -s "http://192.168.1.2:5000/api/files/$FILE1_ID" \
  -H "Authorization: Bearer $NEW_USER2_TOKEN" | jq

# User 2 get File 2 info (should be allowed)
curl -s "http://192.168.1.2:5000/api/files/$FILE2_ID" \
  -H "Authorization: Bearer $NEW_USER2_TOKEN" | jq

# Step 21: Cleanup
# Remove test files
rm -f file1_topsecret.txt file2_hr.txt

echo "=== TEST COMPLETE ==="
echo "Users created: $USER1_ID (IT Manager), $USER2_ID (HR Staff)"
echo "Files uploaded: $FILE1_ID (restrictive), $FILE2_ID (accessible)"

# ========================================
# ADDITIONAL TEST CASES - MISSING SCENARIOS
# ========================================

echo ""
echo "🧪 ADDITIONAL TEST CASES"
echo "========================="

# Test Case A: Super Admin Management Functions
echo ""
echo "=== A. Super Admin Management Tests ==="

# A1: List all users
echo "A1. List all users:"
curl -s "http://192.168.1.2:5000/api/super-admin/users" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.users | length'

# A2: Get user details
echo "A2. Get User 1 details:"
curl -s "http://192.168.1.2:5000/api/super-admin/users/$USER1_ID" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.user | {id, username, attributes}'

# A3: System statistics
echo "A3. System statistics:"
curl -s "http://192.168.1.2:5000/api/super-admin/stats" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

# A4: Get attribute schema
echo "A4. Attribute schema:"
curl -s "http://192.168.1.2:5000/api/super-admin/schema/attributes" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

# Test Case B: Authentication Edge Cases
echo ""
echo "=== B. Authentication Edge Cases ==="

# B1: Test user profile endpoint
echo "B1. User 1 profile:"
curl -s "http://192.168.1.2:5000/api/auth/profile" \
  -H "Authorization: Bearer $NEW_USER1_TOKEN" | jq '.profile | {username, full_name, attributes}'

# B2: Invalid login attempt
echo "B2. Invalid login (should fail):"
curl -s -X POST "http://192.168.1.2:5000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "'$USER1_ID'",
    "password": "WrongPassword"
  }' | jq '.success'

# B3: Logout test
echo "B3. User 1 logout:"
curl -s -X POST "http://192.168.1.2:5000/api/auth/logout" \
  -H "Authorization: Bearer $USER1_TOKEN" | jq

# Test Case C: Health and System Info
echo ""
echo "=== C. System Health Tests ==="

# C1: Root API info
echo "C1. Root API info:"
curl -s "http://192.168.1.2:5000/" | jq '.version'

# C2: ABE system info
echo "C2. ABE system info:"
curl -s "http://192.168.1.2:5000/api/abe/" | jq '.service'

# C3: ABE health check
echo "C3. ABE health check:"
curl -s "http://192.168.1.2:5000/api/abe/health" | jq '.status'

# C4: CA health check
echo "C4. CA health check:"
curl -s "http://192.168.1.2:5000/api/ca/health" | jq '.status'

# C5: Files health check
echo "C5. Files health check:"
curl -s "http://192.168.1.2:5000/api/files/health" \
  -H "Authorization: Bearer $NEW_USER1_TOKEN" | jq '.status'

# Test Case D: ABAC Policy Tests
echo ""
echo "=== D. ABAC Policy Tests ==="

# D1: Get existing policies
echo "D1. Current ABAC policies:"
curl -s "http://192.168.1.2:5000/api/abac/policies" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

# D2: Check access for specific user
echo "D2. Check User 1 access to IT resources:"
curl -s -X POST "http://192.168.1.2:5000/api/abac/check-access" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_attributes": {
      "department": "it",
      "role": "manager",
      "clearance_level": "top_secret"
    },
    "resource": "confidential_it_data",
    "action": "read"
  }' | jq

# D3: ABAC health check
echo "D3. ABAC health check:"
curl -s "http://192.168.1.2:5000/api/abac/health" | jq

# Test Case E: File Management Advanced
echo ""
echo "=== E. File Management Advanced Tests ==="

# E1: List ABE files in upload directory
echo "E1. ABE files in system:"
curl -s "http://192.168.1.2:5000/api/abe/files" | jq '.total'

# E2: Get file access logs (if files exist)
if [ ! -z "$FILE1_ID" ]; then
  echo "E2. File 1 access logs:"
  curl -s "http://192.168.1.2:5000/api/files/$FILE1_ID/access-logs" \
    -H "Authorization: Bearer $NEW_USER1_TOKEN" | jq '.logs | length'
fi

# Test Case F: ABE Direct Encryption/Decryption
echo ""
echo "=== F. Direct ABE Operations ==="

# F1: Create test file for direct ABE encryption
echo "Direct ABE test content - Only for IT managers" > test_direct_abe.txt

# F2: Direct ABE encryption
echo "F1. Direct ABE encryption test:"
curl -s -X POST "http://192.168.1.2:5000/api/abe/encrypt" \
  -H "Authorization: Bearer $NEW_USER1_TOKEN" \
  -F "file=@test_direct_abe.txt" \
  -F "policy=department:it AND role:manager" | jq '.success'

# F3: Clean up direct test file
rm -f test_direct_abe.txt

# Test Case G: User Deactivation/Activation
echo ""
echo "=== G. User Management Advanced ==="

# G1: Create a test user to deactivate
TEST_USER_ID=$(curl -s -X POST "http://192.168.1.2:5000/api/super-admin/users" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_data": {
      "email": "test.user@company.com",
      "password": "Test123!@#",
      "full_name": "Test User"
    },
    "user_attributes": {
      "department": "test",
      "role": "tester",
      "clearance_level": "low",
      "data_access": "public"
    }
  }' | python3 -c "import json,sys; print(json.load(sys.stdin).get('user',{}).get('id',''))" 2>/dev/null)

if [ ! -z "$TEST_USER_ID" ]; then
  echo "G1. Created test user: $TEST_USER_ID"
  
  # G2: Deactivate user
  echo "G2. Deactivating test user:"
  curl -s -X POST "http://192.168.1.2:5000/api/super-admin/users/$TEST_USER_ID/deactivate" \
    -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.success'
  
  # G3: Try login with deactivated user (should fail)
  echo "G3. Login attempt with deactivated user (should fail):"
  curl -s -X POST "http://192.168.1.2:5000/api/auth/login" \
    -H "Content-Type: application/json" \
    -d '{
      "username": "'$TEST_USER_ID'",
      "password": "Test123!@#"
    }' | jq '.success'
  
  # G4: Reactivate user
  echo "G4. Reactivating test user:"
  curl -s -X POST "http://192.168.1.2:5000/api/super-admin/users/$TEST_USER_ID/activate" \
    -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.success'
fi

# Test Case H: Error Handling Tests
echo ""
echo "=== H. Error Handling Tests ==="

# H1: Access without authentication
echo "H1. Unauthenticated access (should fail):"
curl -s "http://192.168.1.2:5000/api/super-admin/users" | jq '.error'

# H2: Invalid endpoint
echo "H2. Invalid endpoint (should 404):"
curl -s "http://192.168.1.2:5000/api/nonexistent/endpoint" | jq

# H3: Malformed JSON request
echo "H3. Malformed JSON (should fail):"
curl -s -X POST "http://192.168.1.2:5000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d 'invalid json' | jq

echo ""
echo "🎉 COMPREHENSIVE TEST SUITE COMPLETED!"
echo "====================================="
echo "Main Users: $USER1_ID (IT Manager), $USER2_ID (HR Staff)"
echo "Test User: $TEST_USER_ID"
echo "Files: $FILE1_ID (restrictive), $FILE2_ID (accessible)"