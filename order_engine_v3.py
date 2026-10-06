# -*- coding: utf-8 -*-
"""SastoukaStore ORDER ENGINE V3 — validation et création des commandes."""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any

SastoukaStore_ICON_PATH_6_6 = Path(__file__).resolve().parent / "static" / "icons" / "sastoukastore-icon.png"

ROOT = Path(__file__).resolve().parent
DB = ROOT / "data" / "chariow.db"

ALLOWED_PAYMENT_METHODS = {"paypal", "flooz", "tmoney", "wave", "card", "cash_delivery"}
MAX_QTY = 100


def _normalize_phone(value: Any) -> str:
    try:
        from phone_utils import normalize_phone
        return normalize_phone(value)
    except Exception:
        raw = str(value or "").strip()
        if not raw or not re.fullmatch(r"[0-9\s().+\-/]+", raw):
            return ""
        digits = re.sub(r"\D", "", raw)
        if not digits:
            return ""
        compact = re.sub(r"[\s().\-/]", "", raw)
        if compact.startswith("00") and len(digits) >= 3:
            return "+" + digits[2:]
        if compact.startswith("+"):
            return "+" + digits
        return digits


def _valid_phone(phone: str) -> bool:
    try:
        from phone_utils import is_valid_phone
        return is_valid_phone(phone)
    except Exception:
        return 8 <= len(phone.lstrip("+")) <= 15


def _valid_email(email: str) -> bool:
    if not email:
        return True
    return bool(re.fullmatch(
        r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
        r"[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+", email
    ))


def _table_exists(con: sqlite3.Connection, name: str) -> bool:
    return bool(con.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone())


def ensure_order_schema(con: sqlite3.Connection) -> None:
    con.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            unit_price REAL NOT NULL DEFAULT 0,
            quantity INTEGER NOT NULL DEFAULT 1,
            subtotal REAL NOT NULL DEFAULT 0,
            variant TEXT DEFAULT '',
            FOREIGN KEY(order_id) REFERENCES orders(id)
        )
    """)
    cols = {r[1] for r in con.execute("PRAGMA table_info(order_items)").fetchall()}
    if "variant" not in cols:
        con.execute("ALTER TABLE order_items ADD COLUMN variant TEXT DEFAULT ''")


def _ensure_base_tables(con: sqlite3.Connection) -> None:
    if not _table_exists(con, "customers"):
        con.execute("""
            CREATE TABLE customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                email TEXT DEFAULT '',
                address TEXT DEFAULT '',
                city TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    if not _table_exists(con, "orders"):
        con.execute("""
            CREATE TABLE orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER,
                total REAL NOT NULL DEFAULT 0,
                payment_method TEXT DEFAULT 'cash_delivery',
                payment_status TEXT DEFAULT 'pending',
                delivery_status TEXT DEFAULT 'pending',
                notes TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    order_cols = {r[1] for r in con.execute("PRAGMA table_info(orders)").fetchall()}
    if "currency" not in order_cols:
        con.execute("ALTER TABLE orders ADD COLUMN currency TEXT DEFAULT 'FCFA'")


def _find_customer(con: sqlite3.Connection, phone: str):
    row = con.execute(
        "SELECT id, phone FROM customers WHERE phone=? ORDER BY id DESC LIMIT 1",
        (phone,),
    ).fetchone()
    if row:
        return row
    digits = phone.lstrip("+")
    return con.execute(
        """
        SELECT id, phone FROM customers
        WHERE REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(COALESCE(phone,''),' ',''),'-',''),'.',''),'(',''),')','') LIKE ?
        ORDER BY id DESC LIMIT 1
        """,
        (f"%{digits}",),
    ).fetchone()


def process_order(payload: dict[str, Any], *, require_address: bool = False):
    """Retourne (dict JSON, code HTTP). Supporte les 2 payloads actuels."""
    if not isinstance(payload, dict):
        return {"ok": False, "message": "Données de commande invalides."}, 400

    customer = payload.get("customer") if isinstance(payload.get("customer"), dict) else {}
    name = str(customer.get("name") or payload.get("name") or "").strip()
    phone = _normalize_phone(customer.get("phone") or payload.get("phone") or "")
    email = str(customer.get("email") or payload.get("email") or "").strip()
    address = str(customer.get("address") or payload.get("address") or "").strip()
    city = str(customer.get("city") or payload.get("city") or "").strip()
    payment_method = str(payload.get("payment_method") or "flooz").strip().lower()
    notes = str(payload.get("notes") or "").strip()
    items = payload.get("items")

    if isinstance(items, str):
        try:
            import json
            items = json.loads(items)
        except Exception:
            items = None

    if not name:
        return {"ok": False, "message": "Le nom du client est obligatoire."}, 400
    if not phone or not _valid_phone(phone):
        return {"ok": False, "message": "Le numéro de téléphone / WhatsApp est invalide."}, 400
    if not _valid_email(email):
        return {"ok": False, "message": "L'adresse e-mail est invalide."}, 400
    if require_address and not address:
        return {"ok": False, "message": "L'adresse du client est obligatoire."}, 400
    if payment_method not in ALLOWED_PAYMENT_METHODS:
        return {"ok": False, "message": "Moyen de paiement non reconnu."}, 400
    if not isinstance(items, list) or not items:
        return {"ok": False, "message": "Votre panier est vide."}, 400
    if len(items) > 50:
        return {"ok": False, "message": "Le panier contient trop d'articles."}, 400

    con = sqlite3.connect(DB, timeout=15.0)
    con.row_factory = sqlite3.Row
    try:
        _ensure_base_tables(con)
        ensure_order_schema(con)
        product_cols = {r[1] for r in con.execute("PRAGMA table_info(products)").fetchall()}
        for needed in ("id", "name", "price", "active"):
            if needed not in product_cols:
                return {"ok": False, "message": "La base produits est incomplète."}, 500

        has_type = "product_type" in product_cols
        has_pdf = "pdf_file" in product_cols
        has_currency = "currency" in product_cols
        variants_exist = _table_exists(con, "product_variants")

        con.execute("BEGIN IMMEDIATE")
        normalized = []
        total = 0.0
        currency = "FCFA"

        for index, raw in enumerate(items, start=1):
            if not isinstance(raw, dict):
                con.rollback()
                return {"ok": False, "message": f"Article #{index} invalide."}, 400
            try:
                pid = int(raw.get("id"))
                qty = int(raw.get("quantity", 1))
            except (TypeError, ValueError):
                con.rollback()
                return {"ok": False, "message": f"Article #{index} invalide."}, 400
            if pid <= 0 or qty < 1 or qty > MAX_QTY:
                con.rollback()
                return {"ok": False, "message": f"Quantité invalide pour l'article #{pid}."}, 400

            product = con.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
            if not product:
                con.rollback()
                return {"ok": False, "message": f"Le produit #{pid} n'existe plus."}, 404
            if not int(product["active"] or 0):
                con.rollback()
                return {"ok": False, "message": f"Le produit « {product['name']} » n'est plus disponible."}, 400

            variant = None
            variant_label = ""
            variant_id_raw = raw.get("variant_id")
            if variant_id_raw not in (None, "", 0, "0"):
                if not variants_exist:
                    con.rollback()
                    return {"ok": False, "message": "La variante demandée n'est plus disponible."}, 400
                try:
                    variant_id = int(variant_id_raw)
                except (TypeError, ValueError):
                    con.rollback()
                    return {"ok": False, "message": "Variante invalide."}, 400
                variant = con.execute(
                    """SELECT id,name,value,price_delta,stock,active FROM product_variants
                       WHERE id=? AND product_id=?""",
                    (variant_id, pid),
                ).fetchone()
                if not variant or not int(variant["active"] or 0):
                    con.rollback()
                    return {"ok": False, "message": "La variante demandée n'est plus disponible."}, 400
                variant_label = " — ".join(
                    x for x in (str(variant["name"] or "").strip(), str(variant["value"] or "").strip()) if x
                )

            unit = float(product["price"] or 0)
            if variant is not None:
                unit = max(0.0, unit + float(variant["price_delta"] or 0))
            subtotal = unit * qty
            if has_currency:
                currency = str(product["currency"] or "FCFA")

            ptype = str(product["product_type"] or "").lower() if has_type else ""
            pdf_file = str(product["pdf_file"] or "").strip() if has_pdf else ""
            is_digital = ptype in {"digital_pdf", "digital", "pdf"} or bool(pdf_file)

            stock = int(product["stock"] or 0) if "stock" in product.keys() else 0
            if not is_digital and stock > 0 and qty > stock:
                con.rollback()
                return {"ok": False, "message": f"Stock insuffisant pour « {product['name']} »."}, 400

            if variant is not None and variant["stock"] is not None and not is_digital:
                vst = int(variant["stock"] or 0)
                if vst > 0 and qty > vst:
                    con.rollback()
                    return {"ok": False, "message": f"Stock insuffisant pour « {product['name']} »."}, 400

            normalized.append({
                "id": int(product["id"]),
                "name": str(product["name"]),
                "price": unit,
                "quantity": qty,
                "subtotal": subtotal,
                "currency": currency,
                "variant": variant_label,
                "variant_id": int(variant["id"]) if variant else None,
                "is_digital": is_digital,
            })
            total += subtotal

        customer_row = _find_customer(con, phone)
        if customer_row:
            customer_id = int(customer_row["id"])
            con.execute(
                "UPDATE customers SET name=?,phone=?,email=?,address=?,city=? WHERE id=?",
                (name, phone, email, address, city, customer_id),
            )
        else:
            cur = con.execute(
                "INSERT INTO customers(name,phone,email,address,city) VALUES(?,?,?,?,?)",
                (name, phone, email, address, city),
            )
            customer_id = int(cur.lastrowid)

        cur = con.execute(
            """INSERT INTO orders(customer_id,total,payment_method,payment_status,delivery_status,notes,currency)
               VALUES(?,?,?,?,?,?,?)""",
            (customer_id, round(total, 2), payment_method, "pending", "pending", notes, currency),
        )
        order_id = int(cur.lastrowid)

        for item in normalized:
            con.execute(
                """INSERT INTO order_items(order_id,product_id,product_name,unit_price,quantity,subtotal,variant)
                   VALUES(?,?,?,?,?,?,?)""",
                (order_id, item["id"], item["name"], item["price"], item["quantity"], item["subtotal"], item["variant"]),
            )
            if not item["is_digital"]:
                row = con.execute("SELECT stock FROM products WHERE id=?", (item["id"],)).fetchone()
                if row and int(row["stock"] or 0) > 0:
                    con.execute("UPDATE products SET stock=MAX(stock-?,0) WHERE id=?", (item["quantity"], item["id"]))
                if item["variant_id"] and variants_exist:
                    row = con.execute("SELECT stock FROM product_variants WHERE id=?", (item["variant_id"],)).fetchone()
                    if row and int(row["stock"] or 0) > 0:
                        con.execute("UPDATE product_variants SET stock=MAX(stock-?,0) WHERE id=?", (item["quantity"], item["variant_id"]))

        con.commit()
        return {
            "ok": True,
            "order_id": order_id,
            "total": round(total, 2),
            "currency": currency,
            "payment_method": payment_method,
            "items": normalized,
            "message": "Commande enregistrée.",
        }, 200
    except sqlite3.IntegrityError:
        con.rollback()
        return {"ok": False, "message": "Impossible d'enregistrer la commande."}, 409
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()
