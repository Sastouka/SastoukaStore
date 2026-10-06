from flask import Blueprint, render_template, request, redirect, url_for, jsonify
import sqlite3
from pathlib import Path

admin_orders = Blueprint("admin_orders", __name__)
DB = Path(__file__).resolve().parent / "data" / "chariow.db"

def db():
    con = sqlite3.connect(DB, timeout=15.0)
    con.row_factory = sqlite3.Row
    return con

@admin_orders.route("/admin/commandes")
def commandes():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    con = db()
    sql = """SELECT o.*, c.name AS c_name, c.phone AS c_phone
             FROM orders o LEFT JOIN customers c ON c.id=o.customer_id WHERE 1=1"""
    params = []
    if q:
        sql += " AND (CAST(o.id AS TEXT) LIKE ? OR COALESCE(c.name,'') LIKE ? OR COALESCE(c.phone,'') LIKE ?)"
        x=f"%{q}%"; params += [x,x,x]
    if status:
        sql += " AND o.delivery_status=?"; params.append(status)
    sql += " ORDER BY o.id DESC"
    rows=con.execute(sql,params).fetchall()
    stats={}
    for s in ["pending","confirmed","preparing","shipped","delivered","cancelled"]:
        stats[s]=con.execute("SELECT COUNT(*) FROM orders WHERE delivery_status=?",(s,)).fetchone()[0]
    con.close()
    return render_template("admin_orders.html",orders=rows,stats=stats,q=q,status=status)

@admin_orders.route("/admin/commande/<int:order_id>")
def commande_detail(order_id):
    con=db()
    order=con.execute("""SELECT o.*,c.name AS c_name,c.phone AS c_phone,c.email AS c_email,
                         c.address AS c_address,c.city AS c_city
                         FROM orders o LEFT JOIN customers c ON c.id=o.customer_id WHERE o.id=?""",(order_id,)).fetchone()
    if not order: con.close(); return "Commande introuvable",404
    items=con.execute("SELECT * FROM order_items WHERE order_id=? ORDER BY id",(order_id,)).fetchall()
    try:
        payment_intent=con.execute("SELECT * FROM payment_intents WHERE order_id=? LIMIT 1",(order_id,)).fetchone()
    except sqlite3.OperationalError:
        payment_intent=None
    con.close()
    return render_template("admin_order_detail.html",order=order,items=items,payment_intent=payment_intent)

@admin_orders.route("/admin/commande/<int:order_id>/statut",methods=["POST"])
def statut(order_id):
    value=request.form.get("delivery_status","pending")
    if value not in {"pending","confirmed","preparing","shipped","delivered","cancelled"}: return "Statut invalide",400
    con=db(); con.execute("UPDATE orders SET delivery_status=? WHERE id=?",(value,order_id)); con.commit(); con.close()
    return redirect(url_for("admin_orders.commande_detail",order_id=order_id))

@admin_orders.route("/admin/commande/<int:order_id>/paiement",methods=["POST"])
def paiement(order_id):
    value=request.form.get("payment_status","pending")
    if value not in {"pending","paid","failed","refunded"}: return "Statut invalide",400
    con=db(); con.execute("UPDATE orders SET payment_status=? WHERE id=?",(value,order_id)); con.commit(); con.close()
    return redirect(url_for("admin_orders.commande_detail",order_id=order_id))

@admin_orders.route("/admin/clients")
def clients():
    q=request.args.get("q","").strip(); con=db()
    sql="""SELECT c.*,COUNT(o.id) orders_count,COALESCE(SUM(o.total),0) total_spent
           FROM customers c LEFT JOIN orders o ON o.customer_id=c.id WHERE 1=1"""
    params=[]
    if q:
        sql+=" AND (c.name LIKE ? OR c.phone LIKE ? OR c.email LIKE ?)"
        x=f"%{q}%"; params=[x,x,x]
    sql+=" GROUP BY c.id ORDER BY c.id DESC"
    rows=con.execute(sql,params).fetchall(); con.close()
    return render_template("admin_clients.html",clients=rows,q=q)

@admin_orders.route("/api/admin/commandes/stats")
def api_stats():
    con=db()
    data={"total":con.execute("SELECT COUNT(*) FROM orders").fetchone()[0],
          "ca":con.execute("SELECT COALESCE(SUM(total),0) FROM orders WHERE payment_status!='refunded'").fetchone()[0],
          "pending":con.execute("SELECT COUNT(*) FROM orders WHERE delivery_status='pending'").fetchone()[0],
          "delivered":con.execute("SELECT COUNT(*) FROM orders WHERE delivery_status='delivered'").fetchone()[0]}
    con.close(); return jsonify(data)

# === SASTOUKASTORE PATCH VENTES LIVE V1 ===
from datetime import datetime as _dt_live


def _live_cover_url(product_id, image_value):
    raw = str(image_value or "").strip()
    if raw.startswith(("http://", "https://", "/")):
        return raw
    if raw:
        return "/static/" + raw.lstrip("/")
    return f"/apercu-pdf/{int(product_id)}?page=1"


def _live_clean_date(value):
    value = str(value or "").strip()
    try:
        _dt_live.strptime(value, "%Y-%m-%d")
        return value
    except ValueError:
        return ""


def _live_sales_filters():
    q = request.args.get("q", "").strip()
    date_debut = _live_clean_date(request.args.get("date_debut", ""))
    date_fin = _live_clean_date(request.args.get("date_fin", ""))
    if date_debut and date_fin and date_fin < date_debut:
        date_debut, date_fin = date_fin, date_debut
    return q, date_debut, date_fin


def _live_where(q, date_debut, date_fin):
    where = ["COALESCE(o.payment_status,'pending') = 'paid'"]
    params = []
    if date_debut:
        where.append("date(o.created_at,'localtime') >= ?")
        params.append(date_debut)
    if date_fin:
        where.append("date(o.created_at,'localtime') <= ?")
        params.append(date_fin)
    if q:
        where.append("""
            (
                CAST(o.id AS TEXT) LIKE ?
                OR COALESCE(c.name,'') LIKE ?
                OR COALESCE(c.phone,'') LIKE ?
                OR EXISTS (
                    SELECT 1 FROM order_items oq
                    WHERE oq.order_id=o.id
                      AND COALESCE(oq.product_name,'') LIKE ?
                )
            )
        """)
        x = f"%{q}%"
        params.extend([x, x, x, x])
    return " AND ".join(where), params


def _live_sales_snapshot(limit=200):
    q, date_debut, date_fin = _live_sales_filters()
    where_sql, params = _live_where(q, date_debut, date_fin)
    con = db()

    orders = con.execute(f"""
        SELECT o.id,o.total,o.payment_method,o.payment_status,
               o.delivery_status,o.created_at,
               COALESCE(c.name,'Client') AS customer_name,
               COALESCE(c.phone,'') AS customer_phone
        FROM orders o
        LEFT JOIN customers c ON c.id=o.customer_id
        WHERE {where_sql}
        ORDER BY o.id DESC
        LIMIT ?
    """, [*params, int(limit)]).fetchall()

    order_ids = [int(r["id"]) for r in orders]
    items_by_order = {oid: [] for oid in order_ids}

    if order_ids:
        placeholders = ",".join("?" for _ in order_ids)
        item_rows = con.execute(f"""
            SELECT oi.id,oi.order_id,oi.product_id,
                   COALESCE(oi.product_name,p.name,'Support PDF') AS product_name,
                   COALESCE(oi.quantity,1) AS quantity,
                   COALESCE(oi.subtotal,0) AS subtotal,
                   COALESCE(oi.variant,'') AS variant,
                   COALESCE(p.image,'') AS image
            FROM order_items oi
            LEFT JOIN products p ON p.id=oi.product_id
            WHERE oi.order_id IN ({placeholders})
            ORDER BY oi.order_id DESC,oi.id ASC
        """, order_ids).fetchall()

        for r in item_rows:
            pid = int(r["product_id"] or 0)
            items_by_order[int(r["order_id"])].append({
                "id": int(r["id"]),
                "product_id": pid,
                "product_name": r["product_name"] or "Support PDF",
                "quantity": int(r["quantity"] or 1),
                "subtotal": float(r["subtotal"] or 0),
                "variant": r["variant"] or "",
                "cover_url": _live_cover_url(pid, r["image"]),
            })

    kpi = con.execute(f"""
        SELECT COUNT(*) AS sales_count,
               COALESCE(SUM(o.total),0) AS revenue,
               COUNT(DISTINCT o.customer_id) AS customers
        FROM orders o
        LEFT JOIN customers c ON c.id=o.customer_id
        WHERE {where_sql}
    """, params).fetchone()

    books = con.execute(f"""
        SELECT COALESCE(SUM(oi.quantity),0)
        FROM order_items oi
        JOIN orders o ON o.id=oi.order_id
        LEFT JOIN customers c ON c.id=o.customer_id
        WHERE {where_sql}
    """, params).fetchone()[0]

    latest = con.execute(f"""
        SELECT COALESCE(MAX(o.id),0)
        FROM orders o
        LEFT JOIN customers c ON c.id=o.customer_id
        WHERE {where_sql}
    """, params).fetchone()[0]

    con.close()

    sales = []
    for r in orders:
        oid = int(r["id"])
        sales.append({
            "id": oid,
            "total": float(r["total"] or 0),
            "payment_method": r["payment_method"] or "paypal",
            "payment_status": r["payment_status"] or "paid",
            "delivery_status": r["delivery_status"] or "pending",
            "created_at": r["created_at"] or "",
            "customer_name": r["customer_name"] or "Client",
            "customer_phone": r["customer_phone"] or "",
            "items": items_by_order.get(oid, []),
        })

    return {
        "sales": sales,
        "sales_count": int(kpi["sales_count"] or 0),
        "revenue": float(kpi["revenue"] or 0),
        "books_count": int(books or 0),
        "customers": int(kpi["customers"] or 0),
        "latest_sale_id": int(latest or 0),
        "server_time": _dt_live.now().astimezone().isoformat(timespec="seconds"),
        "filters": {"q": q, "date_debut": date_debut, "date_fin": date_fin},
    }


@admin_orders.route("/admin/ventes")
def ventes_live():
    return render_template("admin_sales_live.html", **_live_sales_snapshot())


@admin_orders.route("/api/admin/ventes")
def api_ventes_live():
    return jsonify(_live_sales_snapshot())


# === FIN SASTOUKASTORE PATCH VENTES LIVE V1 ===

# === SASTOUKASTORE ADMIN DIGITAL V2 ===
@admin_orders.route("/admin/achats")
def achats():
    return commandes()

# Accès détaillé sous le vocabulaire numérique.
@admin_orders.route("/admin/achat/<int:order_id>")
def achat_detail(order_id):
    return commande_detail(order_id)

# Alias LIVE officiel.
@admin_orders.route("/admin/achats-live")
def achats_live():
    snapshot = _live_sales_snapshot()
    return render_template("admin_sales_live.html", **snapshot)

# === FIN SASTOUKASTORE ADMIN DIGITAL V2 ===
