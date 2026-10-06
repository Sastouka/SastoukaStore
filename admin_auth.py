from pathlib import Path
# -*- coding: utf-8 -*-
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
import hashlib, hmac, os
import secrets
from dotenv import load_dotenv

SASTOUKASTORE_ICON_PATH_6_6 = Path(__file__).resolve().parent / "static" / "icons" / "sastoukastore-icon.png"
load_dotenv()

admin_auth = Blueprint('admin_auth', __name__)
# === SASTOUKASTORE ADMIN RESET 2026 ===
ENV_ADMIN_USERNAME = os.environ.get("SASTOUKASTORE_ADMIN_USER", "").strip()
ENV_ADMIN_SALT = os.environ.get("SASTOUKASTORE_ADMIN_SALT", "").strip()
ENV_ADMIN_PASSWORD_SHA256 = os.environ.get("CHARIOW_ADMIN_HASH", "").strip()
FALLBACK_ADMIN_USERNAMES = ['Admin', 'SastoukaStore']

ADMIN_USERNAME = ENV_ADMIN_USERNAME or "Admin"
ADMIN_SALT = ENV_ADMIN_SALT or ""
ADMIN_PASSWORD_SHA256 = ENV_ADMIN_PASSWORD_SHA256 or ""
# === FIN SASTOUKASTORE ADMIN RESET 2026 ===


def check_admin_password(password):
    if not ADMIN_SALT or not ADMIN_HASH:
        return False
    password = str(password or "")

    # Identifiants configures dans .env.
    if ENV_ADMIN_PASSWORD_SHA256 and ENV_ADMIN_SALT:
        value = hashlib.sha256(
            (ENV_ADMIN_SALT + password).encode("utf-8")
        ).hexdigest()
        if hmac.compare_digest(value, ENV_ADMIN_PASSWORD_SHA256):
            return True

    # Compte local de secours.
    fallback_value = hashlib.sha256(
        ("" + password).encode("utf-8")
    ).hexdigest()
    return hmac.compare_digest(fallback_value, "")


# === SASTOUKASTORE CSRF 1 ===
CSRF_SESSION_KEY = "_sastoukastore_csrf_token"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}

def get_csrf_token():
    token = session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        session[CSRF_SESSION_KEY] = token
    return token

@admin_auth.app_context_processor
def inject_csrf_token():
    return {"csrf_token": get_csrf_token}

# === FIN SASTOUKASTORE CSRF 1 ===

def protect_admin():
    path = request.path
    allowed = {'/admin/login', '/admin/deconnexion'}
    protected = path == '/admin' or path.startswith('/admin/') or path.startswith('/api/admin/')
    if protected and path not in allowed and not session.get('sastoukastore_admin'):
        if path.startswith('/api/'):
            return jsonify({'ok': False, 'error': 'Authentification administrateur requise'}), 401
        return redirect(url_for('admin_auth.login', next=request.full_path))

    # === SASTOUKASTORE CSRF VALIDATION 1 ===
    if (
        protected
        and path not in allowed
        and request.method not in SAFE_METHODS
        and session.get("sastoukastore_admin")
    ):
        expected = session.get(CSRF_SESSION_KEY, "")
        provided = (
            request.form.get("csrf_token", "")
            or request.headers.get("X-CSRF-Token", "")
        )
        if not expected or not provided or not hmac.compare_digest(
            expected, provided
        ):
            if path.startswith("/api/"):
                return jsonify({
                    "ok": False,
                    "error": "Jeton CSRF invalide ou manquant."
                }), 403
            return "Requête refusée : jeton CSRF invalide ou manquant.", 403
    # === FIN SASTOUKASTORE CSRF VALIDATION 1 ===


# === SASTOUKASTORE PATCH 2.2 : ESPACE ADMIN ===
def _safe_admin_next(value):
    value = (value or "").strip()
    if not value:
        return "/admin/dashboard"
    if not value.startswith("/") or value.startswith("//"):
        return "/admin/dashboard"
    if value.startswith("/admin/login"):
        return "/admin/dashboard"
    return value


@admin_auth.route("/espace-admin")
@admin_auth.route("/espace-admin/")
def espace_admin():
    next_url = _safe_admin_next(request.args.get("next", ""))
    if session.get("sastoukastore_admin"):
        return redirect(next_url)
    return redirect(url_for("admin_auth.login", next=next_url))


@admin_auth.route('/admin/login', methods=['GET', 'POST'])
def login():
    error = None
    next_url = request.values.get("next", "").strip()

    if session.get("sastoukastore_admin") and request.method == "GET":
        if not next_url or not next_url.startswith("/") or next_url.startswith("//"):
            next_url = "/admin/dashboard"
        return redirect(next_url)

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        env_username_ok = bool(ENV_ADMIN_USERNAME) and username == ENV_ADMIN_USERNAME
        fallback_username_ok = username in FALLBACK_ADMIN_USERNAMES

        if (env_username_ok or fallback_username_ok) and check_admin_password(password):
            session.clear()
            session.permanent = False
            session["sastoukastore_admin"] = True
            session["sastoukastore_admin_user"] = username

            if not next_url or not next_url.startswith("/") or next_url.startswith("//"):
                next_url = "/admin/dashboard"

            return redirect(next_url)

        error = "Identifiant ou mot de passe incorrect."

    return render_template(
        "admin_login.html",
        error=error,
        next=next_url,
        admin_username=ADMIN_USERNAME,
    )



@admin_auth.route('/admin/deconnexion', methods=['GET', 'POST'])
def logout():
    session.pop('sastoukastore_admin', None)
    session.pop('sastoukastore_admin_user', None)
    return redirect('/')
