"""Test isolation: run the warehouse/dbt tests without touching real data.

The test suites build and tear down a full warehouse, so running them
against the real database or the real ``data/`` directory would wipe a
user's work. :func:`isolated_workspace` gives a test:

* a private temp directory for RAW_DIR / SILVER_DIR / FAILED_DIR /
  REPORT_DIR / MANIFEST_PATH, and
* a throwaway PostgreSQL database (``<dbname>_test``) created on entry and
  dropped on exit,

by overriding the relevant environment variables for the duration of the
``with`` block. Because :mod:`warehouse.config` reads the environment live,
the loader and any ``dbt`` subprocess automatically target the test DB.
"""
from __future__ import annotations

import contextlib
import os
import shutil
import tempfile

import psycopg2
from psycopg2 import sql

_WORKSPACE_VARS = ("RAW_DIR", "SILVER_DIR", "FAILED_DIR", "REPORT_DIR", "MANIFEST_PATH")


def _admin_connection():
    """Connect to the maintenance DB so we can create/drop the test DB."""
    params = {
        "host": os.getenv("PGHOST", "localhost"),
        "port": int(os.getenv("PGPORT", "5432")),
        "user": os.getenv("PGUSER", "jobmarket"),
        "dbname": "postgres",
    }
    password = os.getenv("PGPASSWORD", "jobmarket")
    if password:
        params["password"] = password
    conn = psycopg2.connect(**params)
    conn.autocommit = True
    return conn


def _drop_db(name: str) -> None:
    # CREATE/DROP DATABASE cannot run inside a transaction block, so we operate
    # in autocommit and avoid psycopg2's `with conn` (which opens a transaction).
    conn = _admin_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE datname = %s AND pid <> pg_backend_pid()",
            (name,),
        )
        cur.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(name)))
        cur.close()
    finally:
        conn.close()


def _create_db(name: str) -> None:
    conn = _admin_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
        cur.close()
    finally:
        conn.close()


@contextlib.contextmanager
def isolated_workspace(tag: str = "test"):
    """Context manager that isolates filesystem + database for a test run.

    Yields the temp workspace path. Restores all environment variables and
    removes the temp dir and test database on exit (even on failure).
    """
    base_db = os.getenv("PGDATABASE", "job_market_tracker")
    test_db = f"{base_db}_test"

    saved = {k: os.environ.get(k) for k in (*_WORKSPACE_VARS, "PGDATABASE")}
    workspace = tempfile.mkdtemp(prefix=f"jmt_{tag}_")

    os.environ["RAW_DIR"] = os.path.join(workspace, "raw")
    os.environ["SILVER_DIR"] = os.path.join(workspace, "silver")
    os.environ["FAILED_DIR"] = os.path.join(workspace, "failed")
    os.environ["REPORT_DIR"] = os.path.join(workspace, "reports")
    os.environ["MANIFEST_PATH"] = os.path.join(workspace, "meta", "manifest.json")
    os.environ["PGDATABASE"] = test_db

    _drop_db(test_db)   # in case a previous run crashed and left it behind
    _create_db(test_db)
    print(f"🧪 Isolated workspace: {workspace}\n🧪 Isolated database: {test_db}\n")
    try:
        yield workspace
    finally:
        with contextlib.suppress(Exception):
            _drop_db(test_db)
        shutil.rmtree(workspace, ignore_errors=True)
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        print(f"\n🧹 Tore down test database {test_db} and workspace.")
