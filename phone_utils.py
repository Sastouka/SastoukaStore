# -*- coding: utf-8 -*-
"""
SastoukaStore — utilitaires téléphone.
Normalisation générique compatible avec plusieurs pays.
"""
from __future__ import annotations

import re

_ALLOWED_PHONE_CHARS = re.compile(r"^[0-9\s().+\-/]+$")


def normalize_phone(value: object) -> str:
    """Nettoie un téléphone sans inventer de pays."""
    if value is None:
        return ""

    raw = str(value).strip()
    if not raw:
        return ""

    if not _ALLOWED_PHONE_CHARS.fullmatch(raw):
        return ""

    digits = re.sub(r"\D", "", raw)
    if not digits:
        return ""

    compact = re.sub(r"[\s().\-/]", "", raw)

    if compact.startswith("00") and len(digits) >= 3:
        return "+" + digits[2:]

    if compact.startswith("+"):
        return "+" + digits

    return digits


def phone_digits(value: object) -> str:
    """Retourne uniquement les chiffres."""
    return normalize_phone(value).lstrip("+")


def is_valid_phone(value: object, *, min_digits: int = 8, max_digits: int = 15) -> bool:
    """Validation internationale générique."""
    normalized = normalize_phone(value)
    digits = normalized.lstrip("+")
    return min_digits <= len(digits) <= max_digits


def validate_phone(value: object) -> tuple[bool, str]:
    """Retourne (ok, message)."""
    normalized = normalize_phone(value)
    if not normalized:
        return False, "Le numéro de téléphone est invalide."

    digits = normalized.lstrip("+")
    if not (8 <= len(digits) <= 15):
        return False, "Le numéro de téléphone doit contenir entre 8 et 15 chiffres."

    return True, normalized
