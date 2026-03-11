from __future__ import annotations
from typing import Optional
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError
from streamlit import json
from config import DATABASE_URL
import os
import secrets
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class Repository:
    def __init__(self) -> None:
        self.engine: Engine = create_engine(
            DATABASE_URL,
            pool_pre_ping=True,
            pool_recycle=1800,
            connect_args={"connect_timeout": 5},
        )

    # -------------------------------------------
    # Healthcheck
    # -------------------------------------------
    def healthcheck(self) -> dict:
        try:
            with self.engine.connect() as conn:
                products = conn.execute(text("SELECT COUNT(*) FROM products_min;")).scalar()
                candidates = conn.execute(text("SELECT COUNT(*) FROM tool_class_candidates;")).scalar()
            return {
                "products_min": int(products or 0),
                "tool_class_candidates": int(candidates or 0),
            }
        except OperationalError:
            return {"error": "Database connection failed. Check DATABASE_URL."}
        except Exception as e:
            return {"error": str(e)}

    # ---------------------------
    # Admin users
    # ---------------------------
    def admin_count(self) -> int:
        with self.engine.connect() as conn:
            return int(conn.execute(text("SELECT COUNT(*) FROM admin_users;")).scalar() or 0)

    # Note: create_admin and verify_admin below are legacy (password-based).
    # You can keep them if you still use password login alongside magic links.
    def create_admin(self, username: str, password: str) -> None:
        u = (username or "").strip().lower()
        if not u or not password:
            raise ValueError("Username and password required.")
        
        pw_hash = pwd_context.hash(password)
        q = text("INSERT INTO admin_users (username, password_hash, is_active) VALUES (:u, :h, true);")
        
        try:
            with self.engine.begin() as conn:
                conn.execute(q, {"u": u, "h": pw_hash})
        except Exception:
            raise ValueError("Could not create admin.")

    def verify_admin(self, username: str, password: str) -> bool:
        u = (username or "").strip().lower()
        if not u or not password: return False

        q = text("SELECT id, password_hash, is_active FROM admin_users WHERE username = :u LIMIT 1;")
        with self.engine.connect() as conn:
            row = conn.execute(q, {"u": u}).fetchone()
            if not row or not row[2]: # row[2] is is_active
                return False
            admin_id, pw_hash = row[0], row[1]

        if pwd_context.verify(password, pw_hash):
            with self.engine.begin() as conn:
                conn.execute(text("UPDATE admin_users SET last_login_at = now() WHERE id = :id;"), {"id": admin_id})
            return True
        return False

    # ---------------------------
    # Tool candidates
    # ---------------------------
    def get_tool_candidates(self) -> list[str]:
        q = text("SELECT class_name FROM tool_class_candidates ORDER BY class_name;")
        with self.engine.connect() as conn:
            return [r[0] for r in conn.execute(q).fetchall()]

    def add_tool_candidate(self, class_name: str, source: str = "admin") -> None:
        cn = (class_name or "").strip()
        if not cn: return
        q = text("INSERT INTO tool_class_candidates (class_name, source, product_count) VALUES (:cn, :src, 0) ON CONFLICT (class_name) DO NOTHING;")
        with self.engine.begin() as conn:
            conn.execute(q, {"cn": cn, "src": source})

    def delete_tool_candidate(self, class_name: str) -> None:
        cn = (class_name or "").strip()
        if not cn: return
        with self.engine.begin() as conn:
            conn.execute(text("DELETE FROM tool_class_candidates WHERE class_name = :cn;"), {"cn": cn})

    # ---------------------------
    # YOLO mappings
    # ---------------------------
    def map_yolo_label_to_tool_class(self, yolo_label: str) -> Optional[str]:
        y = (yolo_label or "").strip().lower()
        if not y: return None

        # Exact match
        with self.engine.connect() as conn:
            row = conn.execute(text("SELECT class_name FROM tool_class_candidates WHERE lower(class_name) = :y LIMIT 1;"), {"y": y}).fetchone()
            if row: return row[0]
            
            # Fuzzy match
            q2 = text("SELECT class_name FROM tool_class_candidates WHERE lower(class_name) LIKE :pat OR :y LIKE ('%' || lower(class_name) || '%') ORDER BY length(class_name) ASC LIMIT 1;")
            row2 = conn.execute(q2, {"pat": f"%{y}%", "y": y}).fetchone()
            return row2[0] if row2 else None

    # ---------------------------
    # Products
    # ---------------------------
    def find_products_for_tool(self, tool_class: str, limit: int = 20) -> list[dict]:
        tc = (tool_class or "").strip().lower()
        if not tc: return []
        q = text("""
            SELECT id, sku, name, main_category, sub_category, tags, weight_kg, length_cm, width_cm, height_cm, brand_id, stock_quantity, stock_status
            FROM products_min
            WHERE lower(coalesce(name,'')) LIKE :pat OR lower(coalesce(main_category,'')) LIKE :pat OR lower(coalesce(sub_category,'')) LIKE :pat OR lower(coalesce(tags,'')) LIKE :pat
            LIMIT :limit;
        """)
        with self.engine.connect() as conn:
            rows = conn.execute(q, {"pat": f"%{tc}%", "limit": limit}).mappings().all()
            return [dict(r) for r in rows]

    def guess_shelf(self, main_category: str | None, sub_category: str | None) -> str:
        mc, sc = (main_category or "").strip(), (sub_category or "").strip()
        if mc and sc: return f"{mc}  â†’  {sc}"
        return mc or sc or "Unknown shelf/category"

    # ---------------------------
    # Auth & Admin Management
    # ---------------------------
    def ensure_admin_exists(self, email: str) -> None:
        """Create admin row if it doesn't exist yet (email stored in username column)."""
        u = (email or "").strip().lower()
        if not u: raise ValueError("email required")
        
        with self.engine.connect() as conn:
            if conn.execute(text("SELECT 1 FROM admin_users WHERE username = :u LIMIT 1;"), {"u": u}).fetchone():
                return

        with self.engine.begin() as conn:
            conn.execute(text("INSERT INTO admin_users (username, password_hash, is_active) VALUES (:u, 'MAGIC_LINK_ONLY', TRUE)"), {"u": u})

    def create_magic_link(self, email: str) -> str:
        email = (email or "").strip().lower()
        if not email or "@" not in email: raise ValueError("Invalid email.")

        # Check if user is an invited admin
        if not self.is_invited_admin(email):
            raise ValueError("Access denied: You are not an invited administrator.")

        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=int(os.getenv("MAGIC_LINK_TTL_MIN", "10")))

        with self.engine.begin() as conn:
            conn.execute(
                text("INSERT INTO admin_magic_links (email, token, expires_at, used) VALUES (:email, :token, :expires, FALSE)"),
                {"email": email, "token": token, "expires": expires_at},
            )
        return token

    def consume_magic_link(self, token: str) -> str:
        token = (token or "").strip()
        if not token: raise ValueError("Missing token.")

        with self.engine.begin() as conn:
            row = conn.execute(
                text("SELECT id, email, expires_at, used FROM admin_magic_links WHERE token = :t LIMIT 1"),
                {"t": token},
            ).fetchone()

            if not row: raise ValueError("Invalid login link.")
            link_id, email, expires_at, used = row

            if used: raise ValueError("Link already used.")
            if expires_at <= datetime.now(timezone.utc): raise ValueError("Link expired.")

            conn.execute(text("UPDATE admin_magic_links SET used = TRUE WHERE id = :id"), {"id": link_id})

        self.ensure_admin_exists(email)
        return email

    def cleanup_magic_links(self) -> int:
        with self.engine.begin() as conn:
            res = conn.execute(text("DELETE FROM admin_magic_links WHERE expires_at < now() OR used = TRUE;"))
            return res.rowcount or 0

    # ---------------------------
    # New Secure Invitation System
    # ---------------------------

    def is_invited_admin(self, email: str) -> bool:
        """Checks if an email belongs to a verified admin (invite used)."""
        e = (email or "").strip().lower()
        if not e: return False
        
        # Updated to check 'is_used = TRUE' (verified)
        q = text("SELECT 1 FROM admin_invites WHERE email = :e AND is_used = TRUE LIMIT 1;")
        with self.engine.connect() as conn:
            return conn.execute(q, {"e": e}).fetchone() is not None

    def create_invite_code(self, email: str) -> str:
        """Generates a secure 24-hour key, saves it, and returns it."""
        code = secrets.token_urlsafe(16)
        expires_at = datetime.now() + timedelta(hours=24)
        
        q = text("""
            INSERT INTO admin_invites (email, invite_code, expires_at, is_used)
            VALUES (:email, :code, :expires, FALSE)
            ON CONFLICT (email) DO UPDATE 
            SET invite_code = :code, expires_at = :expires, is_used = FALSE
            RETURNING invite_code;
        """)
        
        with self.engine.begin() as conn:
            result = conn.execute(q, {"email": email, "code": code, "expires": expires_at})
            return result.scalar()

    def redeem_invite_code(self, code: str) -> str:
        """Validates the key. If valid, marks it used and returns the email."""
        q_check = text("SELECT id, email, expires_at, is_used FROM admin_invites WHERE invite_code = :code")
        
        with self.engine.begin() as conn:
            row = conn.execute(q_check, {"code": code}).fetchone()
            
            if not row: raise ValueError("Invalid invitation key.")
            
            id, email, expires_at, is_used = row
            
            if is_used: raise ValueError("This key has already been used.")
            if expires_at < datetime.now(): raise ValueError("This key has expired (24h limit).")
            
            # Mark as used (verified)
            conn.execute(text("UPDATE admin_invites SET is_used = TRUE WHERE id = :id"), {"id": id})
            
            # Ensure they are in the admin_users table so they can log in later
            self.ensure_admin_exists(email)
            
            return email
        
    # ---------------------------
    # Shelves
    # ---------------------------
    def list_shelves(self) -> list[dict]:
        q = text("""
            SELECT id, name, aisle, position, meta
            FROM shelves
            ORDER BY name;
        """)
        with self.engine.connect() as conn:
            return [dict(r) for r in conn.execute(q).mappings().all()]


    def create_shelf(self, name: str, aisle: str | None = None, position: str | None = None) -> int:
        n = (name or "").strip()
        if not n:
            raise ValueError("Shelf name is required.")

        q = text("""
            INSERT INTO shelves (name, aisle, position)
            VALUES (:name, :aisle, :position)
            ON CONFLICT (name) DO NOTHING
            RETURNING id;
        """)
        with self.engine.begin() as conn:
            res = conn.execute(q, {
                "name": n,
                "aisle": aisle,
                "position": position
            }).scalar()
            return int(res) if res else None


    def update_shelf(self, shelf_id: int, name: str, aisle: str | None, position: str | None, meta: dict | None) -> None:
        n = (name or "").strip()
        if not n:
            raise ValueError("Shelf name is required.")

        q = text("""
            UPDATE shelves
            SET name = :name,
                aisle = :aisle,
                position = :position,
                meta = :meta::jsonb
            WHERE id = :id;
        """)

        with self.engine.begin() as conn:
            conn.execute(q, {
                "id": shelf_id,
                "name": n,
                "aisle": (aisle or "").strip() or None,
                "position": (position or "").strip() or None,
                "meta": json.dumps(meta or {}),
            })

    # ---------------------------
    # Products + shelf assignment
    # ---------------------------
    def get_products_admin(self, limit: int = 500, offset: int = 0) -> list[dict]:
        q = text("""
            SELECT
                p.id,
                p.sku,
                p.name,
                p.regular_price,
                p.stock_status,
                s.id   AS shelf_id,
                s.name AS shelf_name
            FROM products_min p
            LEFT JOIN product_shelf ps ON ps.product_id = p.id
            LEFT JOIN shelves s ON s.id = ps.shelf_id
            ORDER BY p.id
            LIMIT :limit OFFSET :offset;
        """)
        with self.engine.connect() as conn:
            return [
                dict(r)
                for r in conn.execute(q, {"limit": limit, "offset": offset}).mappings().all()
            ]



    def set_product_shelf(self, product_id: str, shelf_id: int | None) -> None:
        q = text("""
            INSERT INTO product_shelf (product_id, shelf_id)
            VALUES (:pid, :sid)
            ON CONFLICT (product_id)
            DO UPDATE SET shelf_id = EXCLUDED.shelf_id, updated_at = now();
        """)
        with self.engine.begin() as conn:
            conn.execute(q, {"pid": product_id, "sid": shelf_id})

    def delete_shelf(self, shelf_id: int) -> None:
        q = text("DELETE FROM shelves WHERE id = :id;")
        with self.engine.begin() as conn:
            conn.execute(q, {"id": shelf_id})
