# -*- coding: utf-8 -*-
from flask import Blueprint, render_template, request, Response
from pathlib import Path
import sqlite3
import csv
import io

admin_dashboard = Blueprint("admin_dashboard", __name__)
DB = Path(__file__).resolve().parent / "data" / "chariow.db"

def db():
    con = sqlite3.connect(DB, timeout=15.0)
    con.row_factory = sqlite3.Row
    return con

@admin_dashboard.route("/admin")
@admin_dashboard.route("/admin/dashboard")
def dashboard():
    period = request.args.get("period", "all")
    where = ""
    params = []

    if period == "today":
        where = "WHERE date(o.created_at)=date('now','localtime')"
    elif period == "7d":
        where = "WHERE datetime(o.created_at)>=datetime('now','localtime','-7 day')"
    elif period == "30d":
        where = "WHERE datetime(o.created_at)>=datetime('now','localtime','-30 day')"
    elif period == "year":
        where = "WHERE strftime('%Y',o.created_at)=strftime('%Y','now','localtime')"

    con = db()

    total_orders = con.execute(
        f"SELECT COUNT(*) FROM orders o {where}"
    ).fetchone()[0]

    revenue = con.execute(
        f"""SELECT COALESCE(SUM(o.total),0)
            FROM orders o
            {where}
            AND COALESCE(o.payment_status,'pending') NOT IN ('refunded','failed')"""
        if where else
        """SELECT COALESCE(SUM(o.total),0)
           FROM orders o
           WHERE COALESCE(o.payment_status,'pending') NOT IN ('refunded','failed')"""
    ).fetchone()[0]

    paid_revenue = con.execute(
        f"""SELECT COALESCE(SUM(o.total),0)
            FROM orders o
            {where}
            AND o.payment_status='paid'"""
        if where else
        """SELECT COALESCE(SUM(o.total),0)
           FROM orders o
           WHERE o.payment_status='paid'"""
    ).fetchone()[0]

    customers = con.execute(
        f"""SELECT COUNT(*) FROM customers c
            WHERE EXISTS (
                SELECT 1 FROM orders o WHERE o.customer_id=c.id
                {"AND " + where[6:] if where.startswith("WHERE ") else ""}
            )"""
    ).fetchone()[0] if where else con.execute("SELECT COUNT(*) FROM customers").fetchone()[0]

    products = con.execute(
        "SELECT COUNT(*) FROM products"
    ).fetchone()[0]

    low_stock = con.execute(
        "SELECT COUNT(*) FROM products WHERE COALESCE(stock,0)<=5 AND COALESCE(active,1)=1"
    ).fetchone()[0]

    out_of_stock = con.execute(
        "SELECT COUNT(*) FROM products WHERE COALESCE(stock,0)<=0 AND COALESCE(active,1)=1"
    ).fetchone()[0]

    recent = con.execute("""
        SELECT o.id,o.total,o.payment_status,o.delivery_status,o.created_at,
               COALESCE(c.name,'Client') AS customer_name
        FROM orders o
        LEFT JOIN customers c ON c.id=o.customer_id
        ORDER BY o.id DESC LIMIT 10
    """).fetchall()

    top_products = con.execute(f"""
        SELECT oi.product_name,
               SUM(oi.quantity) AS qty,
               SUM(oi.subtotal) AS amount
        FROM order_items oi
        JOIN orders o ON o.id=oi.order_id
        {where}
        GROUP BY oi.product_id, oi.product_name
        ORDER BY qty DESC, amount DESC
        LIMIT 8
    """).fetchall()

    by_status = con.execute(f"""
        SELECT COALESCE(o.delivery_status,'pending') AS status, COUNT(*) AS n
        FROM orders o
        {where}
        GROUP BY COALESCE(o.delivery_status,'pending')
        ORDER BY n DESC
    """).fetchall()

    by_day = con.execute(f"""
        SELECT date(o.created_at) AS day,
               COUNT(*) AS orders_count,
               COALESCE(SUM(o.total),0) AS revenue
        FROM orders o
        {where}
        GROUP BY date(o.created_at)
        ORDER BY day DESC
        LIMIT 14
    """).fetchall()

    con.close()

    return render_template(
        "admin_dashboard.html",
        period=period,
        total_orders=total_orders,
        revenue=revenue,
        paid_revenue=paid_revenue,
        customers=customers,
        products=products,
        low_stock=low_stock,
        out_of_stock=out_of_stock,
        recent=recent,
        top_products=top_products,
        by_status=by_status,
        by_day=list(reversed(by_day)),
    )

@admin_dashboard.route("/admin/export-commandes.csv")
def export_orders():
    con = db()
    rows = con.execute("""
        SELECT o.id,
               COALESCE(c.name,'') AS customer_name,
               COALESCE(c.phone,'') AS customer_phone,
               COALESCE(c.address,'') AS customer_address,
               COALESCE(c.city,'') AS city,
               o.total,
               o.payment_method,
               o.payment_status,
               o.delivery_status,
               o.created_at
        FROM orders o
        LEFT JOIN customers c ON c.id=o.customer_id
        ORDER BY o.id DESC
    """).fetchall()
    con.close()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow([
        "Commande","Client","Téléphone","Adresse","Ville","Total",
        "Mode paiement","Statut paiement","Statut livraison","Date"
    ])
    for r in rows:
        writer.writerow([
            r["id"], r["customer_name"], r["customer_phone"],
            r["customer_address"], r["city"], r["total"],
            r["payment_method"], r["payment_status"],
            r["delivery_status"], r["created_at"]
        ])

    data = "\ufeff" + output.getvalue()
    return Response(
        data,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=sastoukastore_commandes.csv"}
    )
