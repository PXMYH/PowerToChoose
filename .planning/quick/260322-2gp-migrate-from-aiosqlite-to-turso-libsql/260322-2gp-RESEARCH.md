# Quick Task: Migrate aiosqlite to Turso (libSQL) - Research

**Researched:** 2026-03-22
**Domain:** Python libSQL/Turso client, database migration
**Confidence:** HIGH (verified by direct API testing)

## Summary

The `libsql` Python package (v0.1.11) provides a synchronous sqlite3-compatible API that supports all SQL features used in the current schema (AUTOINCREMENT, ON CONFLICT, CHECK constraints, foreign keys, PRAGMAs, CREATE INDEX IF NOT EXISTS, executescript). It connects to Turso via `sync_url` + `auth_token` params, or to a local SQLite file when those are omitted.

The main migration challenge is that **libsql has no async API** -- the current codebase uses `aiosqlite` (async). All database calls must either switch to synchronous or be wrapped with `asyncio.to_thread()`. The library also **lacks `row_factory`** -- dict-style row access must be implemented manually via `cursor.description`.

**Primary recommendation:** Use `libsql` (v0.1.11, the non-experimental package). Wrap sync calls in `asyncio.to_thread()` for FastAPI compatibility. Build a thin connection wrapper that provides dict-row support and local/remote switching based on env vars.

## Standard Stack

| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| libsql | 0.1.11 | Turso/libSQL Python client | Replaces aiosqlite. Sync-only API. |
| aiosqlite | 0.21.0 | Local dev fallback (KEEP) | Keep as optional fallback for local dev if preferred |

**Install:** `pip install libsql`

**Key decision:** Whether to keep aiosqlite for local dev or use libsql for both local and remote. libsql works fine with local SQLite files (`libsql.connect("path/to/db.db")`), so a single library approach is simpler.

**Recommendation:** Drop aiosqlite entirely. Use libsql for both local and Turso. One code path, fewer bugs.

## API Comparison: aiosqlite vs libsql

| Feature | aiosqlite | libsql | Migration Notes |
|---------|-----------|--------|-----------------|
| Connect | `await aiosqlite.connect(path)` | `libsql.connect(path)` or `libsql.connect(path, sync_url=url, auth_token=token)` | Sync, not async |
| Execute | `await db.execute(sql, params)` | `conn.execute(sql, params)` | Same params style (?) |
| Fetch one | `await cursor.fetchone()` | `cursor.fetchone()` | Returns tuple, not Row |
| Fetch all | `await cursor.fetchall()` | `cursor.fetchall()` | Returns list of tuples |
| executescript | `await db.executescript(sql)` | `conn.executescript(sql)` | Works identically |
| commit | `await db.commit()` | `conn.commit()` | Sync |
| row_factory | `db.row_factory = aiosqlite.Row` | **NOT SUPPORTED** | Must use cursor.description manually |
| Context manager | `async with aiosqlite.connect() as db:` | No async context manager | Use try/finally or sync context |
| PRAGMA | `await db.execute("PRAGMA ...")` | `conn.execute("PRAGMA ...")` | Works |
| Turso sync | N/A | `conn.sync()` | Call after writes to push to remote |

## SQL Feature Compatibility (Verified)

All features used in `schema.sql` are supported. Tested directly against libsql 0.1.11:

| Feature | Status | Verified |
|---------|--------|----------|
| AUTOINCREMENT | Works | YES |
| ON CONFLICT ... DO UPDATE | Works | YES |
| CHECK constraints | Enforced | YES |
| Foreign keys (PRAGMA foreign_keys) | Works | YES |
| CREATE INDEX IF NOT EXISTS | Works | YES |
| CREATE TABLE IF NOT EXISTS | Works | YES |
| datetime('now') defaults | Works | YES |
| executescript (multi-statement) | Works | YES |
| PRAGMA journal_mode | Works (returns 'memory' for :memory:) | YES |

## Architecture Pattern: Connection Wrapper

The current code uses `async with aiosqlite.connect()` throughout. Replace with a wrapper that:

1. Creates a libsql connection (local or Turso based on config)
2. Provides dict-row helper functions
3. Wraps sync calls for async FastAPI routes

### Config Changes (config.py)

```python
class Settings(BaseSettings):
    # ... existing fields ...
    DATABASE_PATH: str = "data/power2choose.db"
    TURSO_DATABASE_URL: str = ""   # libsql://your-db-name-org.turso.io
    TURSO_AUTH_TOKEN: str = ""     # Token from turso db tokens create
```

### Connection Pattern

```python
import libsql

def get_connection():
    """Create a libsql connection -- Turso if configured, local SQLite otherwise."""
    if settings.TURSO_DATABASE_URL:
        conn = libsql.connect(
            settings.DATABASE_PATH,  # local replica file
            sync_url=settings.TURSO_DATABASE_URL,
            auth_token=settings.TURSO_AUTH_TOKEN,
        )
        conn.sync()  # Pull latest from remote on connect
        return conn
    else:
        return libsql.connect(settings.DATABASE_PATH)
```

### Dict Row Helper

```python
def dict_fetchone(cursor):
    """Fetch one row as dict. Replaces aiosqlite.Row behavior."""
    row = cursor.fetchone()
    if row is None:
        return None
    cols = [d[0] for d in cursor.description]
    return dict(zip(cols, row))

def dict_fetchall(cursor):
    """Fetch all rows as dicts."""
    rows = cursor.fetchall()
    if not rows:
        return []
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in rows]
```

### Async Wrapping for FastAPI

Since libsql is synchronous and FastAPI route handlers are async:

```python
import asyncio

async def async_execute(func, *args, **kwargs):
    """Run sync database function in thread pool."""
    return await asyncio.to_thread(func, *args, **kwargs)
```

**Alternative:** Make all database functions synchronous and use FastAPI's `def` (non-async) route handlers or background task functions. FastAPI runs sync handlers in a thread pool automatically.

**Simpler approach:** Just make connection.py functions synchronous (remove `async def`, remove `await`). FastAPI will handle threading. This avoids the `asyncio.to_thread` wrapper entirely.

## Common Pitfalls

### 1. Forgetting conn.sync() After Writes
**What goes wrong:** Data written to local replica but never pushed to Turso remote.
**Prevention:** Call `conn.sync()` after every `conn.commit()` when using embedded replicas.

### 2. No row_factory -- Code Expects Dict Rows
**What goes wrong:** All code using `dict(row)` (where row was an aiosqlite.Row) breaks because libsql returns plain tuples.
**Prevention:** Replace all `dict(row)` patterns with `dict_fetchone(cursor)` / `dict_fetchall(cursor)` helpers.

### 3. Connection Lifecycle Difference
**What goes wrong:** aiosqlite connections are created per-request with `async with`. libsql connections are sync -- cannot use `async with`.
**Prevention:** Use regular `try/finally` or create connection in sync functions.

### 4. Turso URL Format
**What goes wrong:** Using `https://` instead of `libsql://` for the database URL.
**Correct format:** `libsql://your-db-name-org.turso.io`

### 5. Schema Push to Turso
**What goes wrong:** Turso DB is empty -- schema.sql must be applied to the remote database.
**Prevention:** Run `init_db()` once against Turso, or use Turso CLI: `turso db shell <dbname> < schema.sql`

## Migration Checklist

Files to modify:
1. **api/config.py** -- Add `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN` settings
2. **api/database/connection.py** -- Replace aiosqlite with libsql, add dict helpers, add sync()
3. **api/pyproject.toml** -- Replace `aiosqlite` with `libsql` in dependencies
4. **api/requirements.txt** -- Same replacement
5. **Any file importing from connection.py** -- Update async/await patterns if switching to sync

Pattern for each function in connection.py:
- Remove `async def` -> `def`
- Remove `await` before every db call
- Replace `aiosqlite.connect()` with `libsql.connect()`
- Replace `aiosqlite.Row` with dict helper functions
- Add `conn.sync()` after `conn.commit()` for Turso mode
- Replace `async with aiosqlite.connect() as db:` with `conn = get_connection(); try: ... finally: conn.close()`

## Open Questions

1. **Connection pooling** -- libsql docs don't mention connection pooling. For a small app this is fine (create per-request), but worth noting.
2. **Turso free tier limits** -- Check current Turso pricing. Free tier includes 9GB storage, 500 databases, 25M row reads/month as of early 2025. Verify current limits.
3. **Render deployment** -- libsql has wheels for Linux (manylinux) and macOS. Should work on Render (Linux). Verified: wheels exist for `manylinux` on PyPI.

## Sources

### Primary (HIGH confidence)
- Direct API testing of `libsql==0.1.11` on local machine -- all SQL features verified
- PyPI: libsql 0.1.11 (https://pypi.org/project/libsql/)
- PyPI: libsql-experimental 0.0.55 (https://pypi.org/project/libsql-experimental/)
- Turso Python quickstart (https://docs.turso.tech/sdk/python/quickstart)

### Notes
- `libsql-experimental` is the older package name; `libsql` (0.1.x) is the current one. Use `libsql`.
- Both packages have identical APIs. `libsql` is the recommended import going forward.
