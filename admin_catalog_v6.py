from flask import Blueprint, render_template, request, redirect, url_for
import sqlite3
from pathlib import Path

admin_catalog_v6 = Blueprint("admin_catalog_v6", __name__)
DB = Path(__file__).resolve().parent / "data" / "chariow.db"

def db():
    c = sqlite3.connect(DB, timeout=15.0)
    c.row_factory = sqlite3.Row
    return c

@admin_catalog_v6.route("/admin/categories")
def categories():
    con = db()
    cats = con.execute("""
        SELECT c.*, COUNT(p.id) AS products_count
        FROM categories c LEFT JOIN products p ON p.category_id=c.id
        GROUP BY c.id ORDER BY c.name COLLATE NOCASE
    """).fetchall()
    con.close()
    return render_template("admin_categories.html", categories=cats)

@admin_catalog_v6.route("/admin/categories/nouvelle", methods=["GET","POST"])
def nouvelle_categorie():
    if request.method == "POST":
        name = request.form.get("name","").strip()
        if not name:
            return "Nom de catégorie obligatoire", 400
        con = db()
        try:
            con.execute("INSERT INTO categories(name) VALUES(?)", (name,))
            con.commit()
        except sqlite3.IntegrityError:
            con.close()
            return "Cette catégorie existe déjà", 400
        con.close()
        return redirect(url_for("admin_catalog_v6.categories"))
    return render_template("admin_category_form.html", category=None)

@admin_catalog_v6.route("/admin/categories/<int:category_id>/modifier", methods=["GET","POST"])
def modifier_categorie(category_id):
    con = db()
    cat = con.execute("SELECT * FROM categories WHERE id=?", (category_id,)).fetchone()
    if not cat:
        con.close()
        return "Catégorie introuvable", 404
    if request.method == "POST":
        name = request.form.get("name","").strip()
        if not name:
            con.close()
            return "Nom de catégorie obligatoire", 400
        con.execute("UPDATE categories SET name=? WHERE id=?", (name, category_id))
        con.commit()
        con.close()
        return redirect(url_for("admin_catalog_v6.categories"))
    con.close()
    return render_template("admin_category_form.html", category=cat)

@admin_catalog_v6.route("/admin/categories/<int:category_id>/supprimer", methods=["POST"])
def supprimer_categorie(category_id):
    con = db()
    n = con.execute("SELECT COUNT(*) FROM products WHERE category_id=?", (category_id,)).fetchone()[0]
    if n:
        con.close()
        return "Impossible de supprimer une catégorie contenant des produits", 400
    con.execute("DELETE FROM categories WHERE id=?", (category_id,))
    con.commit()
    con.close()
    return redirect(url_for("admin_catalog_v6.categories"))

@admin_catalog_v6.route("/admin/produit/<int:product_id>/variantes")
def variantes(product_id):
    con = db()
    product = con.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
    if not product:
        con.close()
        return "Produit introuvable", 404
    variants = con.execute("""
        SELECT * FROM product_variants
        WHERE product_id=? ORDER BY id
    """, (product_id,)).fetchall()
    con.close()
    return render_template("admin_variants.html", product=product, variants=variants)

@admin_catalog_v6.route("/admin/produit/<int:product_id>/variante/nouvelle", methods=["POST"])
def nouvelle_variante(product_id):
    name = request.form.get("name","").strip()
    value = request.form.get("value","").strip()
    sku = request.form.get("sku","").strip()
    price_delta = float(request.form.get("price_delta") or 0)
    stock = max(0, int(request.form.get("stock") or 0))
    active = 1 if request.form.get("active") else 0
    if not name or not value:
        return "Nom et valeur de variante obligatoires", 400
    con = db()
    con.execute("""
        INSERT INTO product_variants(product_id,name,value,sku,price_delta,stock,active)
        VALUES(?,?,?,?,?,?,?)
    """, (product_id,name,value,sku,price_delta,stock,active))
    con.commit()
    con.close()
    return redirect(url_for("admin_catalog_v6.variantes", product_id=product_id))

@admin_catalog_v6.route("/admin/variante/<int:variant_id>/modifier", methods=["POST"])
def modifier_variante(variant_id):
    name=request.form.get("name","").strip()
    value=request.form.get("value","").strip()
    sku=request.form.get("sku","").strip()
    price_delta=float(request.form.get("price_delta") or 0)
    stock=max(0,int(request.form.get("stock") or 0))
    active=1 if request.form.get("active") else 0
    con=db()
    row=con.execute("SELECT product_id FROM product_variants WHERE id=?", (variant_id,)).fetchone()
    if not row:
        con.close()
        return "Variante introuvable",404
    con.execute("""
        UPDATE product_variants
        SET name=?,value=?,sku=?,price_delta=?,stock=?,active=?
        WHERE id=?
    """,(name,value,sku,price_delta,stock,active,variant_id))
    con.commit()
    con.close()
    return redirect(url_for("admin_catalog_v6.variantes", product_id=row["product_id"]))

@admin_catalog_v6.route("/admin/variante/<int:variant_id>/supprimer", methods=["POST"])
def supprimer_variante(variant_id):
    con=db()
    row=con.execute("SELECT product_id FROM product_variants WHERE id=?", (variant_id,)).fetchone()
    if row:
        con.execute("DELETE FROM product_variants WHERE id=?", (variant_id,))
        con.commit()
        pid=row["product_id"]
    else:
        pid=0
    con.close()
    if pid:
        return redirect(url_for("admin_catalog_v6.variantes", product_id=pid))
    return redirect(url_for("admin_catalog_v6.produits_fallback"))

@admin_catalog_v6.route("/admin/produits")
def produits_fallback():
    con=db()
    products=con.execute("""
        SELECT p.*,c.name category_name FROM products p
        LEFT JOIN categories c ON c.id=p.category_id ORDER BY p.id DESC
    """).fetchall()
    con.close()
    return render_template("admin_products.html",products=products,categories=[],q="")

@admin_catalog_v6.route("/api/categories")
def api_categories():
    con=db()
    rows=con.execute("SELECT id,name FROM categories ORDER BY name COLLATE NOCASE").fetchall()
    con.close()
    return {"categories":[dict(r) for r in rows]}

@admin_catalog_v6.route("/api/produit/<int:product_id>/variantes")
def api_variantes(product_id):
    con=db()
    rows=con.execute("""
        SELECT id,name,value,sku,price_delta,stock
        FROM product_variants
        WHERE product_id=? AND active=1 ORDER BY id
    """,(product_id,)).fetchall()
    con.close()
    return {"variants":[dict(r) for r in rows]}
