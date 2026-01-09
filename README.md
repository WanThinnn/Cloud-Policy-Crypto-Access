# Cloud Policy Crypto Access

A comprehensive system implementing Hybrid Ciphertext-Policy Attribute-Based Encryption (CP-ABE) with Cloud Firestore integration, providing secure file storage, user management, and attribute-based access control.

## Project Overview

This repository contains a full-stack implementation of a secure file sharing system using advanced cryptographic techniques. The system enables fine-grained access control based on user attributes and provides enterprise-level security for sensitive data.

### Key Features

- **Hybrid CP-ABE Encryption**: Advanced attribute-based encryption for secure file storage
- **Cloud Firestore Integration**: Scalable NoSQL database for metadata and user management
- **Attribute-Based Access Control (ABAC)**: Fine-grained permission system
- **JWT Authentication**: Secure token-based authentication
- **File Versioning**: Complete version control with integrity verification
- **Super Admin Management**: Centralized user and system administration
- **Docker Support**: Containerized deployment with Docker Compose

## Project Structure

```
Cloud-Firestore-Crypto-Access/
├── README.md                 # This file - Project overview
├── LICENSE                   # Project license
├── .gitignore               # Git ignore rules
└── app/
    └── backend/             # Backend API server
        ├── README.md        # Detailed backend documentation
        ├── main.py         # Flask application entry point
        ├── requirements.txt # Python dependencies
        ├── Dockerfile      # Docker configuration
        ├── docker-compose.yml # Docker Compose setup
        ├── routes/         # API route handlers
        ├── module/         # Core business logic
        ├── utils/          # Utility functions
        ├── test/           # Test scripts and files
        └── ...             # Other backend files
```

## Quick Start

### Prerequisites

1. **Hybrid CP-ABE Library**: Required for encryption operations
   - Download from: [Hybrid-CP-ABE-Library v.2.2](https://github.com/WanThinnn/Hybrid-CP-ABE-Library/releases/tag/Hybrid-CP-ABE_v.2.2)
   - Or build from source: [Hybrid-CP-ABE-Library](https://github.com/WanThinnn/Hybrid-CP-ABE-Library.git)

2. **System Requirements**:
   - Python 3.8+
   - Firebase account with Firestore enabled
   - Docker (optional, for containerized deployment)

### Getting Started

1. **Clone the Repository**
   ```bash
   git clone https://github.com/WanThinnn/Cloud-Firestore-Crypto-Access.git
   cd Cloud-Firestore-Crypto-Access
   ```

2. **Setup Backend**
   ```bash
   cd app/backend
   # Follow the detailed setup instructions in app/backend/README.md
   ```

3. **Run the System**
   ```bash
   # Option 1: Direct Python execution
   cd app/backend
   python main.py
   
   # Option 2: Docker Compose
   cd app/backend
   docker-compose up -d
   ```

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────┐
│                    Client Applications                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│  │ Web Frontend│  │ Mobile Apps │  │   CLI Tools │      │
│  └─────────────┘  └─────────────┘  └─────────────┘      │
└─────────────────────┬───────────────────────────────────┘
                      │ HTTPS/REST API
┌─────────────────────▼───────────────────────────────────┐
│                  Backend API Server                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│  │ Flask API   │  │JWT Auth     │  │ File Manager│      │
│  │ Routes      │  │ System      │  │ & Versioning│      │
│  └─────────────┘  └─────────────┘  └─────────────┘      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│  │   CP-ABE    │  │    ABAC     │  │  Super Admin│      │
│  │   System    │  │   Policies  │  │ Management  │      │
│  └─────────────┘  └─────────────┘  └─────────────┘      │
└─────────────────────┬───────────────────────────────────┘
                      │ Firebase Admin SDK
┌─────────────────────▼───────────────────────────────────┐
│                 Cloud Firestore                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│  │   Users     │  │ File Meta-  │  │ Access Logs │      │
│  │ Collection  │  │ data Coll.  │  │ Collection  │      │
│  └─────────────┘  └─────────────┘  └─────────────┘      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│  │ ABE Keys    │  │ABAC Policies│  │   Schemas   │      │
│  │ Collection  │  │ Collection  │  │ Collection  │      │
│  └─────────────┘  └─────────────┘  └─────────────┘      │
└─────────────────────────────────────────────────────────┘
```

### Security Features

- **End-to-End Encryption**: Files encrypted with CP-ABE before storage
- **Attribute-Based Access**: Fine-grained access control based on user attributes
- **Password-Protected Keys**: User private keys encrypted with user passwords
- **JWT Authentication**: Secure stateless authentication system
- **Audit Logging**: Comprehensive activity logging for compliance
- **Data Integrity**: Cryptographic verification of file integrity

## Technology Stack

### Backend
- **Framework**: Flask 2.3.3
- **Database**: Google Cloud Firestore
- **Authentication**: JWT (PyJWT 2.8.0)
- **Encryption**: Custom Hybrid CP-ABE Library
- **Deployment**: Docker & Docker Compose
- **Languages**: Python 3.8+

### Security
- **CP-ABE**: Ciphertext-Policy Attribute-Based Encryption
- **ABAC**: Attribute-Based Access Control
- **Cryptography**: PyCryptodome, bcrypt
- **TLS/SSL**: HTTPS communication

## Documentation

- **[Backend API Documentation](app/backend/README.md)**: Comprehensive backend setup and API documentation
- **[API Reference](app/backend/README.md#api-documentation)**: Detailed API endpoint documentation
- **[Deployment Guide](app/backend/README.md#docker-deployment)**: Docker and production deployment instructions
- **[Testing Guide](app/backend/README.md#testing)**: Testing procedures and examples

## Development

### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup

For detailed development setup instructions, see [Backend Documentation](app/backend/README.md#development).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact

- **Repository**: [Cloud-Firestore-Crypto-Access](https://github.com/WanThinnn/Cloud-Firestore-Crypto-Access)
- **Related**: [Hybrid-CP-ABE-Library](https://github.com/WanThinnn/Hybrid-CP-ABE-Library)

## Acknowledgments

- CP-ABE implementation based on hybrid cryptography techniques
- Firebase team for Cloud Firestore integration
- Flask community for the excellent web framework
