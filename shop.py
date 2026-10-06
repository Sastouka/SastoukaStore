from flask import Blueprint, render_template, request, jsonify, send_file
from pathlib import Path
from io import BytesIO
import sqlite3

from phone_utils import normalize_phone, validate_phone
from order_engine_v3 import process_order
shop = Blueprint("shop", __name__)
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "chariow.db"

def get_db():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=15.0)
    conn.row_factory = sqlite3.Row
    return conn

def money(value):
    try:
        return f"{float(value):,.2f}".replace(",", " ")
    except Exception:
        return "0.00"

@shop.app_template_filter("money")
def money_filter(value):
    return money(value)

@shop.route("/produit/<int:product_id>")
def product_detail(product_id):
    conn = get_db()
    product = conn.execute("""
        SELECT p.*, c.name AS category_name
        FROM products p LEFT JOIN categories c ON c.id=p.category_id
        WHERE p.id=? AND p.active=1
    """, (product_id,)).fetchone()
    related = conn.execute("""
        SELECT p.*, c.name AS category_name
        FROM products p LEFT JOIN categories c ON c.id=p.category_id
        WHERE p.active=1 AND p.id<>?
        ORDER BY p.id DESC LIMIT 4
    """, (product_id,)).fetchall() if product else []
    conn.close()
    _variant_conn = sqlite3.connect(Path(__file__).resolve().parent / "data" / "chariow.db")
    _variant_conn.row_factory = sqlite3.Row
    variants = _variant_conn.execute(
        "SELECT * FROM product_variants WHERE product_id=? AND active=1 ORDER BY id",
        (product_id,)
    ).fetchall()
    _variant_conn.close()
    if not product:
        return "Produit introuvable", 404
    
    return render_template("product_detail.html", product=product, related=related, variants=variants)

@shop.route("/apercu-pdf/<int:product_id>")
def pdf_preview(product_id):
    # Rend une des dix premières pages du PDF sous forme d'image filigranée.
    try:
        page_num = int(request.args.get("page", "1"))
    except (TypeError, ValueError):
        page_num = 1
    page_num = max(1, min(page_num, 10))

    conn = get_db()
    row = conn.execute(
        "SELECT id, name, pdf_file, active FROM products WHERE id=? AND active=1 LIMIT 1",
        (product_id,)
    ).fetchone()
    conn.close()

    if not row or not row["pdf_file"]:
        return "Aperçu indisponible.", 404

    filename = Path(str(row["pdf_file"]).replace("\\", "/")).name
    if not filename or Path(filename).suffix.lower() != ".pdf":
        return "Aperçu indisponible.", 400

    pdf_root = (BASE_DIR / "protected_data" / "pdfs").resolve()
    pdf_path = (pdf_root / filename).resolve()

    try:
        pdf_path.relative_to(pdf_root)
    except ValueError:
        return "Aperçu indisponible.", 400

    if not pdf_path.is_file():
        return "Aperçu indisponible.", 404

    try:
        import fitz
    except ImportError:
        return "Aperçu PDF indisponible : installez PyMuPDF.", 503

    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return "Aperçu PDF indisponible : installez Pillow.", 503

    try:
        doc = fitz.open(pdf_path)
        try:
            if page_num > doc.page_count:
                return "Page inexistante.", 404

            pdf_page = doc.load_page(page_num - 1)
            pix = pdf_page.get_pixmap(matrix=fitz.Matrix(1.35, 1.35), alpha=False)
            image = Image.open(BytesIO(pix.tobytes("png"))).convert("RGBA")

            overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)
            font = None
            font_candidates = [
                Path("C:/Windows/Fonts/arialbd.ttf"),
                Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
                Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"),
            ]
            font_size = max(20, int(image.width / 30))
            for candidate in font_candidates:
                try:
                    if candidate.exists():
                        font = ImageFont.truetype(str(candidate), font_size)
                        break
                except Exception:
                    pass
            if font is None:
                font = ImageFont.load_default()

            watermark = "SASTOUKASTORE • APERÇU"
            step_x = max(260, image.width // 3)
            step_y = max(190, image.height // 6)

            for y in range(-step_y, image.height + step_y, step_y):
                for x in range(-step_x, image.width + step_x, step_x):
                    draw.text(
                        (x, y),
                        watermark,
                        font=font,
                        fill=(255, 255, 255, 92),
                        stroke_width=2,
                        stroke_fill=(8, 17, 31, 80),
                    )

            overlay = overlay.rotate(-28, resample=Image.Resampling.BICUBIC, expand=False)
            image = Image.alpha_composite(image, overlay).convert("RGB")

            buffer = BytesIO()
            image.save(buffer, format="JPEG", quality=80, optimize=True)
            buffer.seek(0)

            response = send_file(
                buffer,
                mimetype="image/jpeg",
                as_attachment=False,
                download_name=f"apercu-{product_id}-{page_num}.jpg",
                max_age=0,
            )
            response.headers["Content-Disposition"] = "inline"
            response.headers["Cache-Control"] = "private, no-store, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["X-Content-Type-Options"] = "nosniff"
            return response
        finally:
            doc.close()
    except Exception:
        return "Impossible de générer l’aperçu.", 500
@shop.route("/panier")
def cart():
    return render_template("cart.html")

@shop.route("/commande")
def checkout():
    return render_template("checkout.html")

# === SastoukaStore PATCH 3 : ORDER ENGINE V3 ===
# === SastoukaStore PATCH 3 : ORDER ENGINE V3 ===
@shop.post("/api/commande")
def create_order():
    data = request.get_json(silent=True) or {}
    result, status = process_order(data, require_address=True)
    return jsonify(result), status
# === FIN SastoukaStore PATCH 3 ===
