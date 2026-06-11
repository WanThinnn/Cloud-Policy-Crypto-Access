# **SECURE DOCUMENT MANAGEMENT AND ACCESS CONTROL ON CLOUD DATABASE IN ENTERPRISE**

## **1.1. Project Introduction**

In the context of enterprises increasingly shifting to cloud computing infrastructure, storing, sharing, and utilizing internal documents in the cloud has become an inevitable trend. This model brings numerous benefits in terms of scalability, flexibility, and operational cost optimization. However, it also introduces serious challenges related to **information security** and **data access control**, especially for sensitive documents related to corporate governance, finance, HR, or strategic research.

Traditional access control mechanisms based on fixed access control lists (ACL) or roles (RBAC) often reveal many limitations in modern cloud environments where users, resources, and access contexts are constantly changing. Moreover, relying solely on application-layer logic control is insufficient because data stored on cloud infrastructure is often assumed to be **semi-trusted** and vulnerable to unauthorized access in case of a security breach.

Originating from these issues, the project **"Secure Document Management and Access Control on Cloud Database in Enterprise"** is developed to propose and implement a secure document management system that tightly integrates **Attribute-Based Access Control (ABAC)** and **cryptographic access enforcement via CP-ABE combined with AES-GCM**.

The system not only supports basic business functions such as **creating, storing, sharing, and managing document versions**, but also applies a **dual-layer access control** model. In this model, ABAC dictates the access logic based on policies and attributes, while CP-ABE ensures that only users with matching attributes possess the capability to decrypt and access the data content, even if the storage infrastructure is compromised.

The ABAC mechanism in the system is implemented according to standard architecture consisting of three logical components: **Policy Administration Point (PAP)**, **Policy Decision Point (PDP)**, and **Policy Enforcement Point (PEP)**. 

Simultaneously, the system applies a **hybrid encryption** approach to protect data. File contents are encrypted using the **AES-256-GCM** symmetric algorithm to ensure confidentiality and integrity, while the AES key is encrypted using **CP-ABE** according to the attribute policy defined by the Data Owner. This approach allows attaching access policies directly to the data, eliminating reliance on the trustworthiness of the cloud storage infrastructure.

Furthermore, to mitigate the risk of data leaks from the relational database (SQL DB), the system employs **Field-level Encryption** using **AES-256-GCM** combined with **Blind Indexing** via **HMAC-SHA3-256**. Sensitive document details such as the physical file path, original name, shared URLs, and all extracted metadata are heavily encrypted before being saved into the DB. The actual storage path of the file on the Cloud Storage is obfuscated using random UUID strings to prevent directory traversal or structure guessing. Database queries on fields like `file_name` and `file_path` are securely performed using SHA3-256 hashes to preserve absolute privacy.

## **1.2. List of Requirements**

| No. | Requirement Name | Form | Regulation | Note |
| --- | ----------------------------- | -------------- | -------- | ------- |
| 1 | Create user | F1 | R1 | |
| 2 | Upload encrypted file | F2 | R2 | |
| 3 | Manage file list | F3 | | |
| 4 | Manage user attributes | F4 | R4 | |
| 5 | Manage access keys | F5 | R5 | |
| 6 | Manage file versions | F6 | R6 | |
| 7 | Manage access policies | F7 | R7 | |
| 8 | Manage Super Admin | F8 | R8 | |
| 9 | Manage attribute schemas | F9 | R9 | |
| 10 | Generate system reports | F10.1, F10.2 | | |
| 11 | Change system configuration | | R11 | |
| 12 | Manage access logs | F12 | R12 | |
| 13 | Manage key revocation | F13 | R13 | |
| 14 | Manage system configuration | F14 | R14 | |

## **1.3. Key Regulations and Forms**

### **R1: User Types**
User types are defined in the attribute schema and can be expanded according to enterprise needs. Default types include:
- `super_admin`: Highest administrator — Full system access
- `admin`: Department administrator — Manages users within their department
- `data_owner`: Data Owner (DO) — Creates, uploads, encrypts files; defines CP-ABE policies; manages file versions and access rights
- `data_user`: Data User (DU) — Reads/downloads files according to granted ABAC and CP-ABE policies

### **R2: Upload Encrypted File & Metadata Extraction**
Files uploaded to the system are strictly encrypted based on CP-ABE attribute policies. Nobody, except the file owner, can alter its access policy. During upload, the system automatically extracts comprehensive **metadata**: IP, User-Agent, Uploader Identity (Username, Email, Full Name, Role), File Size, and MIME Type. This metadata is strictly encrypted in the database, while the physical object is stored under a randomized UUID name in the cloud storage.

### **R4: User Attributes (Single Source of Truth)**
The `user_attributes` table is the Single Source of Truth for all user ABAC attributes. These attributes are used for:
- **ABAC**: Evaluating access policies at the PDP
- **CP-ABE**: Generating user secret keys and encrypting files

### **R5: Dynamic Key Generation, HashiCorp Vault, and Redis Cache**
**Cryptographic Keys**:
- **HashiCorp Vault Integration**: The CP-ABE Master Key (`cpabe_msk.key`) and Public Key (`cpabe_pk.key`) are strictly secured within **HashiCorp Vault**. During initialization, if keys do not exist, they are automatically generated, injected into Vault's memory, and backed up locally to `./config/keys`.
- The User Private Key is **dynamically generated (on-the-fly) in RAM** based on the user's current attributes when access is requested. It is cached in **Redis** with a short TTL. It is **NEVER** persisted to the DB or static files.
- **TTL**: Keys are cached for 1 hour.
- **Revocation**: Handled by simply invalidating the specific Redis key.

### **R7: ABAC Access Policy**
Each ABAC policy defines access rules based on three types of attributes:
- **Subject Attributes**: User attributes (department, role, clearance_level, etc.)
- **Resource Attributes**: Resource attributes (file type, classification level)
- **Environment Attributes**: Environmental attributes (time, IP, device, geolocation)
The system features an **Abstract Syntax Tree (AST) evaluator**, allowing policies to support complex **nested boolean logic** (e.g., `(department == 'it' and role == 'manager') or clearance_level == 'top_secret'`). This ensures mathematically precise attribute matching for both the Casbin ABAC layer and the CP-ABE cryptographic layer. Default conflict resolution strategy is **Deny-Override**.

## **1.4. Database Tables Summary**

| No. | Table | Description | Form |
| --- | ------------------- | ----------------------- | -------- |
| 1 | users | User information | F1 |
| 2 | shared_files | Encrypted file metadata | F2 |
| 3 | file_versions | File versions | F6 |
| 4 | user_attributes | User attributes | F4 |
| 5 | access_policies | ABAC Policies | F7 |
| 6 | super_admin | Super Admin information | F8 |
| 7 | system_schemas | Attribute schemas | F9 |
| 8 | access_logs | Access logs | F12 |
| 9 | system_config | System configuration | F14 |
| 10 | storage_buckets | Logical file grouping | — |
| 11 | file_access_policies | Per-file/folder access grants | — |
| 12 | key_revocations | Key revocation audit trail | — |
