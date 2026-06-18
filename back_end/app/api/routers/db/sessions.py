"""
Database Session - PostgreSQL (Supabase).

Optimised for free-tier (1GB RAM).

Schema: public (per SCHEMA_DOCUMENTATION.md).

Supports both:
  - Direct connection:   postgresql://...@db.xxx.supabase.co:5432/postgres
  - Supabase Pooler:     postgresql://...@aws-0-xxx.pooler.supabase.com:6543/postgres
                         (Transaction mode - disables prepared statements to be safe)
"""
import time
from typing import Any, AsyncGenerator, Dict
from urllib.parse import quote, urlparse, urlunparse

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings


def _normalize_db_url(raw_url: str) -> str:
    """
    Normalise the DATABASE_URL so it can be safely fed into asyncpg.

    Operations performed (in order):
      1. Strip leading "DATABASE_URL=" duplicates (in case the user pasted it twice).
      2. Convert "postgresql://" -> "postgresql+asyncpg://" so SQLAlchemy uses asyncpg.
      3. URL-encode the password component so special characters like @,
         : / ? # [ ] % are safe.
      4. Strip any query string (asyncpg accepts connect_args for SSL instead).

    The returned URL is always safe to pass to `create_async_engine`.
    """
    if not raw_url:
        return raw_url

    # 1) Handle duplicated prefix (defensive).
    url = raw_url.strip()
    while url.startswith("DATABASE_URL="):
        url = url[len("DATABASE_URL="):].lstrip()

    # 2) Translate scheme.
    if url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://"):]
    elif url.startswith("postgres://"):
        url = "postgresql+asyncpg://" + url[len("postgres://"):]

    # 3) Encode password.
    parsed = urlparse(url)
    if parsed.password:
        encoded_pw = quote(parsed.password, safe="")
        userinfo = ""
        if parsed.username:
            userinfo = quote(parsed.username, safe="")
        if encoded_pw:
            userinfo = f"{userinfo}:{encoded_pw}" if userinfo else f":{encoded_pw}"
        netloc = parsed.hostname or ""
        if parsed.port:
            netloc = f"{netloc}:{parsed.port}"
        new_netloc = f"{userinfo}@{netloc}" if userinfo else netloc
        url = urlunparse(parsed._replace(netloc=new_netloc))

    # 4) Strip query (asyncpg takes ssl via connect_args).
    parsed = urlparse(url)
    if parsed.query:
        url = urlunparse(parsed._replace(query=""))

    return url


# ============== PostgreSQL (Async) ==============
_db_url = _normalize_db_url(settings.DATABASE_URL)

_POOL_SIZE = min(settings.DB_POOL_SIZE, 5)
_MAX_OVERFLOW = min(settings.DB_MAX_OVERFLOW, 10)

# Short timeouts so connection failures fail fast on Render free-tier
# (otherwise the response hangs for 30+ s and the user sees nothing).
_CONNECT_TIMEOUT_SECONDS = 5
_STATEMENT_TIMEOUT_MS = 30_000

_connect_args: dict = {
    "timeout": _CONNECT_TIMEOUT_SECONDS,
    "server_settings": {
        "application_name": "steam-game-api",
        "statement_timeout": str(_STATEMENT_TIMEOUT_MS),
        "lock_timeout": "10000",
    },
}

# Detect Supabase pooler (Transaction mode on port 6543). asyncpg's prepared
# statement cache breaks in Transaction mode pooler -> disable it.
_is_pooler = (
    "pooler.supabase.com" in _db_url
    or ":6543" in _db_url
)
if _is_pooler:
    _connect_args["prepared_statement_cache_size"] = 0
    _connect_args["statement_cache_size"] = 0

# Supabase requires SSL; pass a TLS context via connect_args.
import ssl as _ssl

_ssl_ctx = _ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = _ssl.CERT_NONE
_connect_args["ssl"] = _ssl_ctx

async_engine = create_async_engine(
    _db_url,
    echo=settings.DEBUG,
    pool_size=_POOL_SIZE,
    max_overflow=_MAX_OVERFLOW,
    pool_pre_ping=True,
    pool_recycle=1800,
    future=True,
    connect_args=_connect_args,
)

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


# ---------------------------------------------------------------------------
# In-memory cache for the lightweight database overview used by /api/status
# and /api/intro. Caching prevents the per-poll count queries from spamming
# the log with [Errno 101] warnings when the database is briefly
# unreachable.
# ---------------------------------------------------------------------------
_OVERVIEW_CACHE: Dict[str, Any] = {
    "payload": None,
    "expires_at": 0.0,
    "min_interval": 0.0,
    "last_attempt_at": 0.0,
    "last_failure_at": 0.0,
    "consecutive_failures": 0,
}
_OVERVIEW_TTL_SECONDS = 30.0       # fresh data lives 30s
_OVERVIEW_FAILURE_BACKOFF = 60.0  # if it failed, don't retry for 60s


async def get_db_overview_cached() -> Dict[str, Any]:
    """
    Return the latest database overview, fetching it from Supabase at
    most once every 30 seconds (or once every 60 seconds if the
    previous attempt failed). This protects the log from spam when
    the database is unreachable.
    """
    from app.services.db_service import get_database_overview

    now = time.time()
    cached = _OVERVIEW_CACHE["payload"]
    expires = _OVERVIEW_CACHE["expires_at"]
    if cached is not None and now < expires:
        return cached

    # Throttle attempts so we don't hammer the database when it's down.
    if now - _OVERVIEW_CACHE["last_attempt_at"] < _OVERVIEW_CACHE["min_interval"]:
        return cached or {"available": False, "counts": {}, "error": "throttled"}

    _OVERVIEW_CACHE["last_attempt_at"] = now
    result = await get_database_overview()

    if result.get("available"):
        _OVERVIEW_CACHE["payload"] = result
        _OVERVIEW_CACHE["expires_at"] = now + _OVERVIEW_TTL_SECONDS
        _OVERVIEW_CACHE["min_interval"] = 0.0
        _OVERVIEW_CACHE["consecutive_failures"] = 0
    else:
        # Back off aggressively so we do not flood the log.
        _OVERVIEW_CACHE["payload"] = result
        _OVERVIEW_CACHE["expires_at"] = now + _OVERVIEW_FAILURE_BACKOFF
        _OVERVIEW_CACHE["min_interval"] = _OVERVIEW_FAILURE_BACKOFF
        _OVERVIEW_CACHE["consecutive_failures"] += 1
        # Only log the FIRST failure and then every 10th to avoid spam.
        if _OVERVIEW_CACHE["consecutive_failures"] == 1 or _OVERVIEW_CACHE["consecutive_failures"] % 10 == 0:
            import logging
            logging.getLogger(__name__).warning(
                "Database overview unavailable (failures=%d): %s",
                _OVERVIEW_CACHE["consecutive_failures"],
                result.get("error") or "unknown",
            )

    return result


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency providing a database session for each request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_db_connection() -> bool:
    """
    Verify that the database is reachable. Returns True if a simple
    SELECT 1 succeeds within a few seconds; False otherwise.

    Used by the /health endpoint. Cached for a few seconds to avoid
    hammering the database on health-check polls.
    """
    import logging
    from sqlalchemy import text

    now = time.time()
    if now - _OVERVIEW_CACHE["last_attempt_at"] < 2.0 and _OVERVIEW_CACHE["payload"] is not None:
        return bool(_OVERVIEW_CACHE["payload"].get("available"))
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        # Down-grade to debug so the health check does not spam the log.
        logging.getLogger(__name__).debug("DB ping failed: %s", exc)
        return False


async def init_db() -> None:
    """
    Initialise the database - create tables if they do not exist (dev/test only).
    In production, use db_extra_tables.sql + db_init_supabase.sql.
    """
    from app.db.base import Base  # noqa: F401
    from app.models import steam, user  # noqa: F401

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database connection on app shutdown."""
    await async_engine.dispose()
