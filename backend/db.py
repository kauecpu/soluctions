"""
Camada de banco de dados (SQLite) para o programa de vagas de freelancer.

Guarda cada vaga com uma chave externa única (source + external_id) para
nunca duplicar a mesma vaga em buscas futuras.
"""
import sqlite3
import sys
import os
from pathlib import Path
from contextlib import contextmanager


def _default_db_path() -> Path:
    # Quando empacotado com PyInstaller, a pasta do executável pode ser
    # read-only (ex: montada por um instalador) ou mudar de lugar. Por isso
    # o banco fica numa pasta de dados do usuário, não ao lado do binário.
    if getattr(sys, "frozen", False):
        base = Path(os.path.expanduser("~")) / ".vagas-freelancer-dev"
        base.mkdir(parents=True, exist_ok=True)
        return base / "jobs.db"
    return Path(__file__).parent / "jobs.db"


DB_PATH = _default_db_path()

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    external_id TEXT NOT NULL,
    title TEXT NOT NULL,
    company TEXT,
    description TEXT,
    url TEXT NOT NULL,
    tags TEXT,
    budget TEXT,
    posted_at TEXT,
    found_at TEXT DEFAULT (datetime('now')),
    applied INTEGER NOT NULL DEFAULT 0,
    applied_at TEXT,
    UNIQUE(source, external_id)
);
"""


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.execute(SCHEMA)


def upsert_jobs(jobs: list[dict]) -> int:
    """Insere vagas novas, ignora as que já existem (mesma source+external_id).
    Retorna quantas vagas novas foram inseridas."""
    inserted = 0
    with get_conn() as conn:
        for job in jobs:
            cur = conn.execute(
                """
                INSERT OR IGNORE INTO jobs
                    (source, external_id, title, company, description, url, tags, budget, posted_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job["source"],
                    str(job["external_id"]),
                    job["title"],
                    job.get("company"),
                    job.get("description"),
                    job["url"],
                    job.get("tags"),
                    job.get("budget"),
                    job.get("posted_at"),
                ),
            )
            if cur.rowcount:
                inserted += 1
    return inserted


def list_jobs(keyword: str | None = None, applied: bool | None = None) -> list[dict]:
    query = "SELECT * FROM jobs WHERE 1=1"
    params: list = []
    if keyword:
        query += " AND (title LIKE ? OR description LIKE ? OR tags LIKE ?)"
        like = f"%{keyword}%"
        params += [like, like, like]
    if applied is not None:
        query += " AND applied = ?"
        params.append(1 if applied else 0)
    query += " ORDER BY found_at DESC"
    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def mark_applied(job_id: int) -> bool:
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE jobs SET applied = 1, applied_at = datetime('now') WHERE id = ?",
            (job_id,),
        )
        return cur.rowcount > 0
