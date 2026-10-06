# -*- coding: utf-8 -*-
from flask import Blueprint, render_template, request, jsonify
from pathlib import Path
import sqlite3

from phone_utils import normalize_phone, validate_phone

SastoukaStore_ICON_PATH_6_6 = Path(__file__).resolve().parent / "static" / "icons" / "sastoukastore-icon.png"
customer_tracking = Blueprint("customer_tracking", __name__)
# === SastoukaStore PATCH 2 : NORMALISATION TELEPHONE ===
DB = Path(__file__).resolve().parent / "data" / "chariow.db"

STATUSES = {
    "pending": ("Commande reçue", "Votre commande a bien été enregistrée."),
    "confirmed": ("Commande confirmée", "Votre commande a été confirmée."),
    "preparing": ("Préparation", "Votre commande est en cours de préparation."),
    "shipped": ("Expédiée", "Votre commande est en cours d'acheminement."),
    "delivered": ("Livrée", "La commande a été livrée."),
    "cancelled": ("Annulée", "Cette commande a été annulée.")
}

def db():
    c = sqlite3.connect(DB, timeout=15.0)
    c.row_factory = sqlite3.Row
    return c

@customer_tracking.route("/suivi-commande", methods=["GET", "POST"])
def suivi_commande():
    order = None
    items = []
    error = None
    phone = request.values.get("phone", "").strip()
    phone = normalize_phone(phone)
    raw_id = request.values.get("order_id", "").strip()

    if raw_id and phone:
        try:
            order_id = int(raw_id)
        except ValueError:
            order_id = 0

        con = db()
        order = con.execute("""
            SELECT o.*, c.name AS customer_name, c.phone AS customer_phone,
                   c.address AS customer_address, c.city AS customer_city
            FROM orders o
            LEFT JOIN customers c ON c.id=o.customer_id
            WHERE o.id=? AND REPLACE(REPLACE(COALESCE(c.phone,''),' ',''),'-','')
                    = REPLACE(REPLACE(?,' ',''),'-','')
        """, (order_id, phone)).fetchone()

        if order:
            items = con.execute("""
                SELECT product_id, product_name, quantity, unit_price, subtotal, variant
                FROM order_items WHERE order_id=? ORDER BY id
            """, (order_id,)).fetchall()
        else:
            error = "Commande introuvable. Vérifiez le numéro et le téléphone."
        con.close()

    status_code = order["delivery_status"] if order else None
    status_label, status_text = STATUSES.get(
        status_code, ("Suivi de commande", "Consultez l'évolution de votre commande.")
    )

    return render_template(
        "order_tracking.html",
        order=order,
        items=items,
        error=error,
        phone=phone,
        order_id=raw_id,
        status_label=status_label,
        status_text=status_text,
        statuses=STATUSES
    )

@customer_tracking.route("/api/suivi-commande")
def api_suivi():
    raw_id = request.args.get("order_id", "").strip()
    phone = request.args.get("phone", "").strip()
    phone = normalize_phone(phone)
    try:
        order_id = int(raw_id)
    except ValueError:
        order_id = 0

    con = db()
    order = con.execute("""
        SELECT o.id, o.total, o.payment_method, o.payment_status,
               o.delivery_status, o.created_at,
               c.name AS customer_name
        FROM orders o
        LEFT JOIN customers c ON c.id=o.customer_id
        WHERE o.id=? AND REPLACE(REPLACE(COALESCE(c.phone,''),' ',''),'-','')
              = REPLACE(REPLACE(?,' ',''),'-','')
    """, (order_id, phone)).fetchone()
    con.close()

    if not order:
        return jsonify({"ok": False, "error": "Commande introuvable"}), 404

    label, text = STATUSES.get(
        order["delivery_status"],
        ("Suivi de commande", "Statut non renseigné.")
    )
    return jsonify({
        "ok": True,
        "order": {
            "id": order["id"],
            "total": order["total"],
            "payment_method": order["payment_method"],
            "payment_status": order["payment_status"],
            "delivery_status": order["delivery_status"],
            "delivery_label": label,
            "delivery_text": text,
            "customer_name": order["customer_name"],
            "created_at": order["created_at"]
        }
    })


# === SastoukaStore PATCH 1 : TELECHARGEMENT SECURISE ===
from flask import send_from_directory, abort

# === SastoukaStore PATCH 4 : TELECHARGEMENT PDF SECURISE ===
@customer_tracking.route("/telecharger/<int:order_id>/<int:product_id>")
def telecharger_pdf(order_id, product_id):
    phone_input = request.args.get("phone", "").strip()

    try:
        from phone_utils import normalize_phone, is_valid_phone
        phone = normalize_phone(phone_input)
        if not phone or not is_valid_phone(phone):
            abort(403, "Accès refusé.")
    except Exception:
        phone = re.sub(r"\D", "", phone_input)
        if len(phone) < 8 or len(phone) > 15:
            abort(403, "Accès refusé.")

    con = db()
    try:
        order = con.execute(
            """
            SELECT o.id, o.payment_status, c.phone AS customer_phone
            FROM orders o
            LEFT JOIN customers c ON c.id=o.customer_id
            WHERE o.id=?
            """,
            (order_id,),
        ).fetchone()

        if not order:
            abort(404, "Commande introuvable.")

        db_phone = str(order["customer_phone"] or "").strip()
        try:
            from phone_utils import normalize_phone
            normalized_db_phone = normalize_phone(db_phone)
        except Exception:
            normalized_db_phone = re.sub(r"\D", "", db_phone)

        if phone != normalized_db_phone:
            abort(403, "Accès refusé.")

        if order["payment_status"] != "paid":
            abort(403, "Accès refusé.")

        item = con.execute(
            """
            SELECT oi.product_id, p.pdf_file, p.active
            FROM order_items oi
            INNER JOIN products p ON p.id=oi.product_id
            WHERE oi.order_id=? AND oi.product_id=?
            ORDER BY oi.id
            LIMIT 1
            """,
            (order_id, product_id),
        ).fetchone()

        if not item:
            abort(403, "Accès refusé.")

        if item["active"] is not None and not int(item["active"]):
            abort(404, "Document indisponible.")

        pdf_name = str(item["pdf_file"] or "").strip()
        if not pdf_name:
            abort(404, "Document indisponible.")

        pdf_path = Path(pdf_name)
        if pdf_path.name != pdf_name or pdf_path.suffix.lower() != ".pdf":
            abort(404, "Document indisponible.")

        protected_dir = Path(__file__).resolve().parent / "protected_data" / "pdfs"
        target = protected_dir / pdf_name

        try:
            target.resolve().relative_to(protected_dir.resolve())
        except ValueError:
            abort(404, "Document indisponible.")

        if not target.is_file():
            abort(404, "Document indisponible.")

        response = send_from_directory(
            protected_dir,
            pdf_name,
            as_attachment=True,
            conditional=True,
        )
        response.headers["Cache-Control"] = "private, no-store, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response
    finally:
        con.close()
# === FIN SastoukaStore PATCH 4 ===

