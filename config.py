from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/tool_shelf")
YOLO_WEIGHTS = os.getenv("YOLO_WEIGHTS", "ultralytics/yolov8n.pt")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "change-me-now")
