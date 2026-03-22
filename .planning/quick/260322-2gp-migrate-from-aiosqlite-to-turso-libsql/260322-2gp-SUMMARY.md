# Quick Task 260322-2gp: Summary

## What was done
Migrated database layer from aiosqlite to libsql_experimental for Turso cloud persistence.

## Changes
- **api/database/connection.py** — Complete rewrite: libsql replaces aiosqlite. Sync libsql calls wrapped in asyncio.to_thread() to preserve async API. Added _dict_row/_dict_rows helpers (libsql has no row_factory). Added _commit_and_sync() for Turso push.
- **api/config.py** — Added TURSO_DATABASE_URL and TURSO_AUTH_TOKEN settings
- **api/pyproject.toml** — Replaced aiosqlite with libsql-experimental
- **api/requirements.txt** — Same replacement for Render

## How it works
- When `TURSO_DATABASE_URL` is set: connects to Turso with embedded replica (local file + remote sync)
- When not set: uses local SQLite file (same as before) — dev/test fallback
- All 51 tests pass without modification (async API preserved)

## User action needed
1. Create a Turso database: `turso db create power2choose`
2. Get the URL: `turso db show power2choose --url`
3. Create auth token: `turso db tokens create power2choose`
4. Set env vars on Render: TURSO_DATABASE_URL and TURSO_AUTH_TOKEN
