# Smart Tool Recognition

**Author:** Mahmoud Triki — Student ID: W2069987  
**Institution:** University of Westminster  
**© 2026 Mahmoud Triki. All rights reserved.**

A Flutter app + Python backend for identifying fasteners (screws, bolts, nuts, washers, rivets, anchors) from photos, retrieving inventory and shelf location data, and continuously improving the AI model through staff-reported corrections.

## Architecture

```text
Flutter app (lib/)
  → DetectorService  → POST /detect      (AI classification)
  → DetectorService  → POST /report      (wrong-detection reports)
  → DatabaseService  → products/stock/shelves CRUD
  → AuthService      → session + admin auth (local SQLite)

FastAPI backend (services/api.py)
  → YOLO11s-cls model (services/detector.py)
  → PostgreSQL  (products, stock, shelves, admin_users, reports)
```

## Model

- **Architecture**: YOLO11s-cls (classification)
- **Classes**: 95 fastener types (vis, boulon, écrou, rondelle, rivet, cheville)
- **Strategy**: type-classifier — model identifies the product type (e.g. `vis__th__zinc__48__din933`), then the API returns all matching size variants from the database
- **Current accuracy**: ~66% top-1 (improving via active learning reports)
- **Dataset**: `E:\photo coliction\type_dataset\` (train + val splits)

## Active Learning Report System

Staff can correct wrong detections directly from the app. Each correction feeds back into the training dataset.

### Staff flow
1. Take photo → AI detects item
2. Tap **"Wrong result?"** button
3. Select the correct class from the dropdown
4. Submit → image saved to `reported_images/{correct_class}/`

### Admin flow
1. Open Admin Panel → **Reports** tab
2. Review each reported image (thumbnail + wrong/correct labels)
3. Tap ✓ to confirm or ✗ to reject
4. Tap **Submit** → confirmed images copied to `type_dataset/train/{class}/`
5. Retrain the model to incorporate new images

## Main Folders

```text
lib/
  pages/        Flutter screens (login, user, admin)
  services/     auth + backend API + detector client
  models/       app data models
  widgets/      reusable UI (product card, report dialog)
  utils/         theme and backend URL config

services/
  api.py                    FastAPI app — all endpoints
  detector.py               YOLO inference wrapper
  measure.py                Ruler-based bolt measurement
  repository.py             Data helpers and CSV import utilities
  dataset_builder.py        Dataset prep + augmentation
  image_downloader.py       icrawler-based image collector
  clean_dataset.py          Dataset integrity checker
  audit_val_with_model.py   Automated val audit using trained model
  delete_bad_val_images.py  Removes audited bad val images
  migrate_parent_class.py   One-shot DB migration for parent_class column
  extract_skus.py           SKU extraction utility
  import_csv.py             Bulk product import from CSV
  create_admin.py           Admin user creation utility
  check_db.py               Database connection checker
```

## Configuration

### Flutter backend URL

Edit `lib/utils/app_config.dart`:

```dart
static const String backendUrl = 'http://<YOUR_LAN_IP>:8000';
```

Use your LAN IP when running Flutter on a phone.

### Backend environment variables

Create `services/.env`:

```env
YOLO_WEIGHTS=ultralytics/best.pt
CONFIDENCE_THRESHOLD=0.35
TOP_K=5
DATASET_PATH=E:\photo coliction\dataset
TYPE_DATASET_PATH=E:\photo coliction\type_dataset
REPORTS_DIR=D:\smart_tool_flutter\reported_images
DATABASE_URL=postgresql://postgres:password@localhost:5432/smart_tool
```

## Run The Project

### Start backend

```powershell
cd services
pip install -r "..\Requirements api.txt"
python -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

### Start Flutter app

```powershell
flutter pub get
flutter run -d windows        # desktop
flutter run -d <device-id>    # Android phone
```

## Retrain the model

After submitting a batch of confirmed reports:

```powershell
yolo train model=yolo11s-cls.pt data="E:/photo coliction/type_dataset" epochs=50 imgsz=224 batch=32 project=runs/classify name=type_v3 workers=4
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/detect` | Run AI classification on uploaded image |
| POST | `/measure` | Ruler-based bolt measurement |
| POST | `/report` | Submit wrong-detection report |
| GET | `/admin/reports` | List pending reports |
| POST | `/admin/reports/{id}/confirm` | Confirm a report |
| POST | `/admin/reports/{id}/reject` | Reject + delete a report |
| POST | `/admin/submit-batch` | Copy confirmed images to training dataset |
| GET | `/model/classes` | List all 95 model class names |
| GET/POST | `/products` | Product CRUD |
| GET/POST | `/shelves` | Shelf CRUD |
| PUT | `/stock/{sku}` | Update stock levels |
| POST | `/train` | Start model training job |
| GET | `/train/status` | Training progress |

## Default Admin Login

- Email: `trikimahoud86@gmail.com`
- Password: `admin123`

Change this password before production use.

## Security Notes

- `.env` is git-ignored — never commit secrets.
- `reported_images/`, `runs/`, `.venv311/` are git-ignored.
- If model `.pt` files become large, use Git LFS.
