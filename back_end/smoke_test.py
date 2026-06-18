"""
Smoke test script - exercises the new database + service code without
needing a running API server.

It verifies:
  1. DATABASE_URL parsing (Supabase direct + pooler).
  2. SQLAlchemy ORM models can be imported.
  3. Schema introspection (describe_database) returns the right tables.
  4. db_service.query_database returns sensible errors for invalid input
     and works when DATABASE_URL is configured.

Usage:
    python smoke_test.py
"""
import asyncio
import os
import sys
from urllib.parse import quote

# Load .env BEFORE importing anything from the app package so that
# settings.DATABASE_URL is populated and the SQLAlchemy engine can
# be created at import time.
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
except Exception as exc:
    print(f"WARN failed to load .env: {exc}")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_url_normalisation():
    from app.api.routers.db.sessions import _normalize_db_url

    pw = quote("p@ss:word/123", safe="")
    direct = _normalize_db_url(
        f"postgresql://postgres:{pw}@db.example.supabase.co:5432/postgres"
    )
    assert direct.startswith("postgresql+asyncpg://"), direct
    assert "db.example.supabase.co" in direct, direct

    pooler = _normalize_db_url(
        f"postgresql://postgres.{quote('proj')}:{pw}"
        f"@aws-0-us-east-1.pooler.supabase.com:6543/postgres"
    )
    assert pooler.startswith("postgresql+asyncpg://"), pooler
    assert "pooler.supabase.com" in pooler, pooler
    print("OK   url normalisation (direct + pooler)")


def test_schema_describe():
    from app.services.db_service import describe_database, ALLOWED_TABLES

    schema = describe_database()
    assert set(schema.keys()) == {"games", "users", "reviews"}, set(schema.keys())
    assert ALLOWED_TABLES == frozenset({"games", "users", "reviews"})
    for name in schema:
        assert schema[name]["columns"], f"empty columns for {name}"
    print("OK   schema describe")


def test_models_importable():
    from app.models import Game, Review, SteamUser
    from app.models import AppUser, Permission, Role, RolePermission, UserRole

    tables = {Game.__tablename__, Review.__tablename__, SteamUser.__tablename__}
    assert tables == {"games", "reviews", "users"}, tables
    print("OK   models import + table names")


def test_sample_data_bootstrap_local():
    from app.services.sample_data_service import register_local_sample
    from app.services.session_service import session_manager

    ok = register_local_sample()
    assert ok, "expected sample_timeseries.csv to be registered"
    assert "sample_timeseries.csv" in session_manager.tables
    meta = session_manager.tables["sample_timeseries.csv"]
    assert meta["source"] == "sample"
    assert meta["columns"], "expected column metadata to be extracted"
    print("OK   sample data bootstrap (local CSV)")


async def test_query_validation_rejects_unknown_table():
    from app.services.db_service import query_database

    result = await query_database(table="secret_data")
    assert result["success"] is False
    assert "secret_data" in result["error"]
    assert "Allowed tables" in result["error"]

    result = await query_database(table="")
    assert result["success"] is False
    print("OK   query_database rejects unknown tables")


async def test_sample_data_bootstrap_db():
    from app.services.sample_data_service import register_db_sample
    from app.services.session_service import session_manager

    ok = await register_db_sample()
    assert ok, "expected db.* virtual tables to be registered"
    for t in ("db.games", "db.users", "db.reviews"):
        assert t in session_manager.tables
        assert session_manager.tables[t]["source"] == "db"
    summary = session_manager.get_db_summary()
    if session_manager.is_db_available():
        assert summary, "summary should be populated when DB is reachable"
        assert "games" in summary
        print("OK   sample data bootstrap (db reachable)")
    else:
        print("OK   sample data bootstrap (db unreachable, summary cached empty)")


async def test_intro_endpoint_payload():
    from app.services.db_service import describe_database, get_database_overview
    from app.services.sample_data_service import LOCAL_SAMPLE_NAME

    db_overview = await get_database_overview()
    db_schema = describe_database()

    payload = {
        "intro": {
            "title": "Steam Game Data Analyst",
            "tagline": "test tagline",
            "system_notes": [],
            "how_to_use": [],
            "future_work": [],
        },
        "sample_data": {
            "local": {"name": LOCAL_SAMPLE_NAME, "title": "t", "description": "d",
                       "columns": [], "kind": "timeseries"},
            "database": {
                "title": "db",
                "description": "d",
                "tables": [],
                "row_counts": db_overview.get("counts", {}),
                "available": db_overview.get("available", False),
                "columns": {
                    name: [c["name"] for c in info["columns"]]
                    for name, info in db_schema.items()
                },
                "error": db_overview.get("error"),
            },
        },
    }
    assert payload["sample_data"]["database"]["columns"]["games"], "games columns missing"
    print("OK   intro payload shape")


async def main():
    test_url_normalisation()
    test_schema_describe()
    test_models_importable()
    test_sample_data_bootstrap_local()
    await test_query_validation_rejects_unknown_table()
    await test_sample_data_bootstrap_db()
    await test_intro_endpoint_payload()
    print("\nAll smoke tests passed.")


if __name__ == "__main__":
    asyncio.run(main())
