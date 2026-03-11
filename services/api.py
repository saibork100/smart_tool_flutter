"""
FastAPI backend for Smart Tool Recognition.
Run with: python -m uvicorn api:app --host 0.0.0.0 --port 8000
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from PIL import Image
from pathlib import Path
from typing import Optional
import io, os, threading, time, shutil, re
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    print("HEIC support enabled.")
except ImportError:
    print("Warning: pillow-heif not installed, HEIC files won't work.")

load_dotenv()

# ── App setup ──────────────────────────────────────────────────────────────────
app = FastAPI(title="Smart Tool Recognition API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Config ─────────────────────────────────────────────────────────────────────
YOLO_WEIGHTS         = os.getenv("YOLO_WEIGHTS", "ultralytics/best.pt")
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.35"))
TOP_K                = int(os.getenv("TOP_K", "3"))
DATASET_PATH         = os.getenv("DATASET_PATH", r"E:\photo coliction\dataset")
DATABASE_URL         = os.getenv("DATABASE_URL", "postgresql://postgres:admin123@localhost:5432/smart_tool")

# ── Database setup ─────────────────────────────────────────────────────────────
engine = create_engine(DATABASE_URL)

def init_db():
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS shelf_locations (
                shelf_id  TEXT PRIMARY KEY,
                aisle     TEXT NOT NULL,
                bay       TEXT NOT NULL,
                zone      TEXT,
                notes     TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS products (
                sku                  TEXT PRIMARY KEY,
                barcode              TEXT UNIQUE,
                name                 TEXT NOT NULL,
                brand                TEXT NOT NULL,
                category             TEXT NOT NULL,
                type                 TEXT NOT NULL DEFAULT 'tool',
                description          TEXT,
                shelf_id             TEXT REFERENCES shelf_locations(shelf_id),
                last_updated         TIMESTAMP DEFAULT NOW()
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS stock (
                sku                   TEXT PRIMARY KEY REFERENCES products(sku),
                quantity_on_shelf     INTEGER DEFAULT 0,
                quantity_in_backstore INTEGER DEFAULT 0,
                status                TEXT DEFAULT 'in_stock'
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS admin_users (
                id            SERIAL PRIMARY KEY,
                email         TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                name          TEXT,
                role          TEXT DEFAULT 'admin',
                is_active     INTEGER DEFAULT 1,
                created_at    TIMESTAMP DEFAULT NOW()
            )
        """))
        # Seed default admin (password: admin123)
        conn.execute(text("""
            INSERT INTO admin_users (email, password_hash, name, role, is_active)
            VALUES ('trikimahoud86@gmail.com',
                    '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9',
                    'Admin', 'admin', 1)
            ON CONFLICT (email) DO NOTHING
        """))
        conn.commit()
    print("Database initialized.")

init_db()

# ── SKU → Label mapping ────────────────────────────────────────────────────────
SKU_TO_LABEL = {
    "GAVHC410": "4mm_10mm", "GAVHC416": "4mm_16mm", "GAVHC420": "4mm_20mm",
    "GAVHC425": "4mm_25mm", "GAVHC430": "4mm_30mm", "GAVHC440": "4mm_40mm",
    "GAVHC450": "4mm_50mm", "GAVHC510": "5mm_10mm", "GAVHC516": "5mm_16mm",
    "GAVHC520": "5mm_20mm", "GAVHC525": "5mm_25mm", "GAVHC530": "5mm_30mm",
    "GAVHC540": "5mm_40mm", "GAVHC550": "5mm_50mm", "GAVHC612": "6mm_12mm",
    "GAVHC616": "6mm_16mm", "GAVHC620": "6mm_20mm", "GAVHC625": "6mm_25mm",
    "GAVHC630": "6mm_30mm", "GAVHC640": "6mm_40mm", "GAVHC650": "6mm_50mm",
    "GAVHC660": "6mm_60mm", "GAVHC670+": "6mm_70mm", "GAVHC680+": "6mm_80mm",
    "GAVHC6100+": "6mm_100mm",
}

def sku_to_label(sku: str) -> str | None:
    if sku in SKU_TO_LABEL:
        return SKU_TO_LABEL[sku]
    m = re.match(r"GAVHC(\d)(\d+)\+?$", sku)
    if m:
        return f"{m.group(1)}mm_{m.group(2)}mm"
    return None

# ── Load detector ──────────────────────────────────────────────────────────────
print(f"Loading model from: {YOLO_WEIGHTS}")
try:
    from detector import Detector
    detector = Detector(weights_path=YOLO_WEIGHTS)
    print("Model loaded successfully.")
except Exception as e:
    print(f"Warning: Could not load model: {e}")
    detector = None

# ── Training state ─────────────────────────────────────────────────────────────
train_state = {
    "running": False, "progress": 0, "total_epochs": 0,
    "current_epoch": 0, "top1_acc": None, "status": "idle", "message": "",
}

# ── Pydantic models ────────────────────────────────────────────────────────────
class ProductModel(BaseModel):
    sku: str
    barcode: Optional[str] = None
    name: str
    brand: str
    category: str
    type: str = "tool"
    description: Optional[str] = None
    shelf_id: Optional[str] = None

class ShelfModel(BaseModel):
    shelf_id: str
    aisle: str
    bay: str
    zone: Optional[str] = None
    notes: Optional[str] = None

class StockModel(BaseModel):
    quantity_on_shelf: int = 0
    quantity_in_backstore: int = 0

class AdminLoginModel(BaseModel):
    email: str
    password_hash: str

# ── Health ─────────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {
        "status": "ok",
        "model_loaded": detector is not None,
        "model_path": YOLO_WEIGHTS,
    }

# ── Detect ─────────────────────────────────────────────────────────────────────
@app.post("/detect")
async def detect(file: UploadFile = File(...)):
    if detector is None:
        raise HTTPException(status_code=503, detail="Model not loaded.")
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty file received.")
    try:
        image = Image.open(io.BytesIO(contents)).convert("RGB")
        image.load()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image: {str(e)}")
    try:
        detections = detector.predict(image, conf=CONFIDENCE_THRESHOLD)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference failed: {str(e)}")
    if not detections:
        return {"predicted_label": None, "confidence": 0.0,
                "threshold": CONFIDENCE_THRESHOLD, "top_predictions": []}
    top = detections[:TOP_K]
    best = top[0]
    return {
        "predicted_label": best.label,
        "confidence": round(best.conf, 4),
        "threshold": CONFIDENCE_THRESHOLD,
        "top_predictions": [{"label": d.label, "confidence": round(d.conf, 4)} for d in top],
    }

# ── Products ───────────────────────────────────────────────────────────────────
@app.get("/products")
def get_products(search: str = ""):
    with engine.connect() as conn:
        if search:
            q = f"%{search.lower()}%"
            rows = conn.execute(text("""
                SELECT p.*, s.aisle, s.bay, s.zone,
                       st.quantity_on_shelf, st.quantity_in_backstore, st.status
                FROM products p
                LEFT JOIN shelf_locations s ON p.shelf_id = s.shelf_id
                LEFT JOIN stock st ON p.sku = st.sku
                WHERE LOWER(p.name) LIKE :q OR LOWER(p.sku) LIKE :q
                   OR LOWER(p.brand) LIKE :q OR LOWER(p.category) LIKE :q
                ORDER BY p.name LIMIT 50
            """), {"q": q})
        else:
            rows = conn.execute(text("""
                SELECT p.*, s.aisle, s.bay, s.zone,
                       st.quantity_on_shelf, st.quantity_in_backstore, st.status
                FROM products p
                LEFT JOIN shelf_locations s ON p.shelf_id = s.shelf_id
                LEFT JOIN stock st ON p.sku = st.sku
                ORDER BY p.name
            """))
        return [dict(r._mapping) for r in rows]

@app.get("/products/{sku}")
def get_product(sku: str):
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT p.*, s.aisle, s.bay, s.zone,
                   st.quantity_on_shelf, st.quantity_in_backstore, st.status
            FROM products p
            LEFT JOIN shelf_locations s ON p.shelf_id = s.shelf_id
            LEFT JOIN stock st ON p.sku = st.sku
            WHERE p.sku = :sku
        """), {"sku": sku})
        row = rows.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Product not found")
        return dict(row._mapping)

@app.get("/products/barcode/{barcode}")
def get_product_by_barcode(barcode: str):
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT p.*, s.aisle, s.bay, s.zone,
                   st.quantity_on_shelf, st.quantity_in_backstore, st.status
            FROM products p
            LEFT JOIN shelf_locations s ON p.shelf_id = s.shelf_id
            LEFT JOIN stock st ON p.sku = st.sku
            WHERE p.barcode = :barcode
        """), {"barcode": barcode})
        row = rows.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Product not found")
        return dict(row._mapping)

@app.post("/products")
def create_product(p: ProductModel):
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO products (sku, barcode, name, brand, category, type, description, shelf_id)
            VALUES (:sku, :barcode, :name, :brand, :category, :type, :description, :shelf_id)
            ON CONFLICT (sku) DO UPDATE SET
                barcode=EXCLUDED.barcode, name=EXCLUDED.name, brand=EXCLUDED.brand,
                category=EXCLUDED.category, type=EXCLUDED.type,
                description=EXCLUDED.description, shelf_id=EXCLUDED.shelf_id,
                last_updated=NOW()
        """), p.model_dump())
        conn.execute(text("""
            INSERT INTO stock (sku) VALUES (:sku)
            ON CONFLICT (sku) DO NOTHING
        """), {"sku": p.sku})
        conn.commit()
    return {"message": "Product saved", "sku": p.sku}

@app.delete("/products/{sku}")
def delete_product(sku: str):
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM stock WHERE sku = :sku"), {"sku": sku})
        conn.execute(text("DELETE FROM products WHERE sku = :sku"), {"sku": sku})
        conn.commit()
    return {"message": "Product deleted"}

@app.post("/products/bulk")
def bulk_upsert_products(products: list[ProductModel]):
    with engine.connect() as conn:
        for p in products:
            conn.execute(text("""
                INSERT INTO products (sku, barcode, name, brand, category, type, description, shelf_id)
                VALUES (:sku, :barcode, :name, :brand, :category, :type, :description, :shelf_id)
                ON CONFLICT (sku) DO UPDATE SET
                    barcode=EXCLUDED.barcode, name=EXCLUDED.name, brand=EXCLUDED.brand,
                    category=EXCLUDED.category, type=EXCLUDED.type,
                    description=EXCLUDED.description, shelf_id=EXCLUDED.shelf_id,
                    last_updated=NOW()
            """), p.model_dump())
            conn.execute(text("""
                INSERT INTO stock (sku) VALUES (:sku)
                ON CONFLICT (sku) DO NOTHING
            """), {"sku": p.sku})
        conn.commit()
    return {"message": f"{len(products)} products saved"}

# ── Shelves ────────────────────────────────────────────────────────────────────
@app.get("/shelves")
def get_shelves():
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT * FROM shelf_locations ORDER BY aisle, bay"))
        return [dict(r._mapping) for r in rows]

@app.post("/shelves")
def create_shelf(s: ShelfModel):
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO shelf_locations (shelf_id, aisle, bay, zone, notes)
            VALUES (:shelf_id, :aisle, :bay, :zone, :notes)
            ON CONFLICT (shelf_id) DO UPDATE SET
                aisle=EXCLUDED.aisle, bay=EXCLUDED.bay,
                zone=EXCLUDED.zone, notes=EXCLUDED.notes
        """), s.model_dump())
        conn.commit()
    return {"message": "Shelf saved", "shelf_id": s.shelf_id}

@app.delete("/shelves/{shelf_id}")
def delete_shelf(shelf_id: str):
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM shelf_locations WHERE shelf_id = :id"), {"id": shelf_id})
        conn.commit()
    return {"message": "Shelf deleted"}

# ── Stock ──────────────────────────────────────────────────────────────────────
@app.put("/stock/{sku}")
def update_stock(sku: str, s: StockModel):
    status = "out_of_stock" if s.quantity_on_shelf == 0 else "low_stock" if s.quantity_on_shelf < 5 else "in_stock"
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO stock (sku, quantity_on_shelf, quantity_in_backstore, status)
            VALUES (:sku, :on_shelf, :backstore, :status)
            ON CONFLICT (sku) DO UPDATE SET
                quantity_on_shelf=EXCLUDED.quantity_on_shelf,
                quantity_in_backstore=EXCLUDED.quantity_in_backstore,
                status=EXCLUDED.status
        """), {"sku": sku, "on_shelf": s.quantity_on_shelf,
               "backstore": s.quantity_in_backstore, "status": status})
        conn.commit()
    return {"message": "Stock updated"}

# ── Admin auth ─────────────────────────────────────────────────────────────────
@app.post("/auth/login")
def login(body: AdminLoginModel):
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT * FROM admin_users
            WHERE email = :email AND password_hash = :hash AND is_active = 1
        """), {"email": body.email, "hash": body.password_hash})
        row = rows.fetchone()
        if not row:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        r = dict(row._mapping)
        return {"name": r["name"], "email": r["email"], "role": r["role"]}

# ── Dataset management ─────────────────────────────────────────────────────────
@app.get("/dataset/classes")
def get_classes():
    result = []
    train_dir = Path(DATASET_PATH) / "train"
    if train_dir.exists():
        for folder in sorted(train_dir.iterdir()):
            if folder.is_dir():
                count = sum(len(list(folder.glob(f"*.{ext}"))) for ext in ["jpg","jpeg","png"])
                sku = next((k for k, v in SKU_TO_LABEL.items() if v == folder.name), None)
                result.append({"class_name": folder.name, "sku": sku, "photo_count": count})
    return result

@app.post("/dataset/add-photos")
async def add_photos(sku: str, files: list[UploadFile] = File(...)):
    label = sku_to_label(sku)
    if not label:
        raise HTTPException(status_code=400, detail=f"Cannot determine training class for SKU: {sku}")
    train_folder = Path(DATASET_PATH) / "train" / label
    val_folder   = Path(DATASET_PATH) / "val"   / label
    train_folder.mkdir(parents=True, exist_ok=True)
    val_folder.mkdir(parents=True, exist_ok=True)
    saved = 0
    for i, file in enumerate(files):
        contents = await file.read()
        try:
            img = Image.open(io.BytesIO(contents)).convert("RGB")
            img.load()
        except Exception:
            continue
        filename = f"upload_{int(time.time())}_{i}.jpg"
        dest = val_folder / filename if (i % 5 == 0) else train_folder / filename
        img.save(str(dest), "JPEG")
        saved += 1
    return {"saved": saved, "label": label, "sku": sku}

# ── Training ───────────────────────────────────────────────────────────────────
@app.post("/train")
def start_training(epochs: int = 50, dataset: str = None):
    if train_state["running"]:
        raise HTTPException(status_code=409, detail="Training already in progress.")
    ds = dataset or DATASET_PATH
    def run():
        try:
            from ultralytics import YOLO
            train_state.update({"running": True, "status": "running",
                "total_epochs": epochs, "current_epoch": 0,
                "progress": 0, "message": "Starting training..."})
            output_dir = os.path.abspath(os.path.join(os.path.dirname(YOLO_WEIGHTS), "..", "runs"))
            model = YOLO("yolov8n-cls.pt")
            def on_epoch_end(trainer):
                ep  = trainer.epoch + 1
                acc = round(float(trainer.metrics.get("metrics/accuracy_top1", 0)), 4)
                train_state.update({"current_epoch": ep,
                    "progress": int((ep / epochs) * 100), "top1_acc": acc,
                    "message": f"Epoch {ep}/{epochs} — Top1: {acc}"})
            model.add_callback("on_train_epoch_end", on_epoch_end)
            model.train(data=ds, epochs=epochs, imgsz=224,
                project=output_dir, name="screw_classifier", exist_ok=True, verbose=False)
            best_src = os.path.join(output_dir, "screw_classifier", "weights", "best.pt")
            shutil.copy2(best_src, os.path.abspath(YOLO_WEIGHTS))
            global detector
            from detector import Detector
            detector = Detector(weights_path=YOLO_WEIGHTS)
            train_state.update({"status": "done", "progress": 100,
                "message": f"Training complete! Top1 accuracy: {train_state['top1_acc']}"})
        except Exception as e:
            train_state.update({"status": "error", "message": str(e)})
        finally:
            train_state["running"] = False
    threading.Thread(target=run, daemon=True).start()
    return {"message": "Training started."}

@app.get("/train/status")
def train_status():
    return train_state
