# NutriQ Security & Privacy Architecture

## Security Implementations
- **Password Security**: Password hashing with cryptographic salts (PBKDF2-SHA256 with 100,000 iterations / bcrypt).
- **Authentication**: JWT access tokens signed with HMAC-SHA256 (`HS256`) and short-lived expiry.
- **Authorization & Ownership**: Strict server-side validation ensuring users can only access their own meals, goals, and profiles.
- **Role-Based Access Control (RBAC)**: Distinct User and Admin roles; all administrator actions are recorded in `audit_logs`.
- **Zero Secret Exposure**: Third-party API keys (Claude, Vision, Speech) are strictly confined to backend environment variables.
- **Input Validation**: Strict Pydantic v2 schemas reject malformed payloads before execution.

## Privacy & Compliance Governance
- **Mandatory Consent Flow**: Users must explicitly accept Terms of Service, Privacy Policy, and AI Health Data Processing consent before account activation.
- **Consent Audit Trail**: Stored in `consent_records` with version timestamps.
- **Data Export Workflow**: Complete user history exportable as a machine-readable JSON/CSV archive (`GET /api/privacy/export`).
- **Cascading Deletion**: Account deletion completely purges all associated meals, health metrics, and sync history (`DELETE /api/privacy/account`).
- **Raw Media Retention Policy**: Food photos and voice recordings are processed ephemerally and deleted by default post-analysis.
