# Setup Guide — Smart Tool Recognition

**Author:** Mahmoud Triki — W2069987, University of Westminster

This guide explains how to run the full system from a fresh clone using Docker.

---

## Requirements

| Tool | Version | Download |
|------|---------|----------|
| Docker Desktop | Latest | https://www.docker.com/products/docker-desktop |
| Flutter SDK | 3.x | https://docs.flutter.dev/get-started/install |
| Android phone (optional) | Android 8+ | — |

---

## Quick Start (Docker)

### 1. Clone the repository

```bash
git clone https://github.com/saibork100/smart_tool_flutter.git
cd smart_tool_flutter
```

### 2. Start the backend

```bash
docker-compose up --build
```

This will:
- Start a PostgreSQL database
- Build and start the FastAPI backend on port 8000
- Load the AI model (`best.pt`)
- Create all database tables automatically
- Create the default admin account

First build takes ~3–5 minutes (downloading Python packages and ML libraries).

### 3. Verify the backend is running

Open your browser and go to:
```
http://localhost:8000/health
```

You should see: `{"status": "ok", ...}`

---

## Run the Flutter App

### Windows Desktop

```powershell
flutter pub get
flutter run -d windows
```

The app connects to `http://localhost:8000` by default.

### Android Phone

1. Enable **Developer options** and **USB debugging** on your phone
2. Connect via USB or enable **Wireless debugging**
3. Find your PC's LAN IP address:
   ```powershell
   ipconfig
   # Look for IPv4 Address under your Wi-Fi adapter, e.g. 192.168.1.x
   ```
4. Run the app:
   ```powershell
   flutter run -d <device-id>
   ```
5. In the app, tap the **network icon** (bottom-right of the login screen) and enter:
   ```
   http://192.168.1.x:8000
   ```
   Replace `x` with your PC's actual IP address.

---

## Default Admin Login

| Field | Value |
|-------|-------|
| Email | `admin@smarttool.demo` |
| Password | `SmartTool2026` |

> **Change this password** after first login via Admin Panel → Settings → Change Password.

---

## Add Your Own Products

The database starts empty. To add products:

**Option A — CSV Import (recommended)**
1. Log in as admin
2. Go to **Import/Export** tab
3. Upload a CSV file with columns: `sku, barcode, name, brand, category, type, shelf_id`

**Option B — Manual entry**
1. Log in as admin
2. Go to **Products** tab → tap **+** to add products one by one

---

## Stop the Backend

```bash
docker-compose down
```

To also delete all database data:
```bash
docker-compose down -v
```

---

## Project Structure

```
smart_tool_flutter/
├── lib/                    Flutter app source (Dart)
├── services/               FastAPI backend (Python)
│   ├── api.py              All API endpoints
│   ├── detector.py         YOLO inference wrapper
│   ├── ultralytics/
│   │   └── best.pt         Trained AI model (YOLO11s-cls, 95 classes)
│   ├── Dockerfile          Docker image for the backend
│   └── requirements.txt    Python dependencies
├── docker-compose.yml      Orchestrates backend + PostgreSQL
├── SECURITY.md             Security architecture documentation
└── SETUP.md                This file
```

---

## AI Model

The app uses a **YOLO11s-cls** model trained to identify 95 fastener types:
- Screws (vis), Bolts (boulon), Nuts (écrou), Washers (rondelle), Rivets, Anchors (cheville)
- Current accuracy: ~66% Top-1 on the validation set
- The model runs on the backend (CPU inside Docker, GPU if available)

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `docker-compose up` fails | Make sure Docker Desktop is running |
| `http://localhost:8000` not reachable | Wait 30 seconds for the backend to fully start |
| Android app can't connect | Set the server URL to your PC's LAN IP (not localhost) |
| "No classes found" in Settings | The dataset folder is not mounted — this is expected in Docker; the AI model still works |
| Admin login fails | Default credentials: `admin@smarttool.demo` / `SmartTool2026` |
