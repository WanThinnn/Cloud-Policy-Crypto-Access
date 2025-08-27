# Cloud Firestore Crypto Access Backend

A comprehensive backend system implementing Hybrid Ciphertext-Policy Attribute-Based Encryption (CP-ABE) with Cloud Firestore integration, providing secure file storage, user management, and attribute-based access control.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Features](#features)
4. [Requirements](#requirements)
5. [Installation](#installation)
6. [Configuration](#configuration)
7. [Running the Application](#running-the-application)
8. [API Documentation](#api-documentation)
9. [Authentication](#authentication)
10. [User Management](#user-management)
11. [File Operations](#file-operations)
12. [ABE System](#abe-system)
13. [ABAC System](#abac-system)
14. [Testing](#testing)
15. [Docker Deployment](#docker-deployment)
16. [Development](#development)
17. [Troubleshooting](#troubleshooting)

## Overview

This backend system provides a secure, scalable solution for attribute-based file encryption and access control. It combines CP-ABE cryptography with modern cloud infrastructure to enable fine-grained access control based on user attributes.

### Key Components

- **CP-ABE Encryption System**: Implements Ciphertext-Policy Attribute-Based Encryption for secure file storage
- **Super Admin Management**: Centralized user management with administrative controls
- **ABAC System**: Attribute-Based Access Control with dynamic policy management
- **File Versioning**: Complete file version tracking with integrity verification
- **JWT Authentication**: Secure token-based authentication system
- **Cloud Firestore Integration**: Scalable NoSQL database for metadata and user management

## Architecture

### System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Client Apps   │    │   Flask Backend  │    │ Cloud Firestore │
│                 │────│                  │────│                 │
│ - Web Frontend  │    │ - REST API       │    │ - User Data     │
│ - Mobile Apps   │    │ - JWT Auth       │    │ - File Metadata │
│ - CLI Tools     │    │ - CP-ABE System  │    │ - Access Logs   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                       ┌──────────────────┐
                       │   ABE Library    │
                       │                  │
                       │ - Master Keys    │
                       │ - Policy Engine  │
                       │ - Crypto Ops     │
                       └──────────────────┘
```

### Module Structure

- **routes/**: API endpoint handlers organized by functionality
- **module/**: Core business logic modules
- **utils/**: Utility functions and helpers
- **config.py**: Configuration management
- **main.py**: Application entry point

## Features

### Security Features

- **Hybrid CP-ABE Encryption**: Advanced attribute-based encryption for files
- **Password-Protected Private Keys**: User private keys encrypted with user passwords
- **JWT Authentication**: Secure token-based authentication
- **Force Password Change**: Mandatory password change for new users
- **Attribute Validation**: Database-driven validation for user attributes
- **ABAC Policies**: Fine-grained access control with wildcard support

### Management Features

- **Super Admin System**: Centralized user and system management
- **User Attribute Management**: Dynamic attribute assignment and validation
- **File Versioning**: Complete version control with rollback capabilities
- **Integrity Verification**: File integrity checking with cryptographic hashes
- **Audit Logging**: Comprehensive logging for security and compliance

### Advanced Features

- **Schema Management**: Dynamic attribute schema management
- **Corporate Policies**: Pre-defined ABAC policies for enterprise environments
- **Health Monitoring**: System health checks and monitoring endpoints
- **Docker Support**: Containerized deployment with Docker Compose

## Requirements

### Hybrid CP-ABE Library Requirements

**IMPORTANT**: This system requires the Hybrid Ciphertext-Policy Attribute-Based Encryption Library for C/C++ to be installed on your system before running the application.

#### Installation Options

**Option 1: Download Pre-built Library**
- Download the pre-built library from: https://github.com/WanThinnn/Hybrid-CP-ABE-Library/releases/tag/Hybrid-CP-ABE_v.2.2
- Extract the library files to the `lib/` directory:
  - For Linux: Place `libhybrid-cp-abe.so` in `lib/`
  - For Windows: Place `libhybrid-cp-abe.dll` in `lib/`

**Option 2: Build from Source**
- Clone the repository: `git clone https://github.com/WanThinnn/Hybrid-CP-ABE-Library.git`
- Follow the build instructions in the library repository
- Copy the compiled library files to the `lib/` directory

#### Library Verification

After installation, verify the library is properly placed:

```bash
# Check library files exist
ls -la lib/
# Should show: libhybrid-cp-abe.so (Linux) or libhybrid-cp-abe.dll (Windows)
```

### System Requirements

- **Operating System**: Linux (Ubuntu 20.04+), macOS, or Windows
- **Python**: 3.8 or higher
- **Memory**: 2GB RAM minimum, 4GB recommended
- **Storage**: 10GB available space
- **Network**: Internet connection for Firestore access

### Dependencies

- Flask 2.3.3
- Firebase Admin SDK 6.2.0
- PyJWT 2.8.0
- Cryptography libraries (PyCryptodome, bcrypt)
- Additional dependencies listed in `requirements.txt`

## Installation

### Manual Installation

1. **Clone the Repository**
   ```bash
   git clone https://github.com/WanThinnn/Cloud-Firestore-Crypto-Access 
   cd Cloud-Firestore-Crypto-Access/app/backend
   ```

2. **Create Virtual Environment**
   ```bash
   python3 -m venv env
   source env/bin/activate  # On Windows: env\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Setup Directories**
   ```bash
   mkdir -p log tmp uploads abe_keys env
   ```

### Firebase Setup

1. **Create Firebase Project**
   - Go to [Firebase Console](https://console.firebase.google.com/)
   - Create a new project
   - Enable Firestore Database

2. **Generate Service Account Key**
   - Go to Project Settings > Service Accounts
   - Generate new private key
   - Save as `env/cloud-firestore-crypto-access.json`

3. **Configure Firestore Rules**
   ```javascript
   rules_version = '2';
   service cloud.firestore {
     match /databases/{database}/documents {
       match /{document=**} {
         allow read, write: if true;
       }
     }
   }
   ```

## Configuration

### Environment Variables

Create `.env` file in the `env/` directory:

```env
# Flask Configuration
FLASK_ENV=development
HOST=0.0.0.0
PORT=5000
DEBUG=true

# JWT Configuration
JWT_SECRET_KEY=your-super-secret-jwt-key-here

# System Service Token
SYSTEM_SERVICE_TOKEN=your-system-service-token

# Firebase Configuration (automatically detected)
GOOGLE_APPLICATION_CREDENTIALS=./env/cloud-firestore-crypto-access.json

# Logging
LOG_LEVEL=INFO
```

### Application Configuration

Key configuration options in `config.py`:

```python
class Config:
    # Server settings
    HOST = os.environ.get('HOST', '0.0.0.0')
    PORT = int(os.environ.get('PORT', 5000))
    DEBUG = False
    
    # JWT settings
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
    
    # Upload settings
    UPLOAD_FOLDER = 'tmp'
    
    # System service authentication
    SYSTEM_SERVICE_TOKEN = os.getenv('SYSTEM_SERVICE_TOKEN')
```

## Running the Application

### Development Mode

```bash
# Activate virtual environment
source env/bin/activate

# Run the application
python main.py
```

The server will start on `http://localhost:5000` by default.

### Production Mode

```bash
# Using Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 main:app

# Or with specific configuration
gunicorn --config gunicorn.conf.py main:app
```

## API Documentation

### Base URL

All API endpoints are prefixed with the base URL:
```
http://your-domain:5000/api
```

### Response Format

All API responses follow a consistent format:

```json
{
  "success": true|false,
  "message": "Human readable message",
  "data": {},
  "error": "Error message (if success=false)"
}
```

### Health Check

Check system status:

```bash
# Basic health check
GET /health

# Detailed health check
GET /api/health

# Readiness probe
GET /api/health/ready

# Liveness probe  
GET /api/health/live
```

## Authentication

The system uses JWT (JSON Web Token) based authentication with two user types:

### Super Admin Authentication

Super admins have full system access and can manage users.

#### Create Super Admin Account

```bash
curl -X POST "http://localhost:5000/api/super-admin/setup" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "superadmin1", 
    "password": "Admin123!@#",
    "email": "admin@company.com",
    "full_name": "System Administrator"
  }'
```

#### Super Admin Login

```bash
curl -X POST "http://localhost:5000/api/super-admin/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "superadmin1",
    "password": "Admin123!@#"
  }'
```

Response:
```json
{
  "success": true,
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 86400,
  "user_id": "21520001",
  "user_type": "super_admin"
}
```

### Regular User Authentication

Regular users are created by super admins and have limited access.

#### User Login

```bash
curl -X POST "http://localhost:5000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "user123",
    "password": "UserPass123!"
  }'
```

#### Force Password Change

New users must change their password on first login:

```bash
curl -X POST "http://localhost:5000/api/auth/change-password" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "user123",
    "old_password": "TempPass123!",
    "new_password": "NewSecurePass123!"
  }'
```

### Using JWT Tokens

Include the JWT token in the Authorization header:

```bash
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## User Management

### Create User Account

Only super admins can create user accounts:

```bash
curl -X POST "http://localhost:5000/api/super-admin/users" \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "user_data": {
      "username": "itmanager001",
      "email": "manager@company.com",
      "password": "Manager123!",
      "full_name": "John Doe Manager"
    },
    "user_attributes": {
      "role": "manager",
      "department": "it",
      "clearance_level": "confidential",
      "data_access": "admin",
      "employment_status": "active",
      "location": "hq_hcm"
    }
  }'
```

### List Users

```bash
curl -X GET "http://localhost:5000/api/super-admin/users" \
  -H "Authorization: Bearer <admin-token>"
```

### Get User Details

```bash
curl -X GET "http://localhost:5000/api/super-admin/users/{user_id}" \
  -H "Authorization: Bearer <admin-token>"
```

### Update User Attributes

```bash
curl -X PUT "http://localhost:5000/api/super-admin/users/{user_id}/attributes" \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "role": "senior_manager",
    "department": "it",
    "clearance_level": "top_secret"
  }'
```

### Deactivate/Activate User

```bash
# Deactivate user
curl -X POST "http://localhost:5000/api/super-admin/users/{user_id}/deactivate" \
  -H "Authorization: Bearer <admin-token>"

# Activate user
curl -X POST "http://localhost:5000/api/super-admin/users/{user_id}/activate" \
  -H "Authorization: Bearer <admin-token>"
```

## File Operations

### Upload File

Upload and encrypt a file with access policy:

```bash
curl -X POST "http://localhost:5000/api/files/upload" \
  -H "Authorization: Bearer <user-token>" \
  -F "file=@test_file.txt" \
  -F "access_policy=role:manager AND department:it" \
  -F "metadata={\"description\": \"Confidential report\"}"
```

### List Files

```bash
curl -X GET "http://localhost:5000/api/files/" \
  -H "Authorization: Bearer <user-token>"
```

### Get File Information

```bash
curl -X GET "http://localhost:5000/api/files/{file_id}" \
  -H "Authorization: Bearer <user-token>"
```

### Download File

```bash
curl -X GET "http://localhost:5000/api/files/{file_id}/download" \
  -H "Authorization: Bearer <user-token>"
```

### Delete File

```bash
curl -X DELETE "http://localhost:5000/api/files/{file_id}" \
  -H "Authorization: Bearer <user-token>"
```

### Update File Access Policy

```bash
curl -X PUT "http://localhost:5000/api/files/{file_id}/policy" \
  -H "Authorization: Bearer <user-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "access_policy": "role:manager OR department:hr"
  }'
```

## ABE System

### Setup ABE System

Initialize the ABE system (creates master and public keys):

```bash
curl -X POST "http://localhost:5000/api/ca/setup" \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json"
```

### Get Public Key

```bash
curl -X GET "http://localhost:5000/api/ca/public-key" \
  -H "Authorization: Bearer <admin-token>"
```

### Check CA Status

```bash
curl -X GET "http://localhost:5000/api/ca/status" \
  -H "Authorization: Bearer <admin-token>"
```

### Generate User Private Key

```bash
curl -X POST "http://localhost:5000/api/ca/users/{user_id}/private-key" \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json"
```

### Check User Private Key Status

```bash
curl -X GET "http://localhost:5000/api/ca/user/private-key/check" \
  -H "Authorization: Bearer <user-token>"
```

### Generate Private Key (User)

```bash
curl -X POST "http://localhost:5000/api/ca/user/private-key/generate" \
  -H "Authorization: Bearer <user-token>"
```

### ABE Encrypt Data

```bash
curl -X POST "http://localhost:5000/api/abe/encrypt" \
  -H "Content-Type: application/json" \
  -d '{
    "data": "sensitive data to encrypt",
    "policy": "role:manager AND department:it"
  }'
```

### ABE Decrypt Data

```bash
curl -X POST "http://localhost:5000/api/abe/decrypt" \
  -H "Authorization: Bearer <user-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "encrypted_data": "<base64-encrypted-data>",
    "password": "user-password"
  }'
```

## ABAC System

### Create Access Policy

```bash
curl -X POST "http://localhost:5000/api/abac/policies" \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "IT Management Access",
    "resource_type": "file",
    "conditions": {
      "role": ["manager", "senior_manager"],
      "department": ["it"],
      "clearance_level": ["confidential", "top_secret"]
    },
    "actions": ["read", "write", "delete"],
    "effect": "allow"
  }'
```

### List Policies

```bash
curl -X GET "http://localhost:5000/api/abac/policies" \
  -H "Authorization: Bearer <admin-token>"
```

### Delete Policy

```bash
curl -X DELETE "http://localhost:5000/api/abac/policies/{policy_id}" \
  -H "Authorization: Bearer <admin-token>"
```

### Setup Corporate Policies

```bash
curl -X POST "http://localhost:5000/api/abac/setup-corporate-policies" \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json"
```

### Check Access

```bash
curl -X POST "http://localhost:5000/api/abac/check-corporate-access" \
  -H "Authorization: Bearer <user-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "resource_type": "file",
    "resource_id": "test_resource",
    "action": "read",
    "context": {
      "time": "business_hours",
      "location": "office"
    }
  }'
```

## Testing

### Comprehensive Test Suite

The system includes a comprehensive test script that validates all functionality:

```bash
# Run full backend test
chmod +x test/full-test-backend.bash
./test/full-test-backend.bash
```

### Manual Testing

#### 1. System Setup

```bash
# Health check
curl -X GET "http://localhost:5000/api/health" | jq

# Setup ABE system
curl -X POST "http://localhost:5000/api/ca/setup" \
  -H "Authorization: Bearer <admin-token>"
```

#### 2. User Management Test

```bash
# Create super admin
curl -X POST "http://localhost:5000/api/super-admin/setup" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "Admin123!",
    "email": "admin@test.com",
    "full_name": "Test Admin"
  }'

# Login as super admin  
curl -X POST "http://localhost:5000/api/super-admin/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "Admin123!"}'
```

#### 3. File Operations Test

```bash
# Create a test file
echo "This is a test file for ABE encryption" > test_upload.txt

# Upload test file
curl -X POST "http://localhost:5000/api/files/upload" \
  -H "Authorization: Bearer <user-token>" \
  -F "file=@test_upload.txt" \
  -F "access_policy=department:it OR department:hr"

# List user files
curl -X GET "http://localhost:5000/api/files/" \
  -H "Authorization: Bearer <user-token>"
```

### Performance Testing

Monitor system performance using built-in health endpoints:

```bash
# Performance metrics
curl -X GET "http://localhost:5000/api/health" | jq '.performance'

# System statistics
curl -X GET "http://localhost:5000/api/super-admin/stats" \
  -H "Authorization: Bearer <admin-token>"
```

## Docker Deployment

### Docker Compose Deployment

1. **Prepare Environment**
   ```bash
   # Create environment file
   cp env/.env.example env/.env
   # Edit env/.env with your configuration
   ```

2. **Build and Run**
   ```bash
   # Build and start services
   docker-compose up -d

   # View logs
   docker-compose logs -f

   # Stop services
   docker-compose down
   ```

3. **Health Check**
   ```bash
   # Check container health
   docker-compose ps

   # Test API
   curl -X GET "http://localhost:5000/api/health"
   ```

### Docker Configuration

The `docker-compose.yml` includes:

- **Persistent Storage**: Logs, uploads, and temporary files
- **Environment Variables**: Flexible configuration
- **Health Checks**: Automatic health monitoring
- **Network Isolation**: Secure networking setup

### Production Deployment

For production deployment:

1. **Update Environment**
   ```bash
   # Set production values in env/.env
   FLASK_ENV=production
   LOG_LEVEL=INFO
   DEBUG=false
   ```

2. **Security Configuration**
   ```bash
   # Generate secure keys
   openssl rand -hex 32  # For JWT_SECRET_KEY
   openssl rand -hex 32  # For SYSTEM_SERVICE_TOKEN
   ```

3. **SSL/TLS Setup**
   - Configure reverse proxy (nginx/Apache)
   - Use SSL certificates
   - Enable HTTPS redirects

## Development

### Project Structure

```
backend/
├── main.py                 # Application entry point
├── config.py              # Configuration management
├── requirements.txt       # Python dependencies
├── Dockerfile             # Docker configuration
├── docker-compose.yml     # Docker Compose setup
├── routes/                # API route handlers
│   ├── __init__.py
│   ├── auth_routes.py     # Authentication endpoints
│   ├── super_admin_routes.py  # Super admin management
│   ├── ca_routes.py       # Certificate Authority
│   ├── files_routes.py    # File operations
│   ├── abac_routes.py     # ABAC system
│   └── abe_routes.py      # ABE operations
├── module/                # Core business logic
│   ├── __init__.py
│   ├── super_admin.py     # Super admin management
│   ├── central_authority.py  # ABE key management
│   ├── user_management.py # User operations
│   ├── file_manager.py    # File operations
│   ├── abac.py           # Access control
│   ├── jwt_auth.py       # JWT authentication
│   └── database.py       # Database connections
├── utils/                 # Utility functions
│   ├── __init__.py
│   └── logger.py         # Logging utilities
├── test/                  # Test scripts
│   └── full-test-backend.bash
└── env/                   # Environment files
    └── firebase-key.json
```

### Adding New Features

1. **Create Route Module**
   ```python
   # routes/new_feature_routes.py
   from flask import Blueprint
   
   new_feature_api = Blueprint('new_feature', __name__)
   
   @new_feature_api.route('/endpoint', methods=['GET'])
   def new_endpoint():
       return jsonify({'message': 'New feature'})
   ```

2. **Register Blueprint**
   ```python
   # routes/__init__.py
   from .new_feature_routes import new_feature_api
   
   all_blueprints = [..., new_feature_api]
   ```

3. **Add Business Logic**
   ```python
   # module/new_feature.py
   class NewFeatureManager:
       def process_data(self):
           # Implementation
           pass
   ```

### Code Standards

- **PEP 8 Compliance**: Follow Python style guidelines
- **Type Hints**: Use type annotations where possible
- **Documentation**: Document all functions and classes
- **Error Handling**: Implement comprehensive error handling
- **Logging**: Use structured logging throughout

### Database Schema

The system uses the following Firestore collections:

#### Users Collection
```javascript
users/{user_id} {
  email: string,
  full_name: string,
  user_type: "super_admin" | "regular",
  is_active: boolean,
  created_at: timestamp,
  must_change_password: boolean,
  password_changed_at: timestamp
}
```

#### User Attributes Collection
```javascript
user_attributes/UA{user_id} {
  role: string,
  department: string,
  clearance_level: string,
  data_access: string,
  employment_status: string,
  location: string
}
```

#### ABE Keys Collection
```javascript
abe_keys/privkey_{user_id}_{timestamp} {
  user_id: string,
  encrypted_key: bytes,
  attributes: array,
  is_active: boolean,
  created_at: timestamp,
  algorithm: string
}
```

#### Shared Files Collection
```javascript
shared_files/{file_id} {
  filename: string,
  file_size: number,
  content_type: string,
  access_policy: string,
  uploaded_by: string,
  created_at: timestamp,
  encrypted_data: bytes
}
```

## Troubleshooting

### Common Issues

#### 1. Firebase Connection Issues

**Problem**: `firebase_admin.exceptions.InvalidArgumentError`

**Solution**:
```bash
# Check Firebase credentials
ls -la env/cloud-crypto-access-firebase-adminsdk-*.json

# Verify environment variable
echo $GOOGLE_APPLICATION_CREDENTIALS

# Test Firebase connection
python -c "import firebase_admin; print('Firebase OK')"
```

#### 2. ABE Library Loading Issues

**Problem**: `Library not loaded` error

**Solution**:
```bash
# Check library files
ls -la lib/

# Install build dependencies
sudo apt-get install build-essential libgmp-dev libssl-dev

# Rebuild library if needed
make clean && make
```

#### 3. JWT Token Issues

**Problem**: `Invalid or expired token`

**Solution**:
```bash
# Check JWT secret configuration
echo $JWT_SECRET_KEY

# Verify token format
python -c "import jwt; print(jwt.decode('token', verify=False))"

# Generate new secret
openssl rand -hex 32
```

#### 4. Permission Issues

**Problem**: `Permission denied` on file operations

**Solution**:
```bash
# Fix directory permissions
chmod 755 log/ tmp/ uploads/ abe_keys/

# Check file ownership
ls -la log/ tmp/ uploads/

# Set correct ownership
chown -R app:app log/ tmp/ uploads/
```

### Debug Mode

Enable debug mode for development:

```bash
# Set environment variables
export FLASK_ENV=development
export DEBUG=true
export LOG_LEVEL=DEBUG

# Run with debug logging
python main.py
```

### Logging

The system provides comprehensive logging:

- **Application Logs**: `log/app.log`
- **API Logs**: `log/api.log`  
- **Authentication Logs**: `log/auth.log`
- **Database Logs**: `log/database.log`
- **Security Logs**: `log/security.log`

View logs in real-time:
```bash
# Application logs
tail -f log/app.log

# API request logs
tail -f log/api.log

# All logs
tail -f log/*.log
```

### Performance Monitoring

Monitor system performance:

```bash
# Check system health
curl -X GET "http://localhost:5000/api/health" | jq

# View system statistics
curl -X GET "http://localhost:5000/api/super-admin/stats" \
  -H "Authorization: Bearer <admin-token>" | jq

# Monitor resource usage
docker stats cloud-firestore-crypto-access-backend
```

### Support

For additional support:

1. **Check Logs**: Review application logs for detailed error information
2. **Test Endpoints**: Use the comprehensive test script to validate functionality
3. **Health Checks**: Monitor system health using built-in endpoints
4. **Documentation**: Refer to API documentation for correct usage patterns

The system is designed to be robust and self-monitoring, with comprehensive error handling and logging throughout all components.
