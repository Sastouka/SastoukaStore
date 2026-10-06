# -*- coding: utf-8 -*-
from flask import Blueprint, render_template, request, redirect, url_for
from pathlib import Path
import sqlite3
import secrets
import re
import unicodedata
from werkzeug.utils import secure_filename

SastoukaStore_ICON_PATH_6_6 = Path(__file__).resolve().parent / "static" / "icons" / "sastoukastore-icon.png"

digital_admin = Blueprint("digital_admin", __name__)

ROOT = Path(__file__).resolve().parent
DB = ROOT / "data" / "chariow.db"
UPLOAD_ROOT = ROOT / "static" / "uploads" / "products"
COVER_ROOT = UPLOAD_ROOT / "covers"
PDF_ROOT = ROOT / "protected_data" / "pdfs"

ALLOWED_COVERS = {"png", "jpg", "jpeg", "webp"}
ALLOWED_PDFS = {"pdf"}

def db():
    con = sqlite3.connect(DB, timeout=15.0)
    con.row_factory = sqlite3.Row
    return con

def slugify(value):
    value = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value or "produit"

def unique_slug(con, base, current_id=None):
    base = slugify(base)
    candidate = base
    n = 2
    while True:
        if current_id is None:
            row = con.execute("SELECT 1 FROM products WHERE slug=? LIMIT 1", (candidate,)).fetchone()
        else:
            row = con.execute(
                "SELECT 1 FROM products WHERE slug=? AND id<>? LIMIT 1",
                (candidate, current_id)
            ).fetchone()
        if not row:
            return candidate
        candidate = f"{base}-{n}"
        n += 1

def ext(name):
    return Path(name or "").suffix.lower().lstrip(".")

def save_upload(file_obj, directory, allowed):
    if not file_obj or not file_obj.filename:
        return ""
    extension = ext(file_obj.filename)
    if extension not in allowed:
        raise ValueError("Format de fichier non autorisé.")
    safe = secure_filename(file_obj.filename)
    if not safe:
        raise ValueError("Nom de fichier invalide.")
    stem = Path(safe).stem[:80]
    final_name = f"{stem}_{secrets.token_hex(5)}.{extension}"
    directory.mkdir(parents=True, exist_ok=True)
    file_obj.save(directory / final_name)
    try:
        return str((directory / final_name).relative_to(ROOT / "static")).replace("\\", "/")
    except ValueError:
        return final_name

def form_values(form, files, old=None):
    name = form.get("name", "").strip()
    try:
        price = float(form.get("price") or 0)
    except (TypeError, ValueError):
        price = 0

    currency = form.get("currency", "FCFA").strip() or "FCFA"
    level = form.get("level", "").strip()
    subject = form.get("subject", "").strip()
    short_description = form.get("short_description", "").strip()
    description = form.get("description", "").strip()
    featured = 1 if form.get("featured") else 0
    active = 1 if form.get("active") else 0

    cover = files.get("cover_image")
    pdf = files.get("pdf_file")

    cover_path = (
        save_upload(cover, COVER_ROOT, ALLOWED_COVERS)
        if cover and cover.filename
        else (old["image"] if old and old["image"] else "")
    )

    pdf_path = (
        save_upload(pdf, PDF_ROOT, ALLOWED_PDFS)
        if pdf and pdf.filename
        else (old["pdf_file"] if old and old["pdf_file"] else "")
    )

    return {
        "name": name,
        "price": price,
        "currency": currency,
        "level": level,
        "subject": subject,
        "short_description": short_description,
        "description": description,
        "featured": featured,
        "active": active,
        "product_type": "digital_pdf",
        "image": cover_path,
        "pdf_file": pdf_path,
    }

def categories_for_form(con):
    return con.execute(
        "SELECT * FROM categories ORDER BY name COLLATE NOCASE"
    ).fetchall()

@digital_admin.route("/admin/produit/nouveau", methods=["GET", "POST"])
def nouveau():
    con = db()
    categories = categories_for_form(con)

    if request.method == "POST":
        try:
            data = form_values(request.form, request.files)
        except ValueError as exc:
            con.close()
            return str(exc), 400

        if not data["name"]:
            con.close()
            return "Le titre du support est obligatoire.", 400
        if data["price"] < 0:
            con.close()
            return "Le prix ne peut pas être négatif.", 400
        if not data["pdf_file"]:
            con.close()
            return "Le fichier PDF éducatif est obligatoire.", 400

        slug = unique_slug(con, data["name"])

        con.execute(
            '''
            INSERT INTO products
            (name, slug, price, stock, active, description, image, category_id,
             product_type, pdf_file, currency, level, subject, short_description, featured)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ''',
            (
                data["name"], slug, data["price"], 999999, data["active"],
                data["description"], data["image"],
                request.form.get("category_id") or None,
                data["product_type"], data["pdf_file"], data["currency"],
                data["level"], data["subject"], data["short_description"],
                data["featured"]
            )
        )
        con.commit()
        con.close()
        return redirect(url_for("admin_catalog.produits"))

    con.close()
    return render_template(
        "admin_product_form_digital.html",
        product=None,
        categories=categories
    )

@digital_admin.route("/admin/produit/<int:product_id>/modifier", methods=["GET", "POST"])
def modifier(product_id):
    con = db()
    product = con.execute(
        "SELECT * FROM products WHERE id=?",
        (product_id,)
    ).fetchone()
    categories = categories_for_form(con)

    if not product:
        con.close()
        return "Produit introuvable", 404

    if request.method == "POST":
        try:
            data = form_values(request.form, request.files, product)
        except ValueError as exc:
            con.close()
            return str(exc), 400

        if not data["name"]:
            con.close()
            return "Le titre du support est obligatoire.", 400
        if not data["pdf_file"]:
            con.close()
            return "Le fichier PDF éducatif est obligatoire.", 400

        slug = unique_slug(con, data["name"], current_id=product_id)

        con.execute(
            '''
            UPDATE products
            SET name=?, slug=?, price=?, active=?, description=?, image=?, category_id=?,
                product_type=?, pdf_file=?, currency=?, level=?, subject=?,
                short_description=?, featured=?
            WHERE id=?
            ''',
            (
                data["name"], slug, data["price"], data["active"],
                data["description"], data["image"],
                request.form.get("category_id") or None,
                data["product_type"], data["pdf_file"], data["currency"],
                data["level"], data["subject"], data["short_description"],
                data["featured"], product_id
            )
        )
        con.commit()
        con.close()
        return redirect(url_for("admin_catalog.produits"))

    con.close()
    return render_template(
        "admin_product_form_digital.html",
        product=product,
        categories=categories
    )
