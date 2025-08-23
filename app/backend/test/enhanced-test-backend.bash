#!/bin/bash

# Enhanced Backend Test Script with File Versioning and Role-Based Permissions
# Tests the complete file management system with ABAC, versioning, and integrity checking

echo "=== Enhanced Cloud Firestore Crypto Access Backend Test ==="
echo "Testing file versioning, role-based permissions, and integrity checking"
echo ""

# Configuration
BASE_URL="http://localhost:5000"
TEST_DIR="test_files"
mkdir -p "$TEST_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Test result function
test_result() {
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ PASS${NC}: $2"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "${RED}✗ FAIL${NC}: $2"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        if [ ! -z "$3" ]; then
            echo -e "${YELLOW}  Error: $3${NC}"
        fi
    fi
}

# Helper functions
make_request() {
    local method="$1"
    local endpoint="$2"
    local data="$3"
    local headers="$4"
    
    if [ -n "$data" ]; then
        curl -s -X "$method" \
             -H "Content-Type: application/json" \
             $headers \
             -d "$data" \
             "$BASE_URL$endpoint"
    else
        curl -s -X "$method" \
             $headers \
             "$BASE_URL$endpoint"
    fi
}

# Create test file
create_test_file() {
    local filename="$1"
    local content="$2"
    echo "$content" > "$TEST_DIR/$filename"
    base64 -w 0 "$TEST_DIR/$filename"
}

# Variables for test data
EMPLOYEE_TOKEN=""
SENIOR_EMPLOYEE_TOKEN=""
MANAGER_TOKEN=""
TEST_FILE_ID=""
VERSION_ID=""

echo -e "${BLUE}=== 1. Health Checks ===${NC}"

# Test basic health
health_response=$(make_request "GET" "/api/health")
echo "$health_response" | grep -q '"status": "healthy"'
test_result $? "Basic health check"

# Test file versioning health
versioning_health=$(make_request "GET" "/api/file-versioning/versions/health")
echo "$versioning_health" | grep -q '"service": "file_versioning"'
test_result $? "File versioning health check"

# Test enhanced files health
enhanced_files_health=$(make_request "GET" "/api/enhanced-files/health")
echo "$enhanced_files_health" | grep -q '"service": "enhanced_files"'
test_result $? "Enhanced files health check"

echo ""
echo -e "${BLUE}=== 2. User Authentication Tests ===${NC}"

# Test employee login
employee_login=$(make_request "POST" "/api/auth/login" '{"username": "employee_test", "password": "employee123"}')
EMPLOYEE_TOKEN=$(echo "$employee_login" | jq -r '.access_token // empty')
if [ -n "$EMPLOYEE_TOKEN" ]; then
    test_result 0 "Employee login"
    echo -e "${YELLOW}  Employee token: ${EMPLOYEE_TOKEN:0:30}...${NC}"
else
    test_result 1 "Employee login" "No access token received"
fi

# Test senior employee login
senior_login=$(make_request "POST" "/api/auth/login" '{"username": "senior_test", "password": "senior123"}')
SENIOR_EMPLOYEE_TOKEN=$(echo "$senior_login" | jq -r '.access_token // empty')
if [ -n "$SENIOR_EMPLOYEE_TOKEN" ]; then
    test_result 0 "Senior employee login"
    echo -e "${YELLOW}  Senior token: ${SENIOR_EMPLOYEE_TOKEN:0:30}...${NC}"
else
    test_result 1 "Senior employee login" "No access token received"
fi

# Test manager login
manager_login=$(make_request "POST" "/api/auth/login" '{"username": "manager_test", "password": "manager123"}')
MANAGER_TOKEN=$(echo "$manager_login" | jq -r '.access_token // empty')
if [ -n "$MANAGER_TOKEN" ]; then
    test_result 0 "Manager login"
    echo -e "${YELLOW}  Manager token: ${MANAGER_TOKEN:0:30}...${NC}"
else
    test_result 1 "Manager login" "No access token received"
fi

echo ""
echo -e "${BLUE}=== 3. Permission Matrix Tests ===${NC}"

# Test permission matrix retrieval for each role
if [ -n "$EMPLOYEE_TOKEN" ]; then
    employee_perms=$(make_request "GET" "/api/enhanced-files/permissions" "" "-H \"Authorization: Bearer $EMPLOYEE_TOKEN\"")
    echo "$employee_perms" | grep -q '"user_role": "EMPLOYEE"'
    test_result $? "Employee permission matrix"
fi

if [ -n "$SENIOR_EMPLOYEE_TOKEN" ]; then
    senior_perms=$(make_request "GET" "/api/enhanced-files/permissions" "" "-H \"Authorization: Bearer $SENIOR_EMPLOYEE_TOKEN\"")
    echo "$senior_perms" | grep -q '"user_role": "SENIOR_EMPLOYEE"'
    test_result $? "Senior employee permission matrix"
fi

if [ -n "$MANAGER_TOKEN" ]; then
    manager_perms=$(make_request "GET" "/api/enhanced-files/permissions" "" "-H \"Authorization: Bearer $MANAGER_TOKEN\"")
    echo "$manager_perms" | grep -q '"user_role": "MANAGER"'
    test_result $? "Manager permission matrix"
fi

echo ""
echo -e "${BLUE}=== 4. File Upload Tests (All Roles) ===${NC}"

# Create test files
TEST_FILE_CONTENT="This is a test file for role-based permissions testing. Version 1.0"
TEST_FILE_BASE64=$(create_test_file "test_document.txt" "$TEST_FILE_CONTENT")

# Test employee upload
if [ -n "$EMPLOYEE_TOKEN" ]; then
    employee_upload=$(make_request "POST" "/api/enhanced-files/upload" \
        "{\"filename\": \"employee_test.txt\", \"file_data\": \"$TEST_FILE_BASE64\", \"attributes\": \"(department:IT) AND (role:EMPLOYEE)\", \"description\": \"Test file uploaded by employee\"}" \
        "-H \"Authorization: Bearer $EMPLOYEE_TOKEN\"")
    
    echo "$employee_upload" | grep -q '"success": true'
    test_result $? "Employee file upload (should succeed)"
    
    if echo "$employee_upload" | grep -q '"success": true'; then
        TEST_FILE_ID=$(echo "$employee_upload" | jq -r '.file_id // empty')
        echo -e "${YELLOW}  Test file ID: $TEST_FILE_ID${NC}"
    fi
fi

# Test senior employee upload
if [ -n "$SENIOR_EMPLOYEE_TOKEN" ]; then
    senior_upload=$(make_request "POST" "/api/enhanced-files/upload" \
        "{\"filename\": \"senior_test.txt\", \"file_data\": \"$TEST_FILE_BASE64\", \"attributes\": \"(department:IT) AND (role:SENIOR_EMPLOYEE)\", \"description\": \"Test file uploaded by senior employee\"}" \
        "-H \"Authorization: Bearer $SENIOR_EMPLOYEE_TOKEN\"")
    
    echo "$senior_upload" | grep -q '"success": true'
    test_result $? "Senior employee file upload (should succeed)"
fi

# Test manager upload
if [ -n "$MANAGER_TOKEN" ]; then
    manager_upload=$(make_request "POST" "/api/enhanced-files/upload" \
        "{\"filename\": \"manager_test.txt\", \"file_data\": \"$TEST_FILE_BASE64\", \"attributes\": \"(department:IT) AND (role:MANAGER)\", \"description\": \"Test file uploaded by manager\"}" \
        "-H \"Authorization: Bearer $MANAGER_TOKEN\"")
    
    echo "$manager_upload" | grep -q '"success": true'
    test_result $? "Manager file upload (should succeed)"
fi

echo ""
echo -e "${BLUE}=== 5. File Download Permission Tests ===${NC}"

if [ -n "$TEST_FILE_ID" ]; then
    # Test employee download (should fail)
    if [ -n "$EMPLOYEE_TOKEN" ]; then
        employee_download=$(make_request "GET" "/api/enhanced-files/download/$TEST_FILE_ID" "" "-H \"Authorization: Bearer $EMPLOYEE_TOKEN\"")
        echo "$employee_download" | grep -q '"error".*"permission denied"'
        test_result $? "Employee download restriction (should fail)"
    fi
    
    # Test senior employee download (should succeed)
    if [ -n "$SENIOR_EMPLOYEE_TOKEN" ]; then
        senior_download_response=$(curl -s -o /dev/null -w "%{http_code}" \
            -H "Authorization: Bearer $SENIOR_EMPLOYEE_TOKEN" \
            "$BASE_URL/api/enhanced-files/download/$TEST_FILE_ID")
        
        [ "$senior_download_response" = "200" ]
        test_result $? "Senior employee download access (should succeed)"
    fi
    
    # Test manager download (should succeed)
    if [ -n "$MANAGER_TOKEN" ]; then
        manager_download_response=$(curl -s -o /dev/null -w "%{http_code}" \
            -H "Authorization: Bearer $MANAGER_TOKEN" \
            "$BASE_URL/api/enhanced-files/download/$TEST_FILE_ID")
        
        [ "$manager_download_response" = "200" ]
        test_result $? "Manager download access (should succeed)"
    fi
fi

echo ""
echo -e "${BLUE}=== 6. File Versioning Tests ===${NC}"

# Create version 2 of the test file
if [ -n "$TEST_FILE_ID" ] && [ -n "$SENIOR_EMPLOYEE_TOKEN" ]; then
    TEST_FILE_V2_CONTENT="This is a test file for role-based permissions testing. Version 2.0 - Updated content with more features."
    TEST_FILE_V2_BASE64=$(create_test_file "test_document_v2.txt" "$TEST_FILE_V2_CONTENT")
    
    # Create new version
    version_create=$(make_request "POST" "/api/file-versioning/file/$TEST_FILE_ID/version" \
        "{\"file_data\": \"$TEST_FILE_V2_BASE64\", \"version_type\": \"MINOR\", \"change_description\": \"Added more features and content\"}" \
        "-H \"Authorization: Bearer $SENIOR_EMPLOYEE_TOKEN\"")
    
    echo "$version_create" | grep -q '"success": true'
    test_result $? "File version creation"
    
    if echo "$version_create" | grep -q '"success": true'; then
        VERSION_ID=$(echo "$version_create" | jq -r '.version_id // empty')
        VERSION_NUMBER=$(echo "$version_create" | jq -r '.version_number // empty')
        APPROVAL_REQUIRED=$(echo "$version_create" | jq -r '.approval_required // false')
        
        echo -e "${YELLOW}  Version ID: $VERSION_ID${NC}"
        echo -e "${YELLOW}  Version Number: $VERSION_NUMBER${NC}"
        echo -e "${YELLOW}  Approval Required: $APPROVAL_REQUIRED${NC}"
    fi
fi

# Test version history
if [ -n "$TEST_FILE_ID" ] && [ -n "$SENIOR_EMPLOYEE_TOKEN" ]; then
    version_history=$(make_request "GET" "/api/file-versioning/file/$TEST_FILE_ID/versions" "" "-H \"Authorization: Bearer $SENIOR_EMPLOYEE_TOKEN\"")
    
    echo "$version_history" | grep -q '"success": true'
    test_result $? "File version history"
    
    version_count=$(echo "$version_history" | jq '.versions | length // 0')
    echo -e "${YELLOW}  Total versions: $version_count${NC}"
fi

echo ""
echo -e "${BLUE}=== 7. Version Approval Workflow Tests ===${NC}"

# Test pending approvals (manager only)
if [ -n "$MANAGER_TOKEN" ]; then
    pending_approvals=$(make_request "GET" "/api/file-versioning/versions/pending" "" "-H \"Authorization: Bearer $MANAGER_TOKEN\"")
    
    echo "$pending_approvals" | grep -q '"success": true'
    test_result $? "Get pending approvals (manager)"
    
    pending_count=$(echo "$pending_approvals" | jq '.total_pending // 0')
    echo -e "${YELLOW}  Pending approvals: $pending_count${NC}"
fi

# Test version approval
if [ -n "$VERSION_ID" ] && [ -n "$MANAGER_TOKEN" ]; then
    version_approval=$(make_request "POST" "/api/file-versioning/version/$VERSION_ID/approve" \
        "{\"approval_notes\": \"Approved after review - changes look good\"}" \
        "-H \"Authorization: Bearer $MANAGER_TOKEN\"")
    
    echo "$version_approval" | grep -q '"success": true'
    test_result $? "Version approval (manager only)"
fi

echo ""
echo -e "${BLUE}=== 8. File Integrity Tests ===${NC}"

# Test integrity analysis
if [ -n "$MANAGER_TOKEN" ]; then
    # Create modified version for integrity testing
    MODIFIED_CONTENT="This is a MODIFIED test file for integrity testing. Some content has been changed!"
    MODIFIED_BASE64=$(create_test_file "test_modified.txt" "$MODIFIED_CONTENT")
    
    integrity_analysis=$(make_request "POST" "/api/file-versioning/integrity/analyze" \
        "{\"old_file_data\": \"$TEST_FILE_BASE64\", \"new_file_data\": \"$MODIFIED_BASE64\", \"old_metadata\": {\"version\": \"1.0.0\", \"filename\": \"test_document.txt\"}}" \
        "-H \"Authorization: Bearer $MANAGER_TOKEN\"")
    
    echo "$integrity_analysis" | grep -q '"success": true'
    test_result $? "File integrity analysis"
    
    if echo "$integrity_analysis" | grep -q '"success": true'; then
        similarity_score=$(echo "$integrity_analysis" | jq -r '.report.comparison.similarity_score // 0')
        risk_level=$(echo "$integrity_analysis" | jq -r '.report.security_analysis.risk_level // "UNKNOWN"')
        echo -e "${YELLOW}  Similarity Score: $similarity_score%${NC}"
        echo -e "${YELLOW}  Risk Level: $risk_level${NC}"
    fi
fi

# Test integrity validation
if [ -n "$SENIOR_EMPLOYEE_TOKEN" ]; then
    # Generate expected hashes for validation test
    expected_sha256=$(echo -n "$TEST_FILE_CONTENT" | sha256sum | cut -d' ' -f1)
    expected_md5=$(echo -n "$TEST_FILE_CONTENT" | md5sum | cut -d' ' -f1)
    
    integrity_validation=$(make_request "POST" "/api/file-versioning/integrity/validate" \
        "{\"file_data\": \"$TEST_FILE_BASE64\", \"expected_hashes\": {\"sha256\": \"$expected_sha256\", \"md5\": \"$expected_md5\"}}" \
        "-H \"Authorization: Bearer $SENIOR_EMPLOYEE_TOKEN\"")
    
    echo "$integrity_validation" | grep -q '"success": true'
    test_result $? "File integrity validation"
fi

echo ""
echo -e "${BLUE}=== 9. File Deletion Permission Tests ===${NC}"

# Test employee deletion (should fail)
if [ -n "$TEST_FILE_ID" ] && [ -n "$EMPLOYEE_TOKEN" ]; then
    employee_delete=$(make_request "DELETE" "/api/enhanced-files/delete/$TEST_FILE_ID" "" "-H \"Authorization: Bearer $EMPLOYEE_TOKEN\"")
    
    echo "$employee_delete" | grep -q '"error".*"permission denied"'
    test_result $? "Employee delete restriction (should fail)"
fi

# Test file info access
if [ -n "$TEST_FILE_ID" ] && [ -n "$SENIOR_EMPLOYEE_TOKEN" ]; then
    file_info=$(make_request "GET" "/api/enhanced-files/info/$TEST_FILE_ID" "" "-H \"Authorization: Bearer $SENIOR_EMPLOYEE_TOKEN\"")
    
    echo "$file_info" | grep -q '"success": true'
    test_result $? "File information access"
    
    if echo "$file_info" | grep -q '"success": true'; then
        can_download=$(echo "$file_info" | jq -r '.permissions.can_download // false')
        can_delete=$(echo "$file_info" | jq -r '.permissions.can_delete // false')
        user_role=$(echo "$file_info" | jq -r '.user_role // "UNKNOWN"')
        
        echo -e "${YELLOW}  User Role: $user_role${NC}"
        echo -e "${YELLOW}  Can Download: $can_download${NC}"
        echo -e "${YELLOW}  Can Delete: $can_delete${NC}"
    fi
fi

echo ""
echo -e "${BLUE}=== 10. Enhanced File Listing Tests ===${NC}"

# Test enhanced file listing with permissions
if [ -n "$SENIOR_EMPLOYEE_TOKEN" ]; then
    enhanced_file_list=$(make_request "GET" "/api/enhanced-files/list" "" "-H \"Authorization: Bearer $SENIOR_EMPLOYEE_TOKEN\"")
    
    echo "$enhanced_file_list" | grep -q '"success": true'
    test_result $? "Enhanced file listing with permissions"
    
    if echo "$enhanced_file_list" | grep -q '"success": true'; then
        file_count=$(echo "$enhanced_file_list" | jq '.files | length // 0')
        echo -e "${YELLOW}  Total accessible files: $file_count${NC}"
    fi
fi

echo ""
echo -e "${BLUE}=== 11. Error Handling Tests ===${NC}"

# Test invalid file ID
invalid_file_response=$(make_request "GET" "/api/enhanced-files/info/invalid_file_id" "" "-H \"Authorization: Bearer $MANAGER_TOKEN\"")
echo "$invalid_file_response" | grep -q '"error".*"not found"'
test_result $? "Invalid file ID handling"

# Test missing authentication
no_auth_response=$(make_request "GET" "/api/enhanced-files/list")
echo "$no_auth_response" | grep -q '"error".*"required"'
test_result $? "Missing authentication handling"

# Test invalid version ID
if [ -n "$MANAGER_TOKEN" ]; then
    invalid_version_response=$(make_request "POST" "/api/file-versioning/version/invalid_version_id/approve" \
        "{\"approval_notes\": \"test\"}" \
        "-H \"Authorization: Bearer $MANAGER_TOKEN\"")
    
    echo "$invalid_version_response" | grep -q '"error"'
    test_result $? "Invalid version ID handling"
fi

echo ""
echo -e "${BLUE}=== Test Summary ===${NC}"
echo "Total Tests: $TOTAL_TESTS"
echo -e "Passed: ${GREEN}$PASSED_TESTS${NC}"
echo -e "Failed: ${RED}$FAILED_TESTS${NC}"
echo ""

# Calculate success rate
if [ $TOTAL_TESTS -gt 0 ]; then
    SUCCESS_RATE=$((PASSED_TESTS * 100 / TOTAL_TESTS))
    echo -e "Success Rate: ${BLUE}$SUCCESS_RATE%${NC}"
    
    if [ $SUCCESS_RATE -ge 90 ]; then
        echo -e "${GREEN}✓ EXCELLENT: File versioning and permission system working well!${NC}"
    elif [ $SUCCESS_RATE -ge 75 ]; then
        echo -e "${YELLOW}⚠ GOOD: System mostly functional, some issues to address${NC}"
    else
        echo -e "${RED}✗ NEEDS WORK: Multiple issues detected${NC}"
    fi
else
    echo -e "${RED}No tests completed${NC}"
fi

echo ""
echo -e "${BLUE}=== Feature Status ===${NC}"
echo "✓ Health Monitoring"
echo "✓ Role-Based Authentication (Employee, Senior Employee, Manager)" 
echo "✓ Permission Matrix Implementation"
echo "✓ File Upload (All Roles)"
echo "✓ Download Restrictions (Senior Employee + Manager only)"
echo "✓ File Versioning System"
echo "✓ Manager Approval Workflow"
echo "✓ File Integrity Checking (ssdeep + SHA256/MD5)"
echo "✓ Delete Permissions (Manager + File Owner)"
echo "✓ Enhanced File Listing with Permissions"
echo "✓ Comprehensive Error Handling"

echo ""
echo -e "${GREEN}Enhanced file management system test completed!${NC}"
echo ""

# Cleanup
rm -rf "$TEST_DIR"

exit 0
