# API Specifications & Workflows

This document describes how the **Cloud-Policy-Crypto-Access** system operates, the authentication flow, the security architecture (CP-ABE combined with ABAC), and the list of main REST API endpoints.

## 1. Core Workflows

### 1.1. Authentication Flow
The system uses JWT (JSON Web Token) combined with HttpOnly Cookies to secure sessions and prevent XSS attacks.
1. **Login**: The client sends a request containing `username` and `password` to `/api/auth/login/`.
2. **Response**: 
   - The server authenticates the credentials.
   - Returns basic user information in the response body.
   - Attaches `access_token` and `refresh_token` to the HTTP response headers via the `Set-Cookie` mechanism with security flags (HttpOnly, Secure, SameSite=Lax).
3. **API Calls**: For subsequent requests to the system (e.g., upload/download file, fetch data), the browser (or client) will automatically attach the Cookie containing the tokens without needing JavaScript `localStorage` intervention.
4. **CSRF Protection**: Data-modifying operations (POST, PUT, DELETE) must include the `X-CSRFToken` header retrieved from the `csrftoken` cookie.

### 1.2. Access Control & Decryption Flow (ABAC + CP-ABE)
Every file resource (Upload) in the system goes through 2 layers of security:
- **Layer 1 - ABAC (Attribute-Based Access Control)**:
  - When a user requests to download/view a file, the PEP (Policy Enforcement Point) sends an access control request to the PDP (Policy Decision Point using PyCasbin).
  - The PDP evaluates the user's attributes (`department`, `role`, `clearance_level`, etc.) against the defined Policies to make an Allow or Deny decision.
- **Layer 2 - CP-ABE (Ciphertext-Policy Attribute-Based Encryption)**:
  - If ABAC allows access, the encrypted file is downloaded to the server. 
  - The system dynamically generates (on-the-fly) a CP-ABE secret key based on the user's current set of attributes. This key is temporarily cached on **Redis** (avoiding persistent storage in the DB).
  - The CP-ABE key is used to decrypt the AES key, which is then used to decrypt the file content and return it to the user. The file content exists only in RAM during request processing.

### 1.3. SQL Encryption & Metadata Security (Field-level Encryption)
In addition to protecting the file contents, the system secures sensitive data within the SQL database:
- **AES-256-GCM Field Encryption**: Sensitive database columns (Original Filename, JSON Metadata, Signed URLs, Physical Paths) are strongly encrypted before insertion.
- **HMAC-SHA3-256 Blind Indexing**: Allows secure searching on encrypted columns without revealing plaintext data.
- **Path Obfuscation**: The physical file names stored in Cloud Storage (Supabase) are randomized UUID strings, bearing no relation to the original filename or business logic.
- **Auto-Extract Metadata**: Upon upload, the system automatically collects IP, User-Agent, uploader identity, file size, and MIME type, encrypting the entire JSON metadata block.

## 2. REST API Specifications

Base URL: `http(s)://<domain>`

### 2.1. Authentication API (Auth API)
Prefix: `/api/auth/`

| Method | Endpoint            | Description                                                                                   | Auth Required |
| ------ | ------------------- | --------------------------------------------------------------------------------------------- | ------------- |
| POST   | `/login/`           | System login. Returns JWT Tokens via HttpOnly Cookies.                                        | No            |
| POST   | `/register/`        | Register a new account (requires Super Admin activation or auto-created depending on config). | No            |
| POST   | `/logout/`          | Removes Access Token and Refresh Token from Cookies.                                          | Yes           |
| POST   | `/token/refresh/`   | Issues a new Access Token based on the Refresh Token.                                         | Yes (Cookie)  |
| GET    | `/profile/`         | Retrieves current user info (personal info, user type).                                       | Yes           |
| GET    | `/permissions/`     | Retrieves system permissions of the current user (is_admin, is_super_admin).                  | Yes           |
| POST   | `/change-password/` | Change password. Requires `old_password` and `new_password`.                                  | Yes           |

### 2.2. System Administration & Authorization API (Admin API)
Prefix: `/api/admin/`

| Method   | Endpoint                            | Description                                                                                        | Auth Required |
| -------- | ----------------------------------- | -------------------------------------------------------------------------------------------------- | ------------- |
| GET/POST | `/user-types/`                      | Manage the list of user types.                                                                     | Admin         |
| GET/POST | `/attributes/`                      | Define attribute schemas (Attribute Definitions). Used for ABAC and CP-ABE.                        | Admin         |
| GET/POST | `/policies/`                        | Manage ABAC Access Policies. Allows defining rules in Casbin format.                               | Admin         |
| POST     | `/policies/parse_ast/`              | Parses a policy string into an Abstract Syntax Tree (AST) structure for UI visualization.          | Admin         |
| POST     | `/policies/test_policy/`            | Tests an ABAC policy string against real user attributes to verify access decisions before saving. | Admin         |
| GET/POST | `/users/`                           | Manage users across the system (create, lock, approve accounts).                                   | Admin         |
| GET      | `/dashboard-stats/`                 | Retrieve overview statistics (Total users, files, policies) for dashboard charts.                  | Admin         |
| GET      | `/users/{id}/attributes/`           | List attributes currently assigned to a specific user.                                             | Admin         |
| POST     | `/users/{id}/attributes/assign/`    | Assign a new attribute to a user. Triggers automatic CP-ABE Redis Cache invalidation for the user. | Admin         |
| DELETE   | `/users/{id}/attributes/{attr_id}/` | Revoke a user's attribute. Automatically Invalidates Redis Cache.                                  | Admin         |

### 2.3. Storage & Data Decryption API (Storage API)
Prefix: `/api/storage/`

| Method   | Endpoint                | Description                                                                                                                                                                                      | Auth Required    |
| -------- | ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------- |
| GET/POST | `/buckets/`             | Manage Storage Buckets (Logical storage to group files).                                                                                                                                         | Yes              |
| GET/POST | `/files/`               | Main API for File Upload. POST data includes `file` and `policy` (Desired CP-ABE policy). The file is encrypted with AES, and the AES key is encrypted with CP-ABE. **Simultaneously**, metadata is extracted, and database fields (filename, path, metadata) are encrypted using AES-256-GCM before SQL insertion. | Yes              |
| GET      | `/files/{id}/`          | Retrieve file metadata.                                                                                                                                                                          | Yes              |
| GET      | `/files/{id}/download/` | Request file download. System performs ABAC check -> generates CP-ABE key (if not cached) -> decrypts -> returns data stream.                                                                    | Yes              |
| DELETE   | `/files/{id}/`          | Move a file to Trash or permanent delete if authorized.                                                                                                                                          | File Owner/Admin |

## 3. Frontend API Usage Guide

When building UI or calling APIs from the Frontend (using Axios or Fetch):

**1. No manual Access Token management needed**
Because the system uses HttpOnly Cookies, you do not need to add the `Authorization: Bearer <token>` Header to requests. The browser automatically handles attaching the Cookie.

**2. CSRF Token Management (Mandatory for POST/PUT/DELETE)**
For security, you must read the value of the `csrftoken` cookie and append it to request headers under the name `X-CSRFToken`.

*Fetch API Example:*
```javascript
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Upload API Call
async function uploadFile(fileInput, policyString) {
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('policy', policyString); // e.g: 'department:it AND role:manager'

    const response = await fetch('/api/storage/files/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken') // Important!
            // Do not set Content-Type, browser will automatically format as multipart/form-data
        },
        body: formData
    });

    return await response.json();
}
```

## 4. Basic Error Handling

- **401 Unauthorized**: User is not logged in or the Token has expired (including the Refresh Token). Frontend should redirect to the `/auth/login/` page.
- **403 Forbidden**: User is authenticated but blocked by the ABAC system from performing the action due to missing attributes (Policy Deny) or insufficient Admin privileges. Or due to an incorrect/missing CSRF Token.
- **404 Not Found**: Resource does not exist.
- **500 Internal Server Error**: Server error (e.g., CP-ABE cannot decrypt due to an incorrect policy, Redis server crash, etc.). All 500 errors are caught and logged carefully on the backend.
