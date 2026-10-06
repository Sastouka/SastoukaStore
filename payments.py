# -*- coding: utf-8 -*-
"""SastoukaStore — API PayPal Checkout."""
from __future__ import annotations

import re
import sqlite3
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from flask import Blueprint, jsonify, request

from download_access import ensure_schema, generate_key
from payment_service import (
    SUPPORTED_METHODS,
    capture_paypal_order,
    create_paypal_order,
    load_paypal_config,
)

payments = Blueprint("payments", __name__)
DB = Path(__file__).resolve().parent / "data" / "chariow.db"
_PHONE_RE = re.compile(r"[^0-9+]")


def db():
    con = sqlite3.connect(DB, timeout=30.0)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA busy_timeout=30000")
    return con


def normalize_phone(value: str) -> str:
    value = _PHONE_RE.sub("", str(value or ""))
    if value.startswith("00"):
        value = "+" + value[2:]
    return value


def ensure_payment_table(con):
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS payment_intents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            provider TEXT NOT NULL,
            payment_method TEXT NOT NULL,
            amount REAL NOT NULL DEFAULT 0,
            currency TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'pending',
            reference TEXT,
            checkout_url TEXT,
            paypal_amount REAL,
            paypal_currency TEXT DEFAULT '',
            transaction_id TEXT DEFAULT '',
            invoice_id TEXT DEFAULT '',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(order_id)
        )
        """
    )
    cols = {r[1] for r in con.execute("PRAGMA table_info(payment_intents)").fetchall()}
    additions = {
        "paypal_amount": "REAL",
        "paypal_currency": "TEXT DEFAULT ''",
        "transaction_id": "TEXT DEFAULT ''",
        "invoice_id": "TEXT DEFAULT ''",
    }
    for name, definition in additions.items():
        if name not in cols:
            con.execute(f"ALTER TABLE payment_intents ADD COLUMN {name} {definition}")


def _same_phone(a: str, b: str) -> bool:
    return normalize_phone(a or "") == normalize_phone(b or "")


@payments.route("/api/payment/config", methods=["GET"])
def payment_config():
    try:
        config = load_paypal_config()
        return jsonify({
            "ok": True,
            "enabled": True,
            "provider": "paypal",
            "client_id": config.client_id,
            "environment": config.environment,
            "currency": config.currency,
            "method": "paypal",
        })
    except Exception as exc:
        return jsonify({
            "ok": False,
            "enabled": False,
            "provider": "paypal",
            "error": str(exc),
        }), 503


@payments.route("/api/payment/methods", methods=["GET"])
def payment_methods():
    try:
        config = load_paypal_config()
        return jsonify({
            "ok": True,
            "provider_mode": "paypal",
            "methods": [{"id": "paypal", "name": "PayPal"}],
            "paypal_currency": config.currency,
            "environment": config.environment,
            "online_payment_active": True,
        })
    except Exception as exc:
        return jsonify({
            "ok": False,
            "provider_mode": "paypal",
            "methods": [],
            "online_payment_active": False,
            "error": str(exc),
        }), 503


@payments.route("/api/payment/create", methods=["POST"])
def create_payment_intent():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        data = request.form.to_dict()

    try:
        order_id = int(data.get("order_id", 0))
    except (TypeError, ValueError):
        order_id = 0

    phone = normalize_phone(data.get("phone", ""))
    if order_id <= 0 or not phone:
        return jsonify({"ok": False, "error": "Commande ou téléphone invalide."}), 400

    con = db()
    try:
        ensure_payment_table(con)
        # La colonne currency n'existe pas dans certaines anciennes bases.
        order_cols = {r[1] for r in con.execute("PRAGMA table_info(orders)").fetchall()}
        if "currency" not in order_cols:
            con.execute("ALTER TABLE orders ADD COLUMN currency TEXT DEFAULT 'FCFA'")
            order_cols.add("currency")

        row = con.execute(
            """
            SELECT o.id, o.total, o.payment_method, o.payment_status,
                   COALESCE(o.currency,'FCFA') AS order_currency,
                   c.phone AS customer_phone, c.email AS customer_email
            FROM orders o
            LEFT JOIN customers c ON c.id=o.customer_id
            WHERE o.id=?
            LIMIT 1
            """,
            (order_id,),
        ).fetchone()
        if not row:
            return jsonify({"ok": False, "error": "Commande introuvable."}), 404
        if not _same_phone(row["customer_phone"], phone):
            return jsonify({"ok": False, "error": "Accès refusé."}), 403
        if str(row["payment_status"] or "").lower() == "paid":
            return jsonify({"ok": False, "error": "Cette commande est déjà payée."}), 409

        existing = con.execute(
            "SELECT reference, status, checkout_url FROM payment_intents WHERE order_id=? LIMIT 1",
            (order_id,),
        ).fetchone()
        if existing and existing["status"] == "created" and existing["reference"]:
            return jsonify({
                "ok": True,
                "order_id": order_id,
                "paypal_order_id": existing["reference"],
                "checkout_url": existing["checkout_url"],
                "status": "created",
                "message": "Commande PayPal déjà préparée.",
            })

        result = create_paypal_order(
            order_id=order_id,
            amount=float(row["total"] or 0),
            local_currency=str(row["order_currency"] or "FCFA"),
            customer_email=str(row["customer_email"] or ""),
        )

        con.execute(
            """
            INSERT INTO payment_intents(
                order_id, provider, payment_method, amount, currency, status,
                reference, checkout_url, paypal_amount, paypal_currency, transaction_id
            )
            VALUES(?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(order_id) DO UPDATE SET
                provider=excluded.provider,
                payment_method=excluded.payment_method,
                amount=excluded.amount,
                currency=excluded.currency,
                status=excluded.status,
                reference=excluded.reference,
                checkout_url=excluded.checkout_url,
                paypal_amount=excluded.paypal_amount,
                paypal_currency=excluded.paypal_currency,
                transaction_id='',
                updated_at=CURRENT_TIMESTAMP
            """,
            (
                order_id,
                "paypal",
                "paypal",
                float(row["total"] or 0),
                str(row["order_currency"] or "FCFA"),
                "created",
                result["paypal_order_id"],
                result.get("approve_url") or "",
                float(result["paypal_amount"]),
                str(result["paypal_currency"]),
                "",
            ),
        )
        con.commit()
        return jsonify({
            "ok": True,
            "order_id": order_id,
            "paypal_order_id": result["paypal_order_id"],
            "paypal_amount": result["paypal_amount"],
            "paypal_amount_text": result["paypal_amount_text"],
            "paypal_currency": result["paypal_currency"],
            "checkout_url": result.get("approve_url") or "",
            "status": "created",
            "message": "Commande PayPal créée.",
        })
    except Exception as exc:
        con.rollback()
        return jsonify({"ok": False, "error": str(exc)}), 502
    finally:
        con.close()


@payments.route("/api/payment/capture", methods=["POST"])
def capture_payment():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        data = request.form.to_dict()

    paypal_order_id = str(data.get("paypal_order_id") or data.get("orderID") or "").strip()
    phone = normalize_phone(data.get("phone", ""))
    if not paypal_order_id or not phone:
        return jsonify({"ok": False, "error": "Commande PayPal ou téléphone invalide."}), 400

    con = db()
    try:
        ensure_payment_table(con)
        intent = con.execute(
            """
            SELECT pi.*, o.total AS order_total,
                   COALESCE(o.currency,'FCFA') AS order_currency,
                   o.payment_status,
                   c.phone AS customer_phone
            FROM payment_intents pi
            INNER JOIN orders o ON o.id=pi.order_id
            LEFT JOIN customers c ON c.id=o.customer_id
            WHERE pi.reference=? AND pi.provider='paypal'
            LIMIT 1
            """,
            (paypal_order_id,),
        ).fetchone()
        if not intent:
            return jsonify({"ok": False, "error": "Transaction PayPal inconnue."}), 404
        if not _same_phone(intent["customer_phone"], phone):
            return jsonify({"ok": False, "error": "Accès refusé."}), 403
        if str(intent["payment_status"] or "").lower() == "paid":
            return jsonify({
                "ok": True,
                "status": "completed",
                "order_id": intent["order_id"],
                "paypal_order_id": paypal_order_id,
                "already_paid": True,
            })

        captured = capture_paypal_order(paypal_order_id)
        if captured["status"] != "COMPLETED":
            return jsonify({
                "ok": False,
                "status": captured["status"] or "FAILED",
                "error": "Le paiement PayPal n'a pas été finalisé.",
            }), 409

        expected_currency = str(intent["paypal_currency"] or "").upper()
        received_currency = str(captured["currency"] or "").upper()
        expected_amount = Decimal(str(intent["paypal_amount"] or "0"))
        received_amount = Decimal(str(captured["amount"] or "0"))
        quant = Decimal("1") if expected_currency in {"HUF", "JPY", "TWD"} else Decimal("0.01")
        expected_amount = expected_amount.quantize(quant, rounding=ROUND_HALF_UP)
        received_amount = received_amount.quantize(quant, rounding=ROUND_HALF_UP)

        if expected_currency != received_currency or expected_amount != received_amount:
            con.execute(
                "UPDATE payment_intents SET status='failed', updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (intent["id"],),
            )
            con.commit()
            return jsonify({
                "ok": False,
                "error": "Le montant ou la devise capturés par PayPal ne correspondent pas à la commande.",
            }), 409

        ensure_schema(con)
        con.execute(
            """
            UPDATE orders SET payment_status='paid',
                payment_confirmed_at=CURRENT_TIMESTAMP,
                payment_confirmed_by='paypal',
                payment_confirmation_channel='paypal',
                payment_confirmation_note=?
            WHERE id=?
            """,
            (f"PayPal capture {captured['capture_id'] or paypal_order_id}", intent["order_id"]),
        )
        con.execute(
            """
            UPDATE payment_intents SET status='completed', transaction_id=?,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (captured["capture_id"], intent["id"]),
        )
        con.commit()

        con2 = db()
        try:
            ensure_schema(con2)
            plain_key = generate_key(
                con2,
                int(intent["order_id"]),
                str(intent["customer_phone"] or ""),
                "paypal",
            )
            con2.commit()
        finally:
            con2.close()

        access_url = (
            request.host_url.rstrip("/")
            + f"/telechargements/{int(intent['order_id'])}"
            + "?key=" + plain_key
        )
        return jsonify({
            "ok": True,
            "status": "completed",
            "order_id": int(intent["order_id"]),
            "paypal_order_id": paypal_order_id,
            "transaction_id": captured["capture_id"],
            "payment_reference": paypal_order_id,
            "key": plain_key,
            "download_url": access_url,
            "message": "Paiement PayPal confirmé. Vos supports PDF sont disponibles.",
        })
    except Exception as exc:
        con.rollback()
        return jsonify({"ok": False, "error": str(exc)}), 502
    finally:
        con.close()


@payments.route("/api/payment/status", methods=["GET"])
def payment_status():
    raw_order_id = request.args.get("order_id", "").strip()
    phone = normalize_phone(request.args.get("phone", ""))
    try:
        order_id = int(raw_order_id)
    except (TypeError, ValueError):
        order_id = 0
    if order_id <= 0 or not phone:
        return jsonify({"ok": False, "error": "Commande ou téléphone invalide."}), 400

    con = db()
    try:
        ensure_payment_table(con)
        row = con.execute(
            """
            SELECT o.id, o.payment_status, c.phone AS customer_phone
            FROM orders o
            LEFT JOIN customers c ON c.id=o.customer_id
            WHERE o.id=? LIMIT 1
            """,
            (order_id,),
        ).fetchone()
        if not row:
            return jsonify({"ok": False, "error": "Commande introuvable."}), 404
        if not _same_phone(row["customer_phone"], phone):
            return jsonify({"ok": False, "error": "Accès refusé."}), 403

        intent = con.execute(
            """
            SELECT provider, payment_method, amount, currency, status,
                   reference, checkout_url, paypal_amount, paypal_currency,
                   transaction_id, created_at, updated_at
            FROM payment_intents WHERE order_id=? LIMIT 1
            """,
            (order_id,),
        ).fetchone()
        return jsonify({
            "ok": True,
            "order_id": order_id,
            "order_payment_status": row["payment_status"],
            "payment_intent": dict(intent) if intent else None,
        })
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500
    finally:
        con.close()
