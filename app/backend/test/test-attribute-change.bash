#!/bin/bash

# Test Attribute Change and Private Key Regeneration
SERVER_URL="http://localhost:5000"

echo "=========================================="
echo "Testing User Attribute Change & Key Regeneration"
echo "=========================================="

# Step 1: Admin login
echo "=== Step 1: Admin Login ==="
ADMIN_TOKEN=$(curl -s -X POST "$SERVER_URL/api/super-admin/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "superadmin1", "password": "Admin123!@#"}' | \
  python3 -c "import json,sys; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)

echo "Admin Token: $ADMIN_TOKEN"

# Step 2: User login
echo "=== Step 2: User Login ==="
USER_TOKEN=$(curl -s -X POST "$SERVER_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "22520001", "password": "User123!@#"}' | \
  python3 -c "import json,sys; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)

echo "User Token: $USER_TOKEN"
TEST_USER_ID="22520001"

# Step 3: Check current user attributes
echo "=== Step 3: Current User Info ==="
curl -s "$SERVER_URL/api/super-admin/users/$TEST_USER_ID" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.user.attributes // .attributes // "No attributes found"'

# Step 4: Check current private key status
echo "=== Step 4: Current Private Key Status ==="
curl -s "$SERVER_URL/api/ca/user/private-key/check" \
  -H "Authorization: Bearer $USER_TOKEN" | jq

# Step 5: Generate initial private key if needed
echo "=== Step 5: Generate Initial Private Key ==="
curl -s -X POST "$SERVER_URL/api/ca/user/generate-private-key" \
  -H "Authorization: Bearer $USER_TOKEN" | jq

# Step 6: Admin updates user attributes
echo "=== Step 6: Admin Updates User Attributes ==="
echo "Changing role from 'manager' to 'intern', clearance from 'confidential' to 'secret'..."
curl -s -X PUT "$SERVER_URL/api/super-admin/users/$TEST_USER_ID/attributes" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "attributes": {
      "role": "intern",
      "department": "hr", 
      "clearance_level": "secret",
      "data_access": "super_admin",
      "employment_status": "active",
      "location": "hq_hcm"
    }
  }' | jq

# Step 7: Check private key status after attribute change
echo "=== Step 7: Private Key Status After Attribute Change ==="
curl -s "$SERVER_URL/api/ca/user/private-key/check" \
  -H "Authorization: Bearer $USER_TOKEN" | jq

# Step 8: User regenerates private key with NEW attributes
echo "=== Step 8: User Regenerates Private Key (Should Use NEW Attributes) ==="
curl -s -X POST "$SERVER_URL/api/ca/user/generate-private-key" \
  -H "Authorization: Bearer $USER_TOKEN" | jq

# Step 9: Verify new private key has correct attributes
echo "=== Step 9: Verify New Private Key Has Updated Attributes ==="
curl -s "$SERVER_URL/api/ca/user/private-key/check" \
  -H "Authorization: Bearer $USER_TOKEN" | jq

# Step 10: Check all private keys in database (for admin verification)
echo "=== Step 10: Verify Old Keys Are Preserved (Admin Check) ==="
echo "This would require a database query to see deactivated keys..."

echo "=========================================="
echo "Test Completed!"
echo "=========================================="

echo ""
echo "🔍 What to verify:"
echo "1. Step 8 should show NEW attributes (intern, secret) not old ones (manager, confidential)"
echo "2. Step 9 should confirm the key has the updated attributes"
echo "3. Old keys should be deactivated but preserved in database for audit"
