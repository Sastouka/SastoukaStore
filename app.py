import os
from dotenv import load_dotenv
load_dotenv()
from flask import Flask, render_template, jsonify, send_from_directory, request, g
import uuid
from pathlib import Path
import sqlite3
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "chariow.db"

app = Flask(__name__)
# === CHARIOW PATCH 6.3 : CART + DOWNLOAD KEY ===
from download_access import download_access
app.register_blueprint(download_access)
# === FIN CHARIOW PATCH 6.3 ===


# === CHARIOW PATCH 6 : DB MIGRATIONS ===
# Exécution des migrations SQLite avant les routes.
# Ce module utilise uniquement sqlite3 et n'a aucune dépendance Flask.
from db_migrations import run_migrations as _chariow_run_migrations

CHARIOW_ICON_PATH_6_6 = Path(__file__).resolve().parent / "static" / "icons" / "chariow-icon.png"
try:
    _chariow_run_migrations(DB_PATH)
except Exception as _migration_error:
    raise RuntimeError(
        f"CHARIOW : échec des migrations SQLite : {_migration_error}"
    ) from _migration_error
# === FIN CHARIOW PATCH 6 ===

# === CHARIOW PATCH 5 : PAYMENT LAYER ===
# Le blueprint paiement reste séparé du moteur de commande.
try:
    from payments import payments as _chariow_payments
    app.register_blueprint(_chariow_payments)
except Exception:
    # Le serveur peut démarrer même si le module paiement est temporairement
    # indisponible ; les autres fonctions CHARIOW ne sont pas bloquées.
    pass


# === CHARIOW SECURITY PATCH 1 ===
CHARIOW_SECRET_KEY = os.environ.get("CHARIOW_SECRET_KEY", "").strip()
if not CHARIOW_SECRET_KEY:
    raise RuntimeError(
        "CHARIOW_SECRET_KEY est obligatoire. "
        "Ajoutez-le dans .env ou dans les variables d'environnement."
    )

app.config.update(
    SECRET_KEY=CHARIOW_SECRET_KEY,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get(
        "CHARIOW_SESSION_COOKIE_SECURE", "0"
    ).strip() == "1",
    PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
    MAX_CONTENT_LENGTH=int(
        os.environ.get("CHARIOW_MAX_CONTENT_LENGTH", str(25 * 1024 * 1024))
    ),
)
# === FIN CHARIOW SECURITY PATCH 1 ===


# === CHARIOW SECURITY HEADERS PATCH 1 ===
@app.after_request
def _chariow_security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault(
        "Referrer-Policy", "strict-origin-when-cross-origin"
    )
    response.headers.setdefault(
        "Permissions-Policy",
        "camera=(), microphone=(), geolocation=()"
    )
    return response
# === FIN CHARIOW SECURITY HEADERS PATCH 1 ===

# === CHARIOW PATCH 17.2 HOMEPAGE FORCEE ===
@app.before_request
def _chariow_force_premium_home():
    if request.path != "/":
        return None

    db_path = Path(__file__).resolve().parent / "data" / "chariow.db"
    conn = None
    try:
        conn = sqlite3.connect(db_path, timeout=15.0)
        conn.row_factory = sqlite3.Row

        try:
            categories = conn.execute(
                "SELECT id, name FROM categories ORDER BY name COLLATE NOCASE"
            ).fetchall()
        except Exception:
            categories = []

        cols = {r[1] for r in conn.execute("PRAGMA table_info(products)").fetchall()}
        base_cols = ["id", "name", "price", "active", "description", "image", "category_id"]
        optional_cols = ["product_type", "pdf_file", "currency", "level", "subject", "short_description", "featured"]
        select_cols = [c for c in base_cols + optional_cols if c in cols]

        if "id" in cols and "name" in cols:
            products = conn.execute(
                "SELECT " + ",".join(select_cols) +
                " FROM products WHERE COALESCE(active,1)=1 ORDER BY id DESC"
            ).fetchall()
        else:
            products = []

        return render_template(
            "premium_home.html",
            products=products,
            categories=categories
        )
    except Exception as exc:
        print("[WARN] Homepage premium :", exc)
        return None
    finally:
        if conn is not None:
            conn.close()
# === FIN CHARIOW PATCH 17.2 ===

# === CHARIOW PATCH 15 : COMMANDES DIGITALES ===
from digital_orders import digital_orders
app.register_blueprint(digital_orders)
# === FIN PATCH 15 ===

# === CHARIOW PATCH 10 : PRODUITS NUMERIQUES ===
from digital_admin import digital_admin
app.register_blueprint(digital_admin)
# === FIN PATCH 10 ===

# === CHARIOW PATCH 9 : AUTH ADMIN PAR 7 CLICS ===
from admin_auth import admin_auth, protect_admin
app.register_blueprint(admin_auth)
app.before_request(protect_admin)

# === FIN PATCH 9 ===

from customer_tracking import customer_tracking
app.register_blueprint(customer_tracking)

from admin_dashboard import admin_dashboard
app.register_blueprint(admin_dashboard)

from admin_catalog_v6 import admin_catalog_v6
app.register_blueprint(admin_catalog_v6)

from admin_catalog import admin_catalog
app.register_blueprint(admin_catalog)

from admin_orders import admin_orders
app.register_blueprint(admin_orders)

from shop import shop
app.register_blueprint(shop)

from admin import admin
app.register_blueprint(admin)

def get_db():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=15.0)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('PRAGMA journal_mode=WAL;')
    conn.execute('PRAGMA synchronous=NORMAL;')
    conn.executescript(
        "CREATE TABLE IF NOT EXISTS settings ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "shop_name TEXT NOT NULL DEFAULT 'CHARIOW',"
        "currency TEXT NOT NULL DEFAULT 'FCFA',"
        "whatsapp TEXT DEFAULT '',"
        "created_at TEXT DEFAULT CURRENT_TIMESTAMP);"
        "CREATE TABLE IF NOT EXISTS categories ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "name TEXT NOT NULL,"
        "slug TEXT UNIQUE NOT NULL,"
        "active INTEGER NOT NULL DEFAULT 1);"
        "CREATE TABLE IF NOT EXISTS products ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "category_id INTEGER,"
        "name TEXT NOT NULL,"
        "slug TEXT UNIQUE NOT NULL,"
        "description TEXT DEFAULT '',"
        "price REAL NOT NULL DEFAULT 0,"
        "image TEXT DEFAULT '',"
        "stock INTEGER NOT NULL DEFAULT 0,"
        "active INTEGER NOT NULL DEFAULT 1,"
        "created_at TEXT DEFAULT CURRENT_TIMESTAMP,"
        "FOREIGN KEY(category_id) REFERENCES categories(id));"
        "CREATE TABLE IF NOT EXISTS customers ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "name TEXT NOT NULL,"
        "phone TEXT NOT NULL,"
        "email TEXT DEFAULT '',"
        "address TEXT DEFAULT '',"
        "city TEXT DEFAULT '',"
        "created_at TEXT DEFAULT CURRENT_TIMESTAMP);"
        "CREATE TABLE IF NOT EXISTS orders ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "customer_id INTEGER,"
        "total REAL NOT NULL DEFAULT 0,"
        "payment_method TEXT DEFAULT 'cash_delivery',"
        "payment_status TEXT DEFAULT 'pending',"
        "delivery_status TEXT DEFAULT 'pending',"
        "notes TEXT DEFAULT '',"
        "created_at TEXT DEFAULT CURRENT_TIMESTAMP,"
        "FOREIGN KEY(customer_id) REFERENCES customers(id));"
    )
    if conn.execute("SELECT COUNT(*) FROM settings").fetchone()[0] == 0:
        conn.execute(
            "INSERT INTO settings (shop_name, currency) VALUES (?, ?)",
            ("CHARIOW", "FCFA")
        )
    conn.commit()
    conn.close()


# === SASTOUKASTORE PATCH : COMPTE FANTÔME (SHADOW ACCOUNT) ===
@app.before_request
def _track_visitor():
    # Ignorer les fichiers statiques et l'espace admin pour ne pas polluer la base
    if request.path.startswith('/static') or request.path.startswith('/admin') or request.path.startswith('/api/health'):
        return None

    visitor_id = request.cookies.get('sastoukastore_visitor_id')
    
    if not visitor_id:
        # Création d'un identifiant unique (UUID)
        visitor_id = "vis_" + uuid.uuid4().hex
        
        # Enregistrement du compte invité en arrière-plan
        try:
            con = get_db()
            con.execute(
                "INSERT INTO customers (name, phone, email, address, city, visitor_id) VALUES (?, ?, ?, ?, ?, ?)",
                ("Visiteur Anonyme", "Non renseigné", "", "", "", visitor_id)
            )
            con.commit()
            con.close()
        except Exception as e:
            print("[Shadow Account] Erreur de création :", e)
            
        g.visitor_id = visitor_id
        g.is_new_visitor = True
    else:
        g.visitor_id = visitor_id
        g.is_new_visitor = False

@app.after_request
def _set_visitor_cookie(response):
    # Si c'est un nouveau visiteur, on lui attribue le cookie pour 1 an
    if getattr(g, 'is_new_visitor', False):
        response.set_cookie(
            'sastoukastore_visitor_id', 
            g.visitor_id, 
            max_age=60 * 60 * 24 * 365, # 1 an
            httponly=True,              # Empêche la lecture par Javascript (Sécurité)
            samesite='Lax'
        )
    return response
# === FIN SASTOUKASTORE PATCH ===


@app.route("/")
def home_premium():
    db_path = Path(__file__).resolve().parent / 'data' / 'chariow.db'
    conn = sqlite3.connect(db_path, timeout=15.0)
    conn.row_factory = sqlite3.Row
    categories = conn.execute('SELECT id, name FROM categories ORDER BY name COLLATE NOCASE').fetchall()
    cols = {row[1] for row in conn.execute('PRAGMA table_info(products)').fetchall()}
    select_cols = ['id','name','price','active','description','image','category_id']
    for col in ['product_type','pdf_file','currency','level','subject','short_description','featured']:
        if col in cols:
            select_cols.append(col)
    products = conn.execute(
        'SELECT ' + ','.join(select_cols) + ' FROM products WHERE COALESCE(active,1)=1 ORDER BY id DESC'
    ).fetchall()
    conn.close()
    return render_template('premium_home.html', products=products, categories=categories)
@app.route("/api/health")
def health():
    return jsonify({"application": "CHARIOW", "status": "ok", "pwa": True})


@app.route("/sw.js")
def chariow_service_worker():
    return send_from_directory(app.static_folder, "sw.js", mimetype="application/javascript")

import webbrowser
import threading
import os

def open_browser():
    webbrowser.open("http://127.0.0.1:5000")

if __name__ == "__main__":
    init_db()
    print("CHARIOW PWA : http://127.0.0.1:5000")
    
    # Empêche l'ouverture en double à cause du mode debug (reloader)
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        threading.Timer(1.25, open_browser).start()
        
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=os.environ.get("CHARIOW_DEBUG", "0") == "1")
