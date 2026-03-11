# Smart Tool Recognition

Smart Tool Recognition is a Flutter app plus a Python backend used to identify screws/tools from images, then retrieve inventory and shelf location data.

## How This Code Works

### Architecture

```text
Flutter app (lib/)
  -> calls FastAPI over HTTP
  -> keeps local session/admin auth state in SQLite

FastAPI backend (services/api.py)
  -> runs YOLO inference (services/detector.py)
  -> reads/writes products, stock, shelves, admin users in PostgreSQL
```

### Flutter flow

1. `lib/main.dart` initializes SQLite and app providers.
2. `AuthGate` sends users to `LoginPage`, `UserPage`, or `AdminPage`.
3. `DetectorService` uploads image files to `POST /detect`.
4. The predicted class is mapped to SKU and resolved to product details using backend endpoints.
5. `DatabaseService` wraps all product, shelf, and stock API calls.

### Backend flow

1. `services/api.py` loads env vars, initializes database tables, and loads YOLO weights.
2. Detection endpoint (`/detect`) runs model inference and returns top predictions.
3. CRUD endpoints manage products, shelves, and stock.
4. Additional endpoints support dataset photo upload and training jobs.

## Main Folders

```text
lib/
  pages/        Flutter screens (login, user, admin)
  services/     auth + backend API + detector client
  models/       app data models
  widgets/      reusable UI components
  utils/        theme and backend URL config

services/
  api.py        FastAPI app and endpoints
  detector.py   YOLO wrapper
  repository.py data helpers/import utilities
  .env.example  environment template
```

## Configuration

### Flutter backend URL

Set the backend URL in `lib/utils/app_config.dart`:

```dart
static const String backendUrl = 'http://<YOUR_IP_OR_HOST>:8000';
```

Use your LAN IP when running Flutter on a phone.

### Backend environment variables

Create `services/.env` from `services/.env.example` and set your values:

- `YOLO_WEIGHTS`
- `CONFIDENCE_THRESHOLD`
- `TOP_K`
- `DATASET_PATH`
- `DATABASE_URL`

## Run The Project

### Start backend

```bash
cd services
pip install -r "..\Requirements api.txt"
python -m uvicorn api:app --host 0.0.0.0 --port 8000
```

### Start Flutter app

```bash
flutter pub get
flutter run -d windows
```

Or run on Android:

```bash
flutter run -d <device-id>
```

## Default Admin Login

Seeded by the project:

- Email: `trikimahoud86@gmail.com`
- Password: `admin123`

Change this password before production use.

## Security Notes

- `.env` is ignored by git to avoid pushing secrets.
- If model files become large, use Git LFS for `*.pt`.
