# Smart Tool Recognition

**Author:** Mahmoud Triki — Student ID: W2069987  
**Institution:** University of Westminster  
**© 2026 Mahmoud Triki. All rights reserved.**

A Flutter app + FastAPI backend for identifying fasteners (screws, bolts, nuts, washers, rivets, anchors) from photos, retrieving inventory and shelf location data, and continuously improving the AI model through staff-reported corrections.

---

## Quick Start (Docker)

The entire backend runs with a single command — no Python, PostgreSQL, or ML library installation required.

### 1. Clone the repository

```bash
git clone https://github.com/saibork100/smart_tool_flutter.git
cd smart_tool_flutter
```

### 2. Start the backend

```bash
docker-compose up --build
```

This automatically:
- Starts PostgreSQL 15
- Builds the FastAPI backend and installs all Python dependencies
- Loads the trained AI model (`services/ultralytics/best.pt`)
- Creates all database tables
- Seeds the default admin account

First build: ~3–5 minutes. Subsequent starts: ~10 seconds.

### 3. Verify backend

Open `http://localhost:8000/health` — you should see `{"status": "ok", "model_loaded": true}`.

### 4. Run the Flutter app

```powershell
flutter pub get
flutter build windows
start build\windows\x64\runner\Release\smart_tool_recognition.exe
```

For Android, tap the network icon on the login screen and enter `http://<your-LAN-IP>:8000`.

### Default admin login

| Field | Value |
|-------|-------|
| Email | `admin@smarttool.demo` |
| Password | `SmartTool2026` |

> Change this password after first login via **Admin Panel → Settings → Change Password**.

---

## Architecture

```text
Flutter app (Dart)
  ├── AuthService      → POST /auth/login, POST /auth/change-password
  ├── DetectorService  → POST /detect, POST /report
  ├── DatabaseService  → products / stock / shelves CRUD (API + SQLite offline cache)
  └── UI pages         → login, staff (user), admin

FastAPI backend (Python)
  ├── YOLO11s-cls model   (services/detector.py)
  ├── PostgreSQL database (products, stock, shelves, admin_users, reports)
  └── Docker Compose      (backend + PostgreSQL containers)
```

### Key design decisions

- **Admin authentication** goes to the backend API (PostgreSQL), not local SQLite.
- **Offline cache**: products are cached in local SQLite so staff can search even when the backend is down.
- **Runtime URL config**: the backend URL is saved in SharedPreferences and configurable from the login screen — no rebuild needed when switching between localhost and LAN IP.
- **CSV import** sends products directly to the backend via `/products/bulk`.

---

## AI Model

| Property | Value |
|----------|-------|
| Architecture | YOLO11s-cls (classification) |
| Classes | 95 fastener types |
| Strategy | Type-classifier → returns all matching size variants from DB |
| Accuracy | ~66% Top-1 on validation set |
| Inference | CPU inside Docker, GPU if available |

**Class naming convention:** `vis__th__zinc__48__din933` (material + type + coating + size + standard)

---

## Active Learning Report System

Staff correct wrong detections. Corrections feed back into the training dataset.

**Staff flow:**
1. Take photo → AI detects item
2. Tap **"Wrong result?"** if incorrect
3. Select the correct class → submit
4. Image saved to `reported_images/{correct_class}/`

**Admin flow:**
1. Admin Panel → **Reports** tab
2. Review thumbnails (wrong vs. correct labels)
3. Confirm ✓ or reject ✗
4. **Submit batch** → copies confirmed images into `type_dataset/train/{class}/`
5. **Start Training** → retrains YOLO model, replaces `best.pt` live

---

## Project Structure

```text
smart_tool_flutter/
├── lib/
│   ├── pages/          login_page, user_page, admin_page
│   ├── services/       auth_service, database_service, detector_service
│   ├── models/         product.dart
│   ├── widgets/        backend_status_banner, product_card
│   └── utils/          app_theme.dart, app_config.dart
├── services/
│   ├── api.py          All FastAPI endpoints
│   ├── detector.py     YOLO inference wrapper
│   ├── ultralytics/
│   │   └── best.pt     Trained model (YOLO11s-cls, 95 classes)
│   ├── Dockerfile      Backend Docker image
│   └── requirements.txt
├── docker-compose.yml  Orchestrates backend + PostgreSQL
├── SECURITY.md         Security architecture documentation
├── SETUP.md            Full setup guide
└── README.md           This file
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Backend and model status |
| POST | `/detect` | AI classification on uploaded image |
| POST | `/report` | Submit wrong-detection report |
| GET | `/admin/reports` | List pending staff reports |
| POST | `/admin/reports/{id}/confirm` | Confirm a report |
| POST | `/admin/reports/{id}/reject` | Reject and delete a report |
| POST | `/admin/submit-batch` | Copy confirmed images to training dataset |
| POST | `/auth/login` | Admin login (returns name, email, role) |
| POST | `/auth/change-password` | Change admin password |
| GET/POST | `/products` | List / create products |
| POST | `/products/bulk` | Bulk upsert products from CSV import |
| GET | `/products/{sku}` | Get product by SKU |
| GET | `/products/barcode/{barcode}` | Get product by barcode |
| GET/POST | `/shelves` | Shelf CRUD |
| PUT | `/stock/{sku}` | Update stock levels |
| GET | `/dataset/classes` | List training dataset classes |
| POST | `/train` | Start model retraining job |
| GET | `/train/status` | Training progress and accuracy |
| GET | `/model/classes` | List all 95 model class names |

---

## Configuration

### Docker environment variables (`docker-compose.yml`)

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | *(set by compose)* | PostgreSQL connection string |
| `YOLO_WEIGHTS` | `ultralytics/best.pt` | Path to model weights |
| `CONFIDENCE_THRESHOLD` | `0.35` | Minimum detection confidence |
| `TOP_K` | `5` | Number of top predictions returned |
| `CORS_ORIGINS` | `*` | Allowed origins for CORS |
| `ADMIN_EMAIL` | `admin@smarttool.demo` | Seeded admin email |
| `ADMIN_PASSWORD` | `SmartTool2026` | Seeded admin password |

### Flutter backend URL

Configurable at runtime via the network icon on the login screen — no rebuild needed. Saved in SharedPreferences.

---

## Security

- All passwords hashed with SHA-256 before storage and transmission.
- No credentials, IPs, or secrets committed to Git.
- `.env`, `reported_images/`, `runs/`, `.venv/` are all git-ignored.
- Full security architecture documented in `SECURITY.md`.
