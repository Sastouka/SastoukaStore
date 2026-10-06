# -*- coding: utf-8 -*-
"""SastoukaStore — couche PayPal Checkout sécurisée."""
from __future__ import annotations

import os

import json
import secrets
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Dict

import requests
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent
SECRET_PATH = ROOT / "secret.json"

# PayPal REST transaction currencies actuellement utiles pour ce checkout.
# La liste complète dépend aussi du pays et du type de paiement.
PAYPAL_TRANSACTION_CURRENCIES = {
    "AUD", "BRL", "CAD", "CNY", "CZK", "DKK", "EUR", "HKD", "HUF",
    "ILS", "JPY", "MYR", "MXN", "TWD", "NZD", "NOK", "PHP", "PLN",
    "GBP", "RUB", "SGD", "SEK", "CHF", "THB", "USD"
}
ZERO_DECIMAL_CURRENCIES = {"HUF", "JPY", "TWD"}


@dataclass(frozen=True)
class PayPalConfig:
    client_id: str
    client_secret: str
    environment: str
    base_url: str
    currency: str
    exchange_rates: Dict[str, float]


def _load_secret_data() -> dict[str, Any]:
    if not SECRET_PATH.is_file():
        raise RuntimeError(
            f"Fichier secret PayPal introuvable : {SECRET_PATH}."
        )
    try:
        data = json.loads(SECRET_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"secret.json invalide : {exc}") from exc
    if not isinstance(data, dict):
        raise RuntimeError("secret.json doit contenir un objet JSON.")
    return data


def _paypal_section(data: dict[str, Any]) -> dict[str, Any]:
    section = data.get("paypal")
    return section if isinstance(section, dict) else data


def _first(section: dict[str, Any], *names: str, default: Any = None) -> Any:
    for name in names:
        value = section.get(name)
        if value not in (None, ""):
            return value
    return default


def load_paypal_config() -> PayPalConfig:
    # Sur Render, les variables d'environnement sont prioritaires.
    # En local, secret.json reste un fallback et n'est pas versionne.
    env_client_id = os.getenv("PAYPAL_CLIENT_ID", "").strip()
    env_client_secret = os.getenv("PAYPAL_CLIENT_SECRET", "").strip()

    if env_client_id and env_client_secret:
        client_id = env_client_id
        client_secret = env_client_secret
        environment = os.getenv("PAYPAL_ENVIRONMENT", "live").strip().lower() or "live"
        currency = os.getenv("PAYPAL_CURRENCY", "EUR").strip().upper() or "EUR"

        raw_rates_text = os.getenv("PAYPAL_EXCHANGE_RATES", "").strip()
        if raw_rates_text:
            try:
                raw_rates = json.loads(raw_rates_text)
            except Exception as exc:
                raise RuntimeError(
                    "PAYPAL_EXCHANGE_RATES doit contenir un objet JSON valide."
                ) from exc
        else:
            raw_rates = {}
    else:
        try:
            section = _paypal_section(_load_secret_data())
        except Exception as exc:
            raise RuntimeError(
                "Identifiants PayPal manquants. Sur Render, definissez "
                "PAYPAL_CLIENT_ID et PAYPAL_CLIENT_SECRET."
            ) from exc

        client_id = str(_first(
            section,
            "client_id",
            "clientId",
            "paypal_client_id",
            "PAYPAL_CLIENT_ID",
            default=""
        ) or "").strip()

        client_secret = str(_first(
            section,
            "client_secret",
            "clientSecret",
            "paypal_client_secret",
            "PAYPAL_CLIENT_SECRET",
            default=""
        ) or "").strip()

        environment = str(_first(
            section,
            "environment",
            "mode",
            "env",
            default="sandbox"
        ) or "sandbox").strip().lower()

        currency = str(_first(
            section,
            "currency",
            "paypal_currency",
            "PAYPAL_CURRENCY",
            default="EUR"
        ) or "EUR").strip().upper()

        raw_rates = _first(
            section,
            "exchange_rates",
            "rates",
            default={}
        )

    if not client_id or not client_secret:
        raise RuntimeError(
            "Identifiants PayPal manquants : PAYPAL_CLIENT_ID et "
            "PAYPAL_CLIENT_SECRET."
        )

    if environment in {"live", "production", "prod"}:
        environment = "live"
        base_url = "https://api-m.paypal.com"
    else:
        environment = "sandbox"
        base_url = "https://api-m.sandbox.paypal.com"

    if currency not in PAYPAL_TRANSACTION_CURRENCIES:
        raise RuntimeError(
            f"Devise PayPal non prise en charge par cette integration : {currency}. "
            "Utilisez notamment EUR ou USD."
        )

    exchange_rates: Dict[str, float] = {}
    if isinstance(raw_rates, dict):
        for key, value in raw_rates.items():
            try:
                rate = float(value)
                if rate > 0:
                    exchange_rates[str(key).strip().upper()] = rate
            except (TypeError, ValueError):
                continue

    return PayPalConfig(
        client_id=client_id,
        client_secret=client_secret,
        environment=environment,
        base_url=base_url,
        currency=currency,
        exchange_rates=exchange_rates,
    )


def _get_access_token(config: PayPalConfig) -> str:
    response = requests.post(
        f"{config.base_url}/v1/oauth2/token",
        auth=(config.client_id, config.client_secret),
        data={"grant_type": "client_credentials"},
        headers={"Accept": "application/json", "Accept-Language": "fr_FR"},
        timeout=30,
    )
    try:
        payload = response.json()
    except Exception:
        payload = {}
    if response.status_code >= 400:
        detail = payload.get("error_description") or payload.get("error") or response.text[:300]
        raise RuntimeError(f"Authentification PayPal impossible : {detail}")
    token = str(payload.get("access_token") or "").strip()
    if not token:
        raise RuntimeError("PayPal n'a pas renvoyé de jeton OAuth.")
    return token


def _paypal_headers(token: str, request_id: str | None = None) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if request_id:
        headers["PayPal-Request-Id"] = request_id
    return headers


def _money(value: Decimal, currency: str) -> str:
    if currency in ZERO_DECIMAL_CURRENCIES:
        return str(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP).to_integral())
    return f"{value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):.2f}"


def convert_to_paypal(
    amount: float | Decimal,
    local_currency: str,
    config: PayPalConfig,
) -> Decimal:
    raw_currency = str(local_currency or "FCFA").strip().upper()

    # SastoukaStore peut stocker/renvoyer la devise avec son symbole.
    # On la convertit vers le code ISO utilisé par PayPal.
    currency_aliases = {
        "€": "EUR",
        "EURO": "EUR",
        "EUR (€)": "EUR",
        "EUR€": "EUR",
        "$": "USD",
        "US$": "USD",
        "£": "GBP",
        "₤": "GBP",
    }
    local_currency = currency_aliases.get(raw_currency, raw_currency)

    paypal_currency = str(config.currency or "EUR").strip().upper()
    amount_dec = Decimal(str(amount or 0))

    if amount_dec < 0:
        raise RuntimeError("Montant négatif invalide.")

    # Même devise : aucune conversion n'est nécessaire.
    if local_currency == paypal_currency:
        converted = amount_dec
    else:
        # Parité fixe pour FCFA/XOF/XAF vers EUR.
        if local_currency in {"FCFA", "F CFA", "CFA", "XOF", "XAF"} and paypal_currency == "EUR":
            converted = amount_dec / Decimal("655.957")
        else:
            rate = config.exchange_rates.get(local_currency)
            if rate is None or rate <= 0:
                raise RuntimeError(
                    f"Taux de conversion manquant pour {raw_currency} -> {paypal_currency}. "
                    "Ajoutez-le dans secret.json, section exchange_rates."
                )
            converted = amount_dec * Decimal(str(rate))

    if converted <= 0:
        raise RuntimeError("Le montant PayPal doit être strictement positif.")

    if paypal_currency in ZERO_DECIMAL_CURRENCIES:
        return converted.quantize(Decimal("1"), rounding=ROUND_HALF_UP)

    return converted.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def create_paypal_order(
    *,
    order_id: int,
    amount: float,
    local_currency: str,
    customer_email: str = "",
) -> Dict[str, Any]:
    config = load_paypal_config()
    paypal_amount = convert_to_paypal(amount, local_currency, config)
    token = _get_access_token(config)

    unique = secrets.token_hex(5).upper()
    invoice_id = f"SastoukaStore-{order_id}-{unique}"
    payload: dict[str, Any] = {
        "intent": "CAPTURE",
        "purchase_units": [{
            "reference_id": f"CHW-{order_id}",
            "custom_id": f"CHW-{order_id}",
            "invoice_id": invoice_id,
            "description": "Supports PDF numériques SastoukaStore",
            "amount": {
                "currency_code": config.currency,
                "value": _money(paypal_amount, config.currency),
            },
        }],
        "application_context": {
            "brand_name": "SastoukaStore",
            "landing_page": "LOGIN",
            "user_action": "PAY_NOW",
            "shipping_preference": "NO_SHIPPING",
        },
    }

    # Le payer email n'est pas nécessaire au checkout PayPal standard.
    # Il est volontairement conservé hors du payload public pour éviter de dépendre
    # d'un flux spécifique de contact.
    _ = customer_email

    response = requests.post(
        f"{config.base_url}/v2/checkout/orders",
        headers=_paypal_headers(token, f"create-{invoice_id}"),
        json=payload,
        timeout=30,
    )
    try:
        data = response.json()
    except Exception:
        data = {}

    if response.status_code >= 400:
        detail = data.get("message") or data.get("details") or response.text[:500]
        raise RuntimeError(f"Création de commande PayPal impossible : {detail}")

    paypal_order_id = str(data.get("id") or "").strip()
    if not paypal_order_id:
        raise RuntimeError("PayPal n'a pas renvoyé d'identifiant de commande.")

    approve_url = ""
    for link in data.get("links") or []:
        if isinstance(link, dict) and link.get("rel") == "approve":
            approve_url = str(link.get("href") or "")
            break

    return {
        "paypal_order_id": paypal_order_id,
        "approve_url": approve_url,
        "paypal_amount": float(paypal_amount),
        "paypal_amount_text": _money(paypal_amount, config.currency),
        "paypal_currency": config.currency,
        "provider": "paypal",
        "environment": config.environment,
        "client_id": config.client_id,
    }


def capture_paypal_order(paypal_order_id: str) -> Dict[str, Any]:
    config = load_paypal_config()
    order_id = str(paypal_order_id or "").strip()
    if not order_id or not re_fullmatch_paypal_id(order_id):
        raise RuntimeError("Identifiant de commande PayPal invalide.")

    token = _get_access_token(config)
    response = requests.post(
        f"{config.base_url}/v2/checkout/orders/{order_id}/capture",
        headers=_paypal_headers(token, f"capture-{order_id}"),
        json={},
        timeout=30,
    )
    try:
        data = response.json()
    except Exception:
        data = {}

    if response.status_code >= 400:
        detail = data.get("message") or data.get("details") or response.text[:500]
        raise RuntimeError(f"Capture PayPal impossible : {detail}")

    status = str(data.get("status") or "").upper()
    purchase_units = data.get("purchase_units") or []
    capture = None
    if purchase_units:
        payments_block = (purchase_units[0] or {}).get("payments") or {}
        captures = payments_block.get("captures") or []
        if captures:
            capture = captures[0]

    amount = ((capture or {}).get("amount") or {}) if isinstance(capture, dict) else {}
    capture_id = str((capture or {}).get("id") or "").strip() if isinstance(capture, dict) else ""

    return {
        "paypal_order_id": order_id,
        "status": status,
        "capture_id": capture_id,
        "currency": str(amount.get("currency_code") or "").upper(),
        "amount": str(amount.get("value") or ""),
        "raw": data,
    }


def re_fullmatch_paypal_id(value: str) -> bool:
    # PayPal IDs sont alphanumériques avec quelques variations selon API.
    # On refuse tout slash/URL/CRLF avant de l'utiliser dans l'URL serveur.
    import re
    return bool(re.fullmatch(r"[A-Za-z0-9_-]{8,64}", value))


# Compatibilité avec l'ancienne couche paiement.
SUPPORTED_METHODS = {"paypal": "PayPal"}
CURRENT_PROVIDER = "paypal"


def create_payment(
    *,
    order_id: int,
    amount: float,
    currency: str,
    payment_method: str,
    customer_phone: str = "",
    customer_email: str = "",
) -> Dict[str, Any]:
    method = str(payment_method or "").strip().lower()
    if method != "paypal":
        return {
            "ok": False,
            "status": "failed",
            "reference": None,
            "checkout_url": None,
            "message": "Le seul moyen de paiement en ligne disponible est PayPal.",
        }
    try:
        result = create_paypal_order(
            order_id=order_id,
            amount=amount,
            local_currency=currency,
            customer_email=customer_email,
        )
        return {
            "ok": True,
            "status": "created",
            "reference": result["paypal_order_id"],
            "checkout_url": result["approve_url"],
            "message": "Commande PayPal créée. Autorisation client attendue.",
            "provider": "paypal",
            "payment_method": "paypal",
            **result,
        }
    except Exception as exc:
        return {
            "ok": False,
            "status": "failed",
            "reference": None,
            "checkout_url": None,
            "message": str(exc),
            "provider": "paypal",
            "payment_method": "paypal",
        }
