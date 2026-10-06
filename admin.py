from flask import Blueprint, render_template, request, redirect, url_for, flash
from pathlib import Path
from werkzeug.utils import secure_filename
import sqlite3, re, uuid

admin = Blueprint("admin", __name__, url_prefix="/admin")
ROOT = Path(__file__).resolve().parent
DB = ROOT / "data" / "chariow.db"
UPLOAD = ROOT / "static" / "uploads" / "products"
ALLOWED = {"png","jpg","jpeg","webp","gif"}

def db():
    c=sqlite3.connect(DB, timeout=15.0); c.row_factory=sqlite3.Row; return c

def slugify(v):
    return re.sub(r"[^a-z0-9]+","-",v.lower().strip()).strip("-") or "produit"

def unique_slug(c,name,pid=None):
    base=slugify(name); s=base; n=2
    while c.execute("SELECT id FROM products WHERE slug=? AND (? IS NULL OR id<>?)",(s,pid,pid)).fetchone():
        s=f"{base}-{n}"; n+=1
    return s

def unique_cat(c,name):
    base=slugify(name); s=base; n=2
    while c.execute("SELECT id FROM categories WHERE slug=?",(s,)).fetchone():
        s=f"{base}-{n}"; n+=1
    return s

def save_image(f):
    if not f or not f.filename: return ""
    ext=f.filename.rsplit(".",1)[-1].lower()
    if ext not in ALLOWED: return ""
    UPLOAD.mkdir(parents=True,exist_ok=True)
    fn=secure_filename(uuid.uuid4().hex+"."+ext)
    f.save(UPLOAD/fn)
    return "/static/uploads/products/"+fn

@admin.route("/")
def dashboard():
    c=db()
    products=c.execute("SELECT p.*,c.name category_name FROM products p LEFT JOIN categories c ON c.id=p.category_id ORDER BY p.id DESC").fetchall()
    categories=c.execute("SELECT * FROM categories ORDER BY name").fetchall()
    stats={"products":c.execute("SELECT COUNT(*) FROM products").fetchone()[0],
           "active":c.execute("SELECT COUNT(*) FROM products WHERE active=1").fetchone()[0],
           "stock":c.execute("SELECT COALESCE(SUM(stock),0) FROM products").fetchone()[0],
           "categories":len(categories)}
    c.close()
    return render_template("premium_home.html",products=products,categories=categories,stats=stats)

@admin.post("/category/add")
def category_add():
    name=request.form.get("name","").strip(); c=db()
    if not name: flash("Nom de catégorie obligatoire.","error")
    else:
        try:
            c.execute("INSERT INTO categories(name,slug) VALUES(?,?)",(name,unique_cat(c,name)))
            c.commit(); flash("Catégorie ajoutée.","success")
        except sqlite3.IntegrityError: flash("Cette catégorie existe déjà.","error")
    c.close(); return redirect(url_for("admin.dashboard"))

@admin.post("/category/delete/<int:cid>")
def category_delete(cid):
    c=db(); used=c.execute("SELECT COUNT(*) FROM products WHERE category_id=?",(cid,)).fetchone()[0]
    if used: flash("Impossible : cette catégorie contient des produits.","error")
    else: c.execute("DELETE FROM categories WHERE id=?",(cid,)); c.commit(); flash("Catégorie supprimée.","success")
    c.close(); return redirect(url_for("admin.dashboard"))

@admin.post("/product/add")
def product_add():
    name=request.form.get("name","").strip(); desc=request.form.get("description","").strip()
    cat=request.form.get("category_id") or None
    try: price=float(request.form.get("price","0").replace(",",".")); stock=int(request.form.get("stock","0"))
    except ValueError: flash("Prix ou stock invalide.","error"); return redirect(url_for("admin.dashboard"))
    if not name or price<0 or stock<0: flash("Vérifiez les données.","error"); return redirect(url_for("admin.dashboard"))
    c=db(); image=save_image(request.files.get("image"))
    c.execute("INSERT INTO products(category_id,name,slug,description,price,image,stock) VALUES(?,?,?,?,?,?,?)",(cat,name,unique_slug(c,name),desc,price,image,stock))
    c.commit(); c.close(); flash("Produit ajouté.","success"); return redirect(url_for("admin.dashboard"))

@admin.post("/product/toggle/<int:pid>")
def toggle(pid):
    c=db(); c.execute("UPDATE products SET active=CASE active WHEN 1 THEN 0 ELSE 1 END WHERE id=?",(pid,)); c.commit(); c.close()
    return redirect(url_for("admin.dashboard"))

@admin.post("/product/delete/<int:pid>")
def delete(pid):
    c=db(); c.execute("DELETE FROM products WHERE id=?",(pid,)); c.commit(); c.close()
    flash("Produit supprimé.","success"); return redirect(url_for("admin.dashboard"))

@admin.route("/product/edit/<int:pid>",methods=["GET","POST"])
def edit(pid):
    c=db(); p=c.execute("SELECT * FROM products WHERE id=?",(pid,)).fetchone(); cats=c.execute("SELECT * FROM categories ORDER BY name").fetchall()
    if not p: c.close(); return "Produit introuvable",404
    if request.method=="POST":
        name=request.form.get("name","").strip(); desc=request.form.get("description","").strip(); cat=request.form.get("category_id") or None
        try: price=float(request.form.get("price","0").replace(",",".")); stock=int(request.form.get("stock","0"))
        except ValueError: c.close(); flash("Prix ou stock invalide.","error"); return redirect(url_for("admin.edit",pid=pid))
        image=save_image(request.files.get("image")) or p["image"] or ""
        c.execute("UPDATE products SET category_id=?,name=?,slug=?,description=?,price=?,image=?,stock=? WHERE id=?",(cat,name,unique_slug(c,name,pid),desc,price,image,stock,pid))
        c.commit(); c.close(); flash("Produit modifié.","success"); return redirect(url_for("admin.dashboard"))
    c.close(); return render_template("admin_product_edit.html",product=p,categories=cats)
