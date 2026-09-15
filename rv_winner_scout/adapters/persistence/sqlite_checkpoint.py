"""SQLite implementation of checkpoint store, state machine persistence, and dead-letter quarantine."""

import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import List, Optional

from rv_winner_scout.config.settings import Settings, get_settings
from rv_winner_scout.domain.models import ProductCandidate
from rv_winner_scout.ports.checkpoint_port import CheckpointPort


class SQLiteCheckpointStore(CheckpointPort):
    """Stores product checkpoints and dead-letter logs in SQLite."""

    def __init__(self, db_path: Optional[str] = None, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        if db_path:
            self.db_path = db_path
        else:
            os.makedirs(self.settings.data_dir, exist_ok=True)
            self.db_path = os.path.join(self.settings.data_dir, "checkpoint.db")

        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
        except Exception:
            pass
        return conn

    def _init_db(self) -> None:
        with self._get_conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS candidates (
                    asin TEXT PRIMARY KEY,
                    canonical_url TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    data_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS dead_letter (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    asin TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    error_detail TEXT NOT NULL,
                    quarantined_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def save_candidate(self, run_id: str, candidate: ProductCandidate) -> None:
        now_str = datetime.now(timezone.utc).isoformat()
        payload = candidate.model_dump_json()
        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT INTO candidates (asin, canonical_url, run_id, stage, data_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(asin) DO UPDATE SET
                    run_id=excluded.run_id,
                    stage=excluded.stage,
                    data_json=excluded.data_json,
                    updated_at=excluded.updated_at
                """,
                (
                    candidate.asin,
                    candidate.canonical_url,
                    run_id,
                    candidate.lifecycle_stage.value,
                    payload,
                    now_str,
                ),
            )
            conn.commit()

    def get_candidate(self, asin: str) -> Optional[ProductCandidate]:
        with self._get_conn() as conn:
            cur = conn.execute("SELECT data_json FROM candidates WHERE asin = ?", (asin,))
            row = cur.fetchone()
            if row:
                return ProductCandidate.model_validate_json(row["data_json"])
        return None

    def get_run_candidates(self, run_id: str) -> List[ProductCandidate]:
        candidates: List[ProductCandidate] = []
        with self._get_conn() as conn:
            cur = conn.execute(
                "SELECT data_json FROM candidates WHERE run_id = ? ORDER BY updated_at ASC",
                (run_id,),
            )
            for row in cur.fetchall():
                candidates.append(ProductCandidate.model_validate_json(row["data_json"]))
        return candidates

    def get_all_candidates(self) -> List[ProductCandidate]:
        candidates: List[ProductCandidate] = []
        with self._get_conn() as conn:
            cur = conn.execute(
                "SELECT data_json FROM candidates ORDER BY updated_at DESC"
            )
            for row in cur.fetchall():
                try:
                    candidates.append(ProductCandidate.model_validate_json(row["data_json"]))
                except Exception:
                    pass
        return candidates

    def get_all_processed_asins(self, completed_only: bool = False) -> set[str]:
        query = (
            "SELECT asin FROM candidates WHERE stage IN ('FINAL_WINNER', 'REJECTED', 'COMMITTED')"
            if completed_only
            else "SELECT asin FROM candidates"
        )
        with self._get_conn() as conn:
            cur = conn.execute(query)
            return {row["asin"] for row in cur.fetchall()}

    def get_uncompleted_candidates(self) -> List[ProductCandidate]:
        with self._get_conn() as conn:
            cur = conn.execute(
                "SELECT data_json FROM candidates WHERE stage NOT IN ('FINAL_WINNER', 'REJECTED', 'COMMITTED')"
            )
            return [ProductCandidate.model_validate_json(row["data_json"]) for row in cur.fetchall()]

    def quarantine_candidate(self, asin: str, stage: str, error_detail: str) -> None:
        now_str = datetime.now(timezone.utc).isoformat()
        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT INTO dead_letter (asin, stage, error_detail, quarantined_at)
                VALUES (?, ?, ?, ?)
                """,
                (asin, stage, error_detail, now_str),
            )
            conn.commit()
