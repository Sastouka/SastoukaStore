# -*- coding: utf-8 -*-
"""
SastoukaStore — migrations SQLite versionnées
PATCH 6.1 : réparation des anciens schémas.

Important :
CREATE TABLE IF NOT EXISTS ne modifie PAS une table déjà existante.
Cette version ajoute donc explicitement les colonnes manquantes des tables
historiques avant de créer les index.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Callable

SastoukaStore_ICON_PATH_6_6 = Path(__file__).resolve().parent / "static" / "icons" / "sastoukastore-icon.png"

MIGRATIONS_TABLE = "schema_migrations"


def connect(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, timeout=30.0)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    con.execute("PRAGMA busy_timeout=30000")
    return con


def table_exists(con: sqlite3.Connection, table: str) -> bool:
    return con.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone() is not None


def columns(con: sqlite3.Connection, table: str) -> set[str]:
    if not table_exists(con, table):
        return set()
    return {row["name"] for row in con.execute(f"PRAGMA table_info({table})")}


def add_column_if_missing(
    con: sqlite3.Connection,
    table: str,
    column: str,
    definition: str,
) -> bool:
    if column in columns(con, table):
        return False
    con.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
    return True


def ensure_core_columns(con: sqlite3.Connection) -> None:
    """
    Répare les anciennes tables existantes sans les supprimer.

    Les DEFAULT utilisés ici sont constants, compatibles avec
    ALTER TABLE ... ADD COLUMN SQLite.
    """
    if table_exists(con, "settings"):
        for col, definition in [
            ("shop_name", "TEXT DEFAULT 'SastoukaStore'"),
            ("currency", "TEXT DEFAULT 'FCFA'"),
            ("whatsapp", "TEXT DEFAULT ''"),
            ("created_at", "TEXT DEFAULT ''"),
        ]:
            add_column_if_missing(con, "settings", col, definition)

    if table_exists(con, "categories"):
        for col, definition in [
            ("name", "TEXT DEFAULT ''"),
            ("slug", "TEXT DEFAULT ''"),
            ("active", "INTEGER NOT NULL DEFAULT 1"),
        ]:
            add_column_if_missing(con, "categories", col, definition)

    if table_exists(con, "products"):
        for col, definition in [
            ("category_id", "INTEGER"),
            ("name", "TEXT DEFAULT ''"),
            ("slug", "TEXT DEFAULT ''"),
            ("description", "TEXT DEFAULT ''"),
            ("price", "REAL NOT NULL DEFAULT 0"),
            ("image", "TEXT DEFAULT ''"),
            ("stock", "INTEGER NOT NULL DEFAULT 0"),
            ("active", "INTEGER NOT NULL DEFAULT 1"),
            ("created_at", "TEXT DEFAULT ''"),
        ]:
            add_column_if_missing(con, "products", col, definition)

    if table_exists(con, "customers"):
        for col, definition in [
            ("name", "TEXT DEFAULT ''"),
            ("phone", "TEXT DEFAULT ''"),
            ("email", "TEXT DEFAULT ''"),
            ("address", "TEXT DEFAULT ''"),
            ("city", "TEXT DEFAULT ''"),
            ("visitor_id", "TEXT UNIQUE"),
            ("created_at", "TEXT DEFAULT ''"),
        ]:
            add_column_if_missing(con, "customers", col, definition)

    if table_exists(con, "orders"):
        for col, definition in [
            ("customer_id", "INTEGER"),
            ("total", "REAL NOT NULL DEFAULT 0"),
            ("payment_method", "TEXT DEFAULT 'cash_delivery'"),
            ("payment_status", "TEXT DEFAULT 'pending'"),
            ("delivery_status", "TEXT DEFAULT 'pending'"),
            ("notes", "TEXT DEFAULT ''"),
            ("created_at", "TEXT DEFAULT ''"),
        ]:
            add_column_if_missing(con, "orders", col, definition)

    if table_exists(con, "order_items"):
        for col, definition in [
            ("order_id", "INTEGER"),
            ("product_id", "INTEGER"),
            ("product_name", "TEXT DEFAULT ''"),
            ("unit_price", "REAL NOT NULL DEFAULT 0"),
            ("quantity", "INTEGER NOT NULL DEFAULT 1"),
            ("subtotal", "REAL NOT NULL DEFAULT 0"),
            ("variant", "TEXT DEFAULT ''"),
            ("created_at", "TEXT DEFAULT ''"),
        ]:
            add_column_if_missing(con, "order_items", col, definition)

    if table_exists(con, "product_variants"):
        for col, definition in [
            ("product_id", "INTEGER"),
            ("name", "TEXT DEFAULT ''"),
            ("value", "TEXT DEFAULT ''"),
            ("sku", "TEXT DEFAULT ''"),
            ("price_delta", "REAL NOT NULL DEFAULT 0"),
            ("stock", "INTEGER NOT NULL DEFAULT 0"),
            ("active", "INTEGER NOT NULL DEFAULT 1"),
            ("created_at", "TEXT DEFAULT ''"),
        ]:
            add_column_if_missing(con, "product_variants", col, definition)


def migration_1_core_schema(con) -> None:
    con.executescript("""
    CREATE TABLE IF NOT EXISTS settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        shop_name TEXT NOT NULL DEFAULT 'SastoukaStore',
        currency TEXT NOT NULL DEFAULT 'FCFA',
        whatsapp TEXT DEFAULT '',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        slug TEXT UNIQUE NOT NULL,
        active INTEGER NOT NULL DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category_id INTEGER,
        name TEXT NOT NULL,
        slug TEXT UNIQUE NOT NULL,
        description TEXT DEFAULT '',
        price REAL NOT NULL DEFAULT 0,
        image TEXT DEFAULT '',
        stock INTEGER NOT NULL DEFAULT 0,
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(category_id) REFERENCES categories(id)
    );

    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT NOT NULL,
        email TEXT DEFAULT '',
        address TEXT DEFAULT '',
        city TEXT DEFAULT '',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        total REAL NOT NULL DEFAULT 0,
        payment_method TEXT DEFAULT 'cash_delivery',
        payment_status TEXT DEFAULT 'pending',
        delivery_status TEXT DEFAULT 'pending',
        notes TEXT DEFAULT '',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(customer_id) REFERENCES customers(id)
    );

    CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        product_name TEXT NOT NULL DEFAULT '',
        unit_price REAL NOT NULL DEFAULT 0,
        quantity INTEGER NOT NULL DEFAULT 1,
        subtotal REAL NOT NULL DEFAULT 0,
        variant TEXT DEFAULT '',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(order_id) REFERENCES orders(id)
    );

    CREATE TABLE IF NOT EXISTS product_variants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        value TEXT NOT NULL,
        sku TEXT DEFAULT '',
        price_delta REAL NOT NULL DEFAULT 0,
        stock INTEGER NOT NULL DEFAULT 0,
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(product_id) REFERENCES products(id)
    );
    """)

    # CRITIQUE : répare les tables déjà présentes.
    ensure_core_columns(con)


def migration_2_digital_catalog(con) -> None:
    if not table_exists(con, "products"):
        return
    for name, definition in [
        ("product_type", "TEXT DEFAULT 'digital'"),
        ("pdf_file", "TEXT DEFAULT ''"),
        ("currency", "TEXT DEFAULT 'FCFA'"),
        ("level", "TEXT DEFAULT ''"),
        ("subject", "TEXT DEFAULT ''"),
        ("short_description", "TEXT DEFAULT ''"),
        ("featured", "INTEGER NOT NULL DEFAULT 0"),
    ]:
        add_column_if_missing(con, "products", name, definition)


def migration_3_order_snapshot_and_variants(con) -> None:
    # Réparation des tables existantes + colonnes de commande.
    ensure_core_columns(con)


def migration_4_payment(con) -> None:
    con.execute("""
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
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(order_id)
    )
    """)


def _create_index_if_possible(
    con: sqlite3.Connection,
    index_name: str,
    table: str,
    expression: str,
) -> bool:
    if not table_exists(con, table):
        return False

    # Sécurité supplémentaire : toutes les colonnes de l'expression doivent
    # être présentes. On extrait les noms simples utilisés par nos index.
    table_cols = columns(con, table)
    for token in ("category_id", "active", "id", "phone", "customer_id",
                  "payment_status", "delivery_status", "order_id",
                  "product_id", "reference"):
        if token in expression and token not in table_cols:
            return False

    con.execute(
        f"CREATE INDEX IF NOT EXISTS {index_name} ON {table}({expression})"
    )
    return True


def migration_5_indexes_and_integrity(con) -> None:
    # Ne jamais échouer simplement parce qu'une vieille table a une structure
    # différente : on répare d'abord, puis on indexe ce qui existe.
    ensure_core_columns(con)

    indexes = [
        ("idx_products_category_active", "products", "category_id, active"),
        ("idx_products_active_created", "products", "active, id DESC"),
        ("idx_customers_phone", "customers", "phone"),
        ("idx_orders_customer_created", "orders", "customer_id, id DESC"),
        ("idx_orders_payment_status", "orders", "payment_status"),
        ("idx_orders_delivery_status", "orders", "delivery_status"),
        ("idx_order_items_order", "order_items", "order_id"),
        ("idx_order_items_product", "order_items", "product_id"),
        ("idx_variants_product_active", "product_variants", "product_id, active"),
        ("idx_payment_intents_status", "payment_intents", "status"),
        ("idx_payment_intents_reference", "payment_intents", "reference"),
    ]

    for index_name, table, expression in indexes:
        _create_index_if_possible(con, index_name, table, expression)

    con.execute("""
    CREATE TABLE IF NOT EXISTS db_meta (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL DEFAULT ''
    )
    """)
    con.execute("""
    INSERT INTO db_meta(key, value)
    VALUES('application', 'SastoukaStore')
    ON CONFLICT(key) DO UPDATE SET value=excluded.value
    """)


def migration_6_legacy_repair(con) -> None:
    """
    Garde-fou pour une base qui aurait déjà enregistré les anciennes
    migrations avec un schéma partiellement ancien.
    """
    ensure_core_columns(con)
    migration_2_digital_catalog(con)
    migration_4_payment(con)
    migration_5_indexes_and_integrity(con)


MIGRATIONS: list[tuple[int, str, Callable]] = [
    (1, "core_schema", migration_1_core_schema),
    (2, "digital_catalog", migration_2_digital_catalog),
    (3, "order_snapshot_and_variants", migration_3_order_snapshot_and_variants),
    (4, "payment_layer", migration_4_payment),
    (5, "indexes_and_integrity", migration_5_indexes_and_integrity),
    (6, "legacy_schema_repair", migration_6_legacy_repair),
]


def ensure_migrations_table(con) -> None:
    con.execute(f"""
    CREATE TABLE IF NOT EXISTS {MIGRATIONS_TABLE} (
        version INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """)


def run_migrations(db_path: str | Path) -> list[str]:
    con = connect(db_path)
    applied = []
    try:
        ensure_migrations_table(con)

        for version, name, fn in MIGRATIONS:
            row = con.execute(
                f"SELECT version FROM {MIGRATIONS_TABLE} WHERE version=?",
                (version,),
            ).fetchone()
            if row:
                continue

            try:
                fn(con)
                con.execute(
                    f"INSERT INTO {MIGRATIONS_TABLE}(version, name) VALUES(?, ?)",
                    (version, name),
                )
                con.commit()
                applied.append(f"{version}:{name}")
            except Exception:
                con.rollback()
                raise

        return applied
    finally:
        con.close()


def schema_status(db_path: str | Path) -> dict:
    con = connect(db_path)
    try:
        ensure_migrations_table(con)
        rows = con.execute(
            f"SELECT version, name, applied_at FROM {MIGRATIONS_TABLE} ORDER BY version"
        ).fetchall()
        return {
            "db": str(Path(db_path)),
            "applied": [dict(r) for r in rows],
        }
    finally:
        con.close()
