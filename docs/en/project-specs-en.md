# **SECURE DOCUMENT MANAGEMENT AND ACCESS CONTROL ON CLOUD DATABASE IN ENTERPRISE**

## **1.1. Project Introduction**

In the context of enterprises increasingly shifting to cloud computing infrastructure, storing, sharing, and utilizing internal documents in the cloud has become an inevitable trend. This model brings numerous benefits in terms of scalability, flexibility, and operational cost optimization. However, it also introduces serious challenges related to **information security** and **data access control**, especially for sensitive documents related to corporate governance, finance, HR, or strategic research.

Traditional access control mechanisms based on fixed access control lists (ACL) or roles (RBAC) often reveal many limitations in modern cloud environments where users, resources, and access contexts are constantly changing. Moreover, relying solely on application-layer logic control is insufficient because data stored on cloud infrastructure is often assumed to be **semi-trusted** and vulnerable to unauthorized access in case of a security breach.

Originating from these issues, the project **"Secure Document Management and Access Control on Cloud Database in Enterprise"** is developed to propose and implement a secure document management system that tightly integrates **Attribute-Based Access Control (ABAC)** and **cryptographic access enforcement via CP-ABE combined with AES-GCM**.

The system not only supports basic business functions such as **creating, storing, sharing, and managing document versions**, but also applies a **dual-layer access control** model. In this model, ABAC dictates the access logic based on policies and attributes, while CP-ABE ensures that only users with matching attributes possess the capability to decrypt and access the data content, even if the storage infrastructure is compromised.

The ABAC mechanism in the system is implemented according to standard architecture consisting of three logical components: **Policy Administration Point (PAP)**, **Policy Decision Point (PDP)**, and **Policy Enforcement Point (PEP)**. 

Simultaneously, the system applies a **hybrid encryption** approach to protect data. File contents are encrypted using the **AES-256-GCM** symmetric algorithm to ensure confidentiality and integrity, while the AES key is encrypted using **CP-ABE** according to the attribute policy defined by the Data Owner. This approach allows attaching access policies directly to the data, eliminating reliance on the trustworthiness of the cloud storage infrastructure.

Furthermore, to mitigate the risk of data leaks from the relational database (SQL DB), the system employs **Field-level Encryption** using **AES-256-GCM** combined with **Blind Indexing** via **HMAC-SHA3-256**. Sensitive document details such as the physical file path, original name, shared URLs, and all extracted metadata are heavily encrypted before being saved into the DB. The actual storage path of the file on the Cloud Storage is obfuscated using random UUID strings to prevent directory traversal or structure guessing. Database queries on fields like `file_name` and `file_path` are securely performed using SHA3-256 hashes to preserve absolute privacy.

Additionally, to future-proof the system against quantum computing threats (Harvest Now, Decrypt Later), the system's transport layer is secured using **Post-Quantum Cryptography (PQC)**. The reverse proxy (Nginx) is built upon the OpenQuantumSafe (OQS) fork, establishing HTTPS connections exclusively via **TLS 1.3** and utilizing the **Hybrid ML-KEM (Kyber) Key Exchange** mechanism (`X25519MLKEM768`). This ensures quantum-resistant data transmission while maintaining backward compatibility with standard browsers.

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

### **1.3.1. Form 1 and Regulation 1**

**F1: User Identity Information**  
User ID: _______  
Full Name: _______  
Email: _______  
Username: _______  
Password (hash): _______  
User Type: _______  
Account Creation Date: _______  
Account Expiry Date: _______  
Account Status: _______  
Attribute Reference: → F4 (user_attributes)  

> **Note:** ABAC attributes (department, role, clearance_level, etc.) are stored separately in the `user_attributes` collection (F4) to ensure consistency and serve as the single source of truth for both CP-ABE and ABAC systems.

**R1:** User types (`user_type`) are defined in the attribute schema (F9) and can be expanded according to enterprise needs. Default types include:

| User Type | Description | Special Permissions |
| --------- | ----------- | ------------------- |
| `super_admin` | Highest administrator | Full system access |
| `admin` | Department administrator | Manages users within their department |
| `data_owner` | Data Owner (DO) | Creates, uploads, encrypts files; defines CP-ABE policies; manages file versions and access rights |
| `data_user` | Data User (DU) | Reads/downloads files according to granted ABAC and CP-ABE policies |

Each type inherits a basic set of permissions, but access to specific resources is still controlled by ABAC policies based on attributes (F4). Only Super Admins can create users and assign types. Users cannot register accounts themselves. Every user must have all required attributes according to the attribute schema (F9), stored in F4 to facilitate ABAC and CP-ABE access control.

**Example: User Identity Information**  
F1: User Identity Information  
User ID: 22520001  
Full Name: Nguyen Van A  
Email: itmanager001@company.com  
Username: nva_it  
Password (hash): $argon2id$v=19$m=65536...  
User Type: data_owner  
Account Creation Date: 08/09/2025  
Account Expiry Date: 08/09/2026  
Account Status: active  
Attribute Reference: → UA22520001 (user_attributes)  

### **1.3.2 Form 2 and Regulation 2**

**F2: Uploaded File Information**  
File Name: _______  
File Type: _______  
Size: _______  
Access Policy: _______  
Description: _______  
Tags: _______  
Upload Date: _______  
Uploader: _______  

**R2:** There are 5 main file types supported (text/plain, document, image, video, audio). Maximum file size is 100MB. The system only accepts virus-free files that are encrypted based on Ciphertext-Policy Attribute-Based Encryption (CP-ABE). The attribute policy is defined by the file's owner (Data Owner). Data Users with attributes satisfying this policy can access the file. No one can change the file's Access Policy except its owner.

Additionally, the system automatically extracts **metadata** such as: IP, User-Agent, Uploader Identity (Name, Email, Role), file size, and MIME Type. All metadata, along with sensitive fields (Original File Name, Path, Signed URL), is **completely encrypted** using AES-256-GCM in the SQL database. The physical storage path on Cloud Storage is assigned a random UUID string to prevent directory structure inference.

**Example: Uploaded File Information**  
F2: Uploaded File Information  
File Name: q1-report.pdf  
File Type: document
Size: 39 bytes  
Access Policy: "department:it" OR "department:hr"  
Description: Enterprise Q1 report file.  
Tags: report, upload  
Upload Date: 08/09/2025  
Uploader: 22520001  

### **1.3.3 Form 3**

**F3: File List**

| No. | File ID | File Name | File Type | Owner | Status |
| --- | ------- | --------- | --------- | ----- | ------ |
| 1 | 0ae91604-eff2-46cd-81f0-e714b5936ea3 | q1-report.pdf | document | 22520001 | ACTIVE |
| 2 | 1f2cb81c-5a08-459a-9bac-2122896a8aaa | version.txt | text/plain | 22520001 | HISTORICAL |

### **1.3.4 Form 4 and Regulation 4**

**F4: User ABAC Attributes (Source of Truth for CP-ABE)**  
Attribute Doc ID: _______  
User ID (reference from F1): _______  
Updated By: _______  
Updated Date: _______  
Attribute Version: _______  

| No. | Attribute | Type | Value | Status | Effective Date |
| --- | --------- | ---- | ----- | ------ | -------------- |
| 1 | department | enum | | active | |
| 2 | role | enum | | active | |
| 3 | clearance_level | enum | | active | |
| 4 | location | string | | active | |
| 5 | data_access | enum | | active | |
| 6 | employment_status | enum | | active | |

**R4:** The `user_attributes` collection serves as the **Single Source of Truth** for all ABAC attributes of users. These attributes are used to:
- **ABAC**: Evaluate access policies at the PDP
- **CP-ABE**: Generate user secret keys and encrypt files

Only Super Admins or Admins (within their department scope) have the right to modify attributes. Every attribute change will:
1. Increment the attribute version
2. Be recorded in the audit log (F12)
3. Trigger the CP-ABE key revocation and re-issuance process (F13)

**List of mandatory attributes** (according to schema F9):

| Attribute | Description | Allowed Values |
| --------- | ----------- | -------------- |
| `department` | Department | hr, finance, it, operations, executive, security |
| `role` | Job Role | intern, employee, manager, director, ceo |
| `clearance_level` | Security Clearance | public, confidential, secret, top_secret |
| `location` | Work Location | Free string (e.g., hcm_office, hanoi_office) |
| `data_access` | Data Access Level | basic, advanced, full |
| `employment_status` | Employment Status | active, inactive, terminated, on_leave |

**Example:**  
F4: User ABAC Attributes  
Attribute Doc ID: UA22520001  
User ID: 22520001  
Updated By: 21520001 (Super Admin)  
Updated Date: 08/09/2025  
Attribute Version: 3  

| No. | Attribute | Type | Value | Status | Effective Date |
| --- | --------- | ---- | ----- | ------ | -------------- |
| 1 | department | enum | it | active | 08/09/2025 |
| 2 | role | enum | manager | active | 08/09/2025 |
| 3 | clearance_level | enum | secret | active | 08/09/2025 |
| 4 | location | string | hcm_office | active | 08/09/2025 |
| 5 | data_access | enum | advanced | active | 08/09/2025 |
| 6 | employment_status | enum | active | active | 01/01/2025 |

### **1.3.5 Regulation 5 (Dynamic Key Generation, Redis Cache, and Disaster Recovery)**

**R5:** 
- **Encryption Keys**:
    - **HashiCorp Vault Integration**: The Master Key (`cpabe_msk.key`) and Public Key (`cpabe_pk.key`) are strictly secured within **HashiCorp Vault**. Upon initialization, if they do not exist, the system automatically generates keys, injects them into Vault's memory, and backs up a copy locally at `./config/keys`.
    - Personal Secret Keys (Private Keys) are **dynamically generated (on-the-fly) in RAM** based on current user attributes upon request and temporarily cached in **Redis**. They are **NEVER** persisted to the DB or static files.
- **Time-To-Live (TTL)**: Keys are cached for a short duration (default 1 hour).
- **Key Revocation**: When user attributes change or the account is deactivated, the system simply deletes (invalidates) the corresponding key from the Redis cache. Subsequent requests will be denied or require key regeneration based on the newly updated attributes.

*(Note: Traditional Key Management Form - F5 - has been omitted since the system no longer manages fixed key repositories in the DB).*

### **1.3.6 Form 6 and Regulation 6**

**F6: File Version Record**  
File ID: _______  
Version: _______  
Size: _______  
Creator: _______  
Creation Date: _______  
Change Description: _______  

**R6:** Each file can have multiple versions. Only the ACTIVE version can be downloaded. HISTORICAL versions are retained for auditing purposes.

**Example:**  
F6: File Version Record  
File ID: 0ae91604-eff2-46cd-81f0-e714b5936ea3  
Version: 1.0.0  
Size: 39 bytes  
Creator: 22520001  
Creation Date: 08/09/2025  
Change Description: Initial version  

### **1.3.7 Form 7 and Regulation 7**

**F7: ABAC Access Policy Record**  
Policy ID: _______  
Policy Name: _______  
Description: _______  
Resource: _______  
Action: _______  

**User Attributes (Subject Conditions):**  
- department: _______  
- role: _______  
- clearance_level: _______  
- employment_status: _______  

**Resource Attributes (Resource Conditions):**  
- resource_type: _______  
- classification: _______  
- owner_department: _______  

**Environment Attributes (Environment Conditions):**  
- time_range: _______  
- ip_whitelist: _______  
- device_type: _______  
- location: _______  

Effect: _______  
Priority: _______  
Conflict Resolution Strategy: _______  
Status: _______  
Creation Date: _______  

**R7:** Each ABAC policy defines access rules based on three attribute categories:
- **Subject Attributes**: User attributes (department, role, clearance_level, etc.)
- **Resource Attributes**: Resource attributes (file type, classification level)
- **Environment Attributes**: Environmental constraints (time, IP, device, geographic location)

The system integrates an **Abstract Syntax Tree (AST)** parser, enabling policies to support **complex nested boolean logic** using parentheses (e.g., `(department == 'it' and role == 'manager') or clearance_level == 'top_secret'`). This guarantees precise attribute matching for both the ABAC tier (Casbin) and the cryptographic tier (CP-ABE).

Only Super Admins can create/edit policies via a Visual UI Builder or by writing direct code. There are 2 effects: ALLOW and DENY. Higher priority overrides lower priority. The default conflict resolution strategy is **Deny-Override**.

**Example 1: Subject attribute-based policy (with nested logic)**  
F7: ABAC Access Policy Record  
Policy ID: executives_all_access  
Policy Name: Executive All Access  
Description: Executive level access to all resources  
Resource: shared_files  
Action: read, write, delete  
Subject Attributes: `(role == "executive" OR role == "ceo") AND department == "board"`  
Resource Attributes: *  
Environment Attributes: *  
Effect: ALLOW  
Priority: 100  
Conflict Resolution Strategy: deny-override  
Status: active  
Creation Date: 08/09/2025  

**Example 2: Policy with environmental conditions**  
F7: ABAC Access Policy Record  
Policy ID: finance_office_hours_only  
Policy Name: Finance Department Office Hours Access  
Description: Finance staff can only access sensitive files during office hours from the office network  
Resource: shared_files  
Action: read, download  
Subject Attributes: department == "finance" AND clearance_level >= "confidential"  
Resource Attributes: classification == "financial_report"  
Environment Attributes: time_range == "08:00-18:00" AND ip_whitelist CONTAINS request.ip AND device_type IN ["company_laptop", "company_desktop"]  
Effect: ALLOW  
Priority: 80  
Conflict Resolution Strategy: deny-override  
Status: active  
Creation Date: 08/09/2025  

### **1.3.8 Form 8 and Regulation 8**

**F8: Super Admin Information**  
ID: _______  
Username: _______  
Email: _______  
Permissions: _______  
Role: _______  
Status: _______  
Last Login: _______  
Creation Date: _______  

**R8:** Super Admins hold the highest privilege within the system. They can manage all users, files, policies, and system configurations.

**Example:**  
F8: Super Admin Information  
ID: 21520001  
Username: SuperAdmin  
Email: admin@company.com  
Permissions: ['user_management', 'file_management', 'system_config', 'policy_management']  
Role: super_admin  
Status: active  
Last Login: 08/09/2025  
Creation Date: 08/09/2025  

### **1.3.9 Form 9 and Regulation 9**

**F9: Available Attribute Schema**  
Schema ID: _______  
Version: _______  
Updated Date: _______  
Updated By: _______  

| No. | Attribute Name | Type | Allowed Values | Required |
| --- | -------------- | ---- | -------------- | -------- |
| 1 | | | | |
| 2 | | | | |

**R9:** The attribute schema defines the valid attributes for users in the system. Only Super Admins can alter the schema. Every modification is version-controlled.

**Example:**  
F9: System Attribute Schema  
Schema ID: user_attribute_schemas  
Version: 1.0  
Updated Date: 08/09/2025  
Updated By: 21520001  

| No. | Attribute Name | Type | Allowed Values | Required |
| --- | -------------- | ---- | -------------- | -------- |
| 1 | clearance_level | enum | [public, confidential, secret, top_secret] | Yes |
| 2 | department | enum | [hr, finance, it, operations, executive, security] | Yes |
| 3 | role | enum | [intern, employee, manager, director, ceo] | Yes |
| 4 | location | string | Any valid location | No |
| 5 | data_access | enum | [basic, advanced, full] | Yes |
| 6 | employment_status | enum | [active, inactive, terminated, on_leave] | Yes |

### **1.3.10 Form 10**

#### Form 10.1

**F10.1: Database Collections Statistics Report**  
Date: _______  

| No. | Collection Name | Document Count | Example Document ID |
| --- | --------------- | -------------- | ------------------- |
| 1 | users | 2 | 21520001, 22520001 |
| 2 | shared_files | 2 | 0ae91604-eff2-46cd-81f0-e714b5936ea3 |
| 3 | file_versions | 3 | 26173b83-09b7-4914-bc04-9e70376298ce |
| 4 | user_attributes | 2 | UA22520001, UA21520001 |
| 5 | access_policies | 30 | SuperAdmin_Full_Access |
| 6 | super_admin | 1 | 21520001 |
| 7 | system_schemas | 1 | user_attribute_schemas |
| 8 | access_logs | 156 | log_20250908_143052_001 |
| 9 | system_config | 1 | system_config_main |

Total collections: 9  
Total documents: 198  

#### Form 10.2

**F10.2: User Type Statistics Report**  
Date: _______  

| No. | User Type | Quantity | Ratio |
| --- | --------- | -------- | ----- |
| 1 | super_admin | 1 | 25% |
| 2 | admin | 0 | 0% |
| 3 | data_owner | 2 | 50% |
| 4 | data_user | 1 | 25% |

Total users: 4  

### **1.3.11 Regulation 11**

**R11:** Super Admins can alter regulations as follows:  
- **R1:** Change user types, account validity periods, and basic permissions.  
- **R2:** Modify supported file types and maximum file size limits.
- **R4:** Alter authorization attributes: department, clearance_level, role, location, data_access, employment_status.  
- **R6:** Update file versioning policies (ACTIVE, HISTORICAL) and maximum retained version limits.
- **R7:** Update ABAC policies: add/edit/delete policies, adjust priorities and access conditions.
- **R8:** Manage Super Admin accounts: create/deactivate accounts, change permissions, reset passwords.
- **R9:** Update attribute schemas: add/edit/delete attributes, modify data types and valid values.
- **R14:** Adjust system configuration: CP-ABE, ABAC, Audit, Security.

---

### **1.3.12 Form 12 and Regulation 12**

**F12: Access Logs**  
Log ID: _______  
Timestamp: _______  
User ID: _______  
Resource ID: _______  
Requested Action: _______  
PDP Result: _______  
Applied Policy: _______  
User Attributes at Access Time: _______  
Environment Attributes: _______  
Error Details (if any): _______  

**R12:** Every access request (both successful and failed) must be recorded in the system logs. Logs must capture complete details regarding the user, resource, action, PDP decision, and attributes at the time of access. Log data is retained for a minimum of 12 months for audit and compliance purposes. Only Super Admins have the authority to view and export logs via the user interface.

Additionally, to facilitate integration with Security Information and Event Management (SIEM) solutions, the system continuously outputs these audit trails into 7 granular, structured JSON files within the `logs/` directory (`crypto-access-auth.json`, `crypto-access-storage.json`, `crypto-access-policy.json`, `crypto-access-user.json`, `crypto-access-attributes.json`, `crypto-access-audit.json`, `crypto-access-system.json`). These logs are enriched with context (e.g., `user.id`, `user.name`) for seamless ingestion and analysis by external SIEM platforms (e.g., Splunk, Wazuh, ELK Stack).

**Example:**  
F12: Access Logs  
Log ID: log_20250908_143052_001  
Timestamp: 2025-09-08T14:30:52+07:00  
User ID: 22520001  
Resource ID: 0ae91604-eff2-46cd-81f0-e714b5936ea3  
Requested Action: download  
PDP Result: ALLOW  
Applied Policy: ["it_department_access", "secret_clearance_access"]  
User Attributes: {"department": "it", "role": "manager", "clearance_level": "secret"}  
Environment Attributes: {"ip": "192.168.1.105", "time": "14:30", "device": "laptop_001"}  
Error Details: null  

---

### **1.3.13 Regulation 13 (Key Revocation via Invalidation)**

**R13:** When a user's attributes change (promotion, department transfer, resignation) or a security violation is detected, the system initiates the revocation of the user's current decryption capabilities for encrypted files.
Instead of maintaining a persistent Key Revocation List Collection like legacy systems, the revocation mechanism is minimally designed via **Redis cache invalidation**.
- Specifically: Upon attribute or account status alteration, the system calls a method to delete the byte array containing the user's CP-ABE Key (User Private Key) from the Redis cache.
- Effect: The user instantaneously loses decryption capability with the old key. Subsequent document requests will force the system to regenerate a new key based on the most recently updated attribute set (provided the user is still eligible).
*(Thus, maintaining F13: Key Revocation List as a form or collection is obsolete)*.

---

### **1.3.14 Form 14 and Regulation 14**

**F14: System Configuration**  
Config ID: _______  
Version: _______  
Updated Date: _______  
Updated By: _______  

**CP-ABE Configuration:**  
- Algorithm: _______  
- Key Length: _______  
- Key Expiry: _______  

**ABAC Configuration:**  
- Default Conflict Resolution Strategy: _______  
- Policy Cache Duration: _______  

**Audit Configuration:**  
- Log Retention Period: _______  
- Auto Report Export: _______  

**Security Configuration:**  
- Global IP Whitelist: _______  
- Session Duration: _______  
- Max Failed Login Attempts: _______  

**R14:** System configurations are centrally managed and only Super Admins are authorized to make modifications. All configuration changes must be recorded with version history. Default configurations apply upon system initialization and can be customized per enterprise requirements.

**Example:**  
F14: System Configuration  
Config ID: system_config_main  
Version: 1.2.0  
Updated Date: 08/09/2025  
Updated By: 21520001  

CP-ABE Configuration:  
- Algorithm: CP-ABE (BSW07)  
- Integration: AES-256-GCM (hybrid encryption)  
- Key Expiry: 365 days  

ABAC Configuration:  
- Default Conflict Strategy: deny-override  
- Policy Cache Duration: 300 seconds  

Audit Configuration:  
- Log Retention: 12 months  
- Auto Report: weekly  

Security Configuration:
- IP whitelist: `192.168.0.0/16`, `10.0.0.0/8`
- Session time: 8 hours (managed via HttpOnly Cookie containing JWT Access/Refresh Token to prevent XSS)
- Redis Configuration: Centralized Redis via django-redis to cache bytecodes of CP-ABE Keys on RAM
- Post-Quantum TLS: Enabled by default (Hybrid X25519MLKEM768 via OQS Nginx)
- Max failed login attempts: 5
- Content Security Policy (CSP): Enabled (strict mode) via Nginx to prevent XSS.
- Rate Limiting: 10 requests/minute (Download/Preview), 5 requests/minute (Upload) to prevent DoS.
- Impossible Travel: Detect and block logins from two distant geographical locations within < 30 minutes.
- Device & Session Management: Active sessions tracking with "Log out All Other Devices" feature.
- Audit Log Integrity: O(1) verify using Redis Hash Cache combined with Blockchain mechanisms.  

---

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
