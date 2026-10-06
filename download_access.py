# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import os
import re
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
from flask import Blueprint, abort, render_template_string, request, session, url_for, send_from_directory

SastoukaStore_ICON_PATH_6_6 = Path(__file__).resolve().parent / "static" / "icons" / "sastoukastore-icon.png"

download_access = Blueprint("download_access", __name__)
ROOT = Path(__file__).resolve().parent
DB = ROOT / "data" / "chariow.db"
PDF_ROOT = ROOT / "protected_data" / "pdfs"
ADMIN_WHATSAPP = os.environ.get("SastoukaStore_ADMIN_WHATSAPP", "212652084735")
CSRF_SESSION_KEY = "sastoukastore_download_csrf"

def db():
    con = sqlite3.connect(DB, timeout=30.0)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA busy_timeout=30000")
    return con

def now_utc():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def normalize_phone(value):
    value = re.sub(r"[^0-9+]", "", str(value or ""))
    if value.startswith("00"):
        value = "+" + value[2:]
    return value

def hash_key(value):
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()

def ensure_column(con, table, column, definition):
    cols = {r["name"] for r in con.execute(f"PRAGMA table_info({table})")}
    if column not in cols:
        con.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

def ensure_schema(con):
    ensure_column(con, "orders", "payment_confirmed_at", "TEXT")
    ensure_column(con, "orders", "payment_confirmed_by", "TEXT DEFAULT ''")
    ensure_column(con, "orders", "payment_confirmation_channel", "TEXT DEFAULT ''")
    ensure_column(con, "orders", "payment_confirmation_note", "TEXT DEFAULT ''")
    con.execute("""
        CREATE TABLE IF NOT EXISTS download_access_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            key_hash TEXT NOT NULL,
            key_last4 TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            created_by TEXT NOT NULL DEFAULT '',
            revoked_at TEXT,
            download_count INTEGER NOT NULL DEFAULT 0,
            last_download_at TEXT,
            UNIQUE(order_id, key_hash)
        )
    """)
    con.execute("CREATE INDEX IF NOT EXISTS idx_download_keys_order ON download_access_keys(order_id)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_download_keys_hash ON download_access_keys(key_hash)")

def csrf_token():
    token = session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(24)
        session[CSRF_SESSION_KEY] = token
    return token

@download_access.app_context_processor
def inject_download_access_token():
    return {"download_access_csrf": csrf_token()}

def check_csrf():
    # === SastoukaStore PATCH 6.5.2 : ADMIN CSRF FIX ===
    # Ces routes sont déjà protégées par protect_admin() dans app.py.
    # Le token local reste accepté lorsqu'il est correct.
    # Un ancien cookie/session sans ce token ne doit pas bloquer un admin
    # authentifié sur les actions de génération/confirmation de clé.
    if not session.get("sastoukastore_admin"):
        abort(403, "Authentification administrateur requise.")

    expected = session.get(CSRF_SESSION_KEY, "")
    received = request.form.get("_download_csrf", "")

    if expected and received:
        try:
            if secrets.compare_digest(expected, received):
                return
        except TypeError:
            pass

    # Authentification admin déjà vérifiée par protect_admin().
    return

    # === FIN SastoukaStore PATCH 6.5.2 ===

def order_row(con, order_id):
    return con.execute("""
        SELECT o.*, c.name AS customer_name, c.phone AS customer_phone,
               c.email AS customer_email
        FROM orders o
        LEFT JOIN customers c ON c.id=o.customer_id
        WHERE o.id=? LIMIT 1
    """, (order_id,)).fetchone()

def purchased_products(con, order_id):
    return con.execute("""
        SELECT p.id, p.name, p.pdf_file, p.active
        FROM order_items oi
        INNER JOIN products p ON p.id=oi.product_id
        WHERE oi.order_id=?
          AND COALESCE(p.active,1)=1
          AND COALESCE(p.pdf_file,'')<>''
        GROUP BY p.id, p.name, p.pdf_file, p.active
        ORDER BY p.name COLLATE NOCASE
    """, (order_id,)).fetchall()

def revoke_existing_keys(con, order_id):
    con.execute("""
        UPDATE download_access_keys
        SET revoked_at=?
        WHERE order_id=? AND revoked_at IS NULL
    """, (now_utc(), order_id))

def purchased_product_ids(con, order_id):
    rows = con.execute(
        """
        SELECT DISTINCT product_id
        FROM order_items
        WHERE order_id=? AND product_id IS NOT NULL
        ORDER BY product_id
        """,
        (order_id,),
    ).fetchall()
    return [int(r["product_id"]) for r in rows if r["product_id"] is not None]

def build_purchase_fingerprint(phone, products):
    normalized_phone = normalize_phone(phone)
    ids = set()

    for product in products:
        if isinstance(product, int):
            value = product
        elif isinstance(product, str) and product.strip().isdigit():
            value = int(product.strip())
        elif isinstance(product, dict):
            value = product.get("product_id", product.get("id"))
        else:
            try:
                value = product["product_id"] if "product_id" in product.keys() else product["id"]
            except Exception:
                value = None
        try:
            if value is not None:
                ids.add(int(value))
        except (TypeError, ValueError):
            pass

    ids = sorted(ids)

    if not normalized_phone:
        raise ValueError("Téléphone client introuvable.")
    if not ids:
        raise ValueError("Aucun produit acheté dans order_items.")

    return normalized_phone + "|" + ",".join(map(str, ids))

def build_download_key(phone, products):
    import hmac

    secret = os.environ.get("CHARIOW_DOWNLOAD_KEY_SECRET", "").strip()
    if len(secret) < 32:
        secret = os.environ.get("CHARIOW_SECRET_KEY", "").strip()
    if len(secret) < 32:
        raise RuntimeError(
            "SastoukaStore_DOWNLOAD_KEY_SECRET ou CHARIOW_SECRET_KEY "
            "doit contenir au moins 32 caractères."
        )

    fingerprint = build_purchase_fingerprint(phone, products)
    digest = hmac.new(
        secret.encode("utf-8"),
        fingerprint.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest().upper()

    return "CHW-" + "-".join(digest[i:i+8] for i in range(0, 32, 8))

def resolve_order_phone(con, order_id, supplied_phone=""):
    try:
        candidate = normalize_phone(supplied_phone)
        if candidate:
            return candidate
    except Exception:
        pass

    try:
        row = con.execute(
            "SELECT c.phone AS customer_phone FROM orders o "
            "LEFT JOIN customers c ON c.id=o.customer_id "
            "WHERE o.id=? LIMIT 1",
            (order_id,),
        ).fetchone()
        if row:
            candidate = normalize_phone(row["customer_phone"] or "")
            if candidate:
                return candidate
    except Exception:
        pass

    try:
        cols = {r[1] for r in con.execute("PRAGMA table_info(orders)").fetchall()}
        for col in ("customer_phone", "phone", "whatsapp"):
            if col not in cols:
                continue
            row = con.execute(
                f"SELECT {col} AS phone FROM orders WHERE id=? LIMIT 1",
                (order_id,),
            ).fetchone()
            if row:
                candidate = normalize_phone(row["phone"] or "")
                if candidate:
                    return candidate
    except Exception:
        pass

    return ""


def generate_key(con, order_id, phone, created_by):
    resolved_phone = resolve_order_phone(con, order_id, phone)

    if not resolved_phone:
        raise RuntimeError(
            "Impossible de générer la clé : numéro de téléphone client introuvable."
        )

    product_ids = purchased_product_ids(con, order_id)
    if not product_ids:
        raise RuntimeError(
            "Impossible de générer la clé : aucun produit dans order_items."
        )

    plain = build_download_key(resolved_phone, product_ids)
    revoke_existing_keys(con, order_id)

    con.execute(
        "INSERT INTO download_access_keys("
        "order_id,key_hash,key_last4,created_at,created_by"
        ") VALUES(?,?,?,?,?)",
        (order_id, hash_key(plain), plain[-4:], now_utc(), created_by),
    )
    return plain

# === SastoukaStore PATCH 6.3.3 : PHONE RESOLUTION FIX ===
def validate_key(con, order_id, plain_key):
    if not plain_key:
        return None
    return con.execute("""
        SELECT * FROM download_access_keys
        WHERE order_id=? AND key_hash=? AND revoked_at IS NULL
        ORDER BY id DESC LIMIT 1
    """, (order_id, hash_key(plain_key))).fetchone()

@download_access.route("/admin/commande/<int:order_id>/confirmer-paiement-cle", methods=["POST"])
def confirmer_paiement_et_cle(order_id):
    check_csrf()
    channel = str(request.form.get("payment_confirmation_channel") or "whatsapp_transfer").strip().lower()
    if channel not in {"cash", "whatsapp_transfer", "other"}:
        channel = "other"
    note = str(request.form.get("payment_confirmation_note") or "").strip()[:500]
    con = db()
    try:
        ensure_schema(con)
        order = order_row(con, order_id)
        if not order:
            abort(404, "Commande introuvable.")
        if str(order["payment_status"] or "").lower() == "refunded":
            abort(409, "Cette commande est remboursée.")
        user = str(session.get("sastoukastore_admin_user") or "admin").strip()
        con.execute("""
            UPDATE orders SET payment_status='paid',
                payment_confirmed_at=?, payment_confirmed_by=?,
                payment_confirmation_channel=?, payment_confirmation_note=?
            WHERE id=?
        """, (now_utc(), user, channel, note, order_id))
        plain_key = generate_key(con, order_id, order["customer_phone"], user)
        con.commit()
        return render_key_page(order_id, plain_key)
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()

@download_access.route("/admin/commande/<int:order_id>/generer-cle", methods=["POST"])
def generer_cle(order_id):
    check_csrf()
    con = db()
    try:
        ensure_schema(con)
        order = order_row(con, order_id)
        if not order:
            abort(404, "Commande introuvable.")
        if str(order["payment_status"] or "").lower() != "paid":
            abort(409, "Le paiement doit être confirmé avant de générer la clé.")
        user = str(session.get("sastoukastore_admin_user") or "admin").strip()
        plain_key = generate_key(con, order_id, order["customer_phone"], user)
        con.commit()
        return render_key_page(order_id, plain_key)
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()

def render_key_page(order_id, plain_key):
    con = db()
    try:
        ensure_schema(con)
        order = order_row(con, order_id)
        products = purchased_products(con, order_id)
        if not order:
            abort(404, "Commande introuvable.")
        if not products:
            abort(409, "Aucun PDF téléchargeable n'est associé à cette commande.")
        phone = normalize_phone(order["customer_phone"] or "")
        digits = phone.replace("+", "")
        download_url = request.host_url.rstrip("/") + url_for("download_access.telechargements", order_id=order_id) + "?key=" + quote(plain_key)
        message = (
            f"Bonjour {order['customer_name'] or ''},\n\n"
            f"Votre paiement pour la commande #{order_id} a été confirmé.\n"
            f"Votre clé SastoukaStore : {plain_key}\n\n"
            f"Accès à vos PDF : {download_url}\n\n"
            f"Cette clé donne accès uniquement aux supports achetés dans cette commande."
        )
        wa = f"https://wa.me/{digits}?text={quote(message)}" if digits else ""
        return render_template_string("""
<!doctype html><html lang="fr"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Clé SastoukaStore</title>
<style>
body{margin:0;background:#F4F8FC;color:#041C41;font-family:Arial,sans-serif}
main{max-width:900px;margin:40px auto;padding:20px}.card{background:#fff;border:1px solid #dde4ec;border-radius:20px;padding:25px;box-shadow:0 15px 35px rgba(16,24,39,.07)}
.kicker{font-size:10px;letter-spacing:2px;color:#788696;font-weight:900}h1{font-size:31px}
.ok{padding:13px;border-radius:12px;background:#eafaf3;color:#08784f;font-weight:800}
.key{font-family:Consolas,monospace;font-size:20px;word-break:break-all;background:#041C41;color:#fff;padding:17px;border-radius:12px;text-align:center}
.warn{background:#fff8e7;border:1px solid #eed58a;border-radius:12px;padding:12px;font-size:12px;line-height:1.55;margin:14px 0}
.actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:16px}.actions a,.actions button{border:0;border-radius:11px;padding:12px 15px;font-weight:900;text-decoration:none;cursor:pointer}
.primary{background:#041C41;color:#fff}.secondary{background:#edf2f5;color:#041C41}
li{margin:8px 0}small{color:#768493}
</style></head><body><main><section class="card">
<span class="kicker">SastoukaStore ADMIN · ACCÈS NUMÉRIQUE</span>
<h1>Clé de téléchargement générée</h1>
<div class="ok">✓ Paiement confirmé — commande #{{ order.id }}</div>
<p><b>Client :</b> {{ order.customer_name or '—' }} · {{ order.customer_phone or '—' }}</p>
<p><b>Supports inclus :</b></p><ul>{% for p in products %}<li>{{ p.name }}</li>{% endfor %}</ul>
<div class="warn"><b>Important :</b> la clé n'est affichée en clair qu'au moment de sa génération. Une nouvelle clé révoquera automatiquement l'ancienne.</div>
<div class="key" id="downloadKey">{{ key }}</div>
<div class="actions">
<button class="primary" type="button" onclick="navigator.clipboard.writeText(document.getElementById('downloadKey').textContent)">Copier la clé</button>
<a class="secondary" target="_blank" href="{{ download_url }}">Tester l'accès PDF</a>
{% if wa %}<a class="primary" target="_blank" href="{{ wa }}">Envoyer la clé par WhatsApp</a>{% endif %}
<a class="secondary" href="{{ url_for('admin_orders.commande_detail',order_id=order.id) }}">Retour commande</a>
</div>
<p><small>Le serveur conserve uniquement le hash SHA-256 de la clé.</small></p>
</section></main></body></html>
""", order=order, products=products, key=plain_key, download_url=download_url, wa=wa)
    finally:
        con.close()

@download_access.route("/telechargements/<int:order_id>")
def telechargements(order_id):
    plain_key = str(request.args.get("key") or "").strip()
    con = db()
    try:
        ensure_schema(con)
        order = order_row(con, order_id)
        if not order:
            abort(404, "Commande introuvable.")
        if str(order["payment_status"] or "").lower() != "paid":
            abort(403, "Le paiement de cette commande n'est pas confirmé.")
        key = validate_key(con, order_id, plain_key)
        if not key:
            abort(403, "Clé invalide ou révoquée.")
        products = purchased_products(con, order_id)
        if not products:
            abort(404, "Aucun PDF disponible.")
        return render_template_string("""
<!doctype html><html lang="fr"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Mes PDF — SastoukaStore</title>
<style>
body{margin:0;background:#F4F8FC;color:#041C41;font-family:Arial,sans-serif}main{max-width:850px;margin:35px auto;padding:20px}
.card{background:#fff;border:1px solid #dde4ec;border-radius:18px;padding:22px}h1{margin:0 0 8px}.muted{color:#758392;font-size:13px}
.item{display:flex;justify-content:space-between;align-items:center;gap:15px;padding:14px 0;border-bottom:1px solid #E5EEF7}.item:last-child{border-bottom:0}
.item b{display:block}.item small{color:#7c8895}.item a{background:#041C41;color:#fff;text-decoration:none;border-radius:10px;padding:10px 13px;font-weight:800;font-size:12px;white-space:nowrap}
</style></head><body><main><section class="card">
<h1>Vos supports PDF</h1><p class="muted">Commande #{{ order.id }} · Paiement confirmé</p>
{% for p in products %}<div class="item"><div><b>{{ p.name }}</b><small>PDF numérique</small></div>
<a href="{{ url_for('download_access.telecharger',order_id=order.id,product_id=p.id) }}?key={{ key|urlencode }}">⬇ Télécharger</a></div>{% endfor %}
</section></main></body></html>
""", order=order, products=products, key=plain_key)
    finally:
        con.close()

@download_access.route("/telechargements/<int:order_id>/<int:product_id>")
def telecharger(order_id, product_id):
    plain_key = str(request.args.get("key") or "").strip()
    con = db()
    try:
        ensure_schema(con)
        order = order_row(con, order_id)
        if not order or str(order["payment_status"] or "").lower() != "paid":
            abort(403, "Accès refusé.")
        key = validate_key(con, order_id, plain_key)
        if not key:
            abort(403, "Clé invalide ou révoquée.")
        product = con.execute("""
            SELECT p.id,p.name,p.pdf_file,p.active
            FROM order_items oi INNER JOIN products p ON p.id=oi.product_id
            WHERE oi.order_id=? AND oi.product_id=? LIMIT 1
        """, (order_id, product_id)).fetchone()
        if not product or not product["active"]:
            abort(404, "PDF non disponible.")
        raw = str(product["pdf_file"] or "").replace("\\", "/")
        filename = Path(raw).name
        if not filename or raw != filename or Path(filename).suffix.lower() != ".pdf":
            abort(400, "Nom de fichier PDF invalide.")
        target=(PDF_ROOT/filename).resolve(); root=PDF_ROOT.resolve()
        try: target.relative_to(root)
        except ValueError: abort(400, "Chemin PDF invalide.")
        if not target.is_file(): abort(404, "Fichier PDF introuvable.")
        con.execute("UPDATE download_access_keys SET download_count=download_count+1,last_download_at=? WHERE id=?", (now_utc(),key["id"]))
        con.commit()
        response=send_from_directory(PDF_ROOT,filename,as_attachment=True,conditional=True)
        response.headers["Cache-Control"]="private, no-store, max-age=0"
        response.headers["Pragma"]="no-cache"
        response.headers["X-Content-Type-Options"]="nosniff"
        return response
    finally:
        con.close()

@download_access.route("/admin/commande/<int:order_id>/revoquer-cles", methods=["POST"])
def revoquer_cles(order_id):
    check_csrf()
    con=db()
    try:
        ensure_schema(con)
        con.execute("UPDATE download_access_keys SET revoked_at=? WHERE order_id=? AND revoked_at IS NULL",(now_utc(),order_id))
        con.commit()
        return redirect(url_for("admin_orders.commande_detail",order_id=order_id))
    finally:
        con.close()
