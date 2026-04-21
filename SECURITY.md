# Security Architecture — Smart Tool Recognition

**Author:** Mahmoud Triki — W2069987, University of Westminster  
**© 2026 Mahmoud Triki. All rights reserved.**

---

## Overview

This document describes the security measures implemented in the Smart Tool Recognition system. The system consists of two components: a Flutter client (Windows / Android) and a Python FastAPI backend. Security is applied at the authentication, transport, data storage, and API layers.

---

## 1. Authentication

### 1.1 Two-Role Access Model

| Role  | Login method | What they can access |
|-------|-------------|----------------------|
| Staff | Name only (no password) | Camera identification, barcode scan, wrong-detection reports |
| Admin | Email + password | Full inventory management, reports review, AI training panel |

Staff accounts intentionally require no password — they only access read-only product data and submit correction reports. No destructive actions are available to staff.

### 1.2 Admin Password Hashing

Admin passwords are never stored in plain text. Before being stored or compared, passwords are converted to a SHA-256 digest:

```dart
// auth_service.dart
String _hashPassword(String password) {
  final bytes = utf8.encode(password);
  return sha256.convert(bytes).toString();
}
```

The hash is computed on the client before being checked against the local SQLite database. The raw password never leaves the device.

**Limitation acknowledged:** SHA-256 without a salt is vulnerable to rainbow table attacks if the database is physically stolen. For a production deployment, Argon2 or bcrypt with a per-user salt would be recommended. For this academic prototype, SHA-256 provides adequate protection against casual access.

### 1.3 Session Persistence

After a successful login, the session is stored in `SharedPreferences` (encrypted on Android, Windows AppData on desktop):

```dart
await prefs.setString('user_email', email);
await prefs.setString('user_name', name);
await prefs.setBool('is_admin', isAdmin);
```

Sessions persist across app restarts without requiring re-authentication.

### 1.4 Admin Creation

Admin accounts are created using an interactive CLI script that prompts for credentials at runtime — no hardcoded defaults:

```bash
python services/create_admin.py
# Admin email: <prompted>
# Admin name:  <prompted>
# Password:    <prompted, hidden>
```

---

## 2. Secrets Management

### 2.1 Environment Variables

All sensitive configuration values are loaded from a `.env` file at runtime and never hardcoded in source code:

```env
DATABASE_URL=postgresql://user:password@host:5432/dbname
YOLO_WEIGHTS=ultralytics/best.pt
CONFIDENCE_THRESHOLD=0.35
TOP_K=5
TYPE_DATASET_PATH=...
REPORTS_DIR=...
```

If `DATABASE_URL` is not set, the backend refuses to start with a clear error:

```python
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set.")
```

### 2.2 Git Exclusions

The `.gitignore` file excludes all sensitive files from version control:

```
.env
reported_images/
runs/
*.pt
.dart_tool/
build/
```

This ensures passwords, trained model weights, and user-submitted images are never published to the repository.

### 2.3 No Secrets in Source Code

The repository contains no hardcoded:
- Passwords or password hashes
- Email addresses
- Database connection strings
- IP addresses
- API keys

All placeholders in configuration files use `x.x.x.x` or `<your value here>` to guide setup without exposing real values.

---

## 3. Network Security

### 3.1 CORS Configuration

Cross-Origin Resource Sharing is controlled via an environment variable:

```python
_allowed_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)
```

In development, `CORS_ORIGINS=*` allows all origins for convenience. In production, this should be set to the specific Flutter app origin only.

### 3.2 LAN-Only Deployment

The FastAPI backend is bound to `0.0.0.0:8000` and intended for use on a private LAN only. It is not exposed to the public internet. The Flutter client communicates using the local IP address configured in `app_config.dart`.

### 3.3 Input Validation

All database queries use SQLAlchemy parameterized queries, preventing SQL injection:

```python
conn.execute(text("SELECT * FROM products WHERE sku = :sku"), {"sku": sku})
```

No raw string concatenation is used in any database query.

---

## 4. Data Storage Security

### 4.1 Local SQLite (Flutter Client)

The Flutter app uses a local SQLite database (`smart_tool.db`) for:
- Admin user session (email + password hash)
- Offline product cache

The database is stored in the app's private data directory, inaccessible to other applications without root access on Android or admin access on Windows.

### 4.2 PostgreSQL (Backend)

The backend uses PostgreSQL for all inventory, stock, shelf, and report data. Access is controlled by the `DATABASE_URL` credential which is only available on the server machine via the `.env` file.

### 4.3 Reported Images

Staff-submitted correction images are saved to a local directory defined by `REPORTS_DIR` in `.env`. This directory is:
- Git-ignored (never uploaded to the repository)
- Only accessible via authenticated admin API endpoints (`/admin/reports`)

---

## 5. API Security

### 5.1 Admin Endpoints

All `/admin/*` endpoints are intended for admin access only. The frontend enforces this by only rendering the admin panel after a successful admin login verification.

### 5.2 Report Submission

The `/report` endpoint accepts image uploads from staff. Uploaded files are:
- Saved with a UUID-based filename (prevents path traversal)
- Stored outside the web root (cannot be served directly)
- Reviewed by an admin before being used in training

```python
filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.jpg"
```

### 5.3 File Upload Safety

The `/detect` and `/report` endpoints accept image files. The backend reads and processes these through the YOLO model directly — no files are permanently stored in a publicly accessible location.

---

## 6. Known Limitations (Academic Prototype)

| Limitation | Impact | Production Recommendation |
|---|---|---|
| SHA-256 password hashing (no salt) | Vulnerable to rainbow tables if DB stolen | Use Argon2id or bcrypt with per-user salt |
| No JWT / bearer token auth on API | Any LAN device can call the API | Add token-based authentication |
| No HTTPS | Traffic readable on LAN | Deploy with TLS (nginx + Let's Encrypt) |
| No rate limiting | Brute force possible | Add FastAPI rate-limit middleware |
| Staff login has no password | Any name can log in as staff | Acceptable for internal hardware store use |

---

## 7. Security Testing Performed

- **Manual code review** — all source files scanned for hardcoded credentials, IP addresses, and personal information
- **Git history audit** — confirmed `.env` never committed; sensitive files excluded
- **Input path review** — confirmed all DB queries use parameterized inputs
- **Dependency review** — all packages from official pub.dev and PyPI sources

---

## 8. Summary

| Layer | Mechanism |
|---|---|
| Authentication | SHA-256 hashed password checked against local SQLite |
| Session | SharedPreferences (device-local, cleared on logout) |
| Secrets | Environment variables only, never in source code |
| Database queries | Parameterized (SQL injection protected) |
| File uploads | UUID filenames, stored outside web root |
| CORS | Configurable via env var, restricted method/header list |
| Git | `.env`, images, model weights all excluded |
