# -*- coding: utf-8 -*-
from phone_utils import normalize_phone, validate_phone
from order_engine_v3 import process_order
"""
SastoukaStore — commandes de supports PDF numériques
Confirmation de commande uniquement.
Aucun paiement en ligne n'est déclenché ici.
"""
from flask import Blueprint, request, jsonify
from pathlib import Path
import sqlite3
import json

SastoukaStore_ICON_PATH_6_6 = Path(__file__).resolve().parent / "static" / "icons" / "sastoukastore-icon.png"

digital_orders = Blueprint("digital_orders", __name__)
DB = Path(__file__).resolve().parent / "data" / "chariow.db"

def db():
    con = sqlite3.connect(DB, timeout=15.0)
    con.row_factory = sqlite3.Row
    return con

def get_payload():
    data = request.get_json(silent=True)
    if isinstance(data, dict):
        return data

    data = request.form.to_dict()
    if "payload" in data:
        try:
            payload = json.loads(data["payload"])
            if isinstance(payload, dict):
                return payload
        except Exception:
            pass

    if "items" in data and isinstance(data["items"], str):
        try:
            data["items"] = json.loads(data["items"])
        except Exception:
            pass

    return data

# === SastoukaStore PATCH 3 : ORDER ENGINE V3 ===
# === SastoukaStore PATCH 3 : ORDER ENGINE V3 ===
@digital_orders.route("/api/commande-digitale", methods=["POST"])
def commande_digitale():
    data = get_payload()
    result, status = process_order(data, require_address=False)
    return jsonify(result), status
# === FIN SastoukaStore PATCH 3 ===
