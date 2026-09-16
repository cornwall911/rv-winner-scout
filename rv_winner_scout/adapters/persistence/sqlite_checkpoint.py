"""SQLite implementation of checkpoint store, state machine persistence, and dead-letter quarantine."""

import json
import logging
import os
import shutil
import sqlite3
import time
from datetime import datetime, timezone
from typing import List, Optional, Set

from rv_winner_scout.config.settings import Settings, get_settings
from rv_winner_scout.domain.models import ProductCandidate
from rv_winner_scout.ports.checkpoint_port import CheckpointPort

logger = logging.getLogger(__name__)


class SQLiteCheckpointStore(CheckpointPort):
    """Stores product checkpoints and dead-letter logs in SQLite with self-healing recovery and JSON redundancy."""

    def __init__(self, db_path: Optional[str] = None, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        if db_path:
            self.db_path = db_path
        else:
            os.makedirs(self.settings.data_dir, exist_ok=True)
            self.db_path = os.path.join(self.settings.data_dir, "checkpoint.db")

        self.json_backup_path = os.path.join(
            os.path.dirname(self.db_path), "checkpoint_state.json"
        )
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            # Use DELETE journal mode so database is 100% self-contained in a single file
            conn.execute("PRAGMA journal_mode=DELETE;")
            conn.execute("PRAGMA synchronous=NORMAL;")
        except Exception:
            pass
        return conn

    from contextlib import contextmanager

    @contextmanager
    def _managed_conn(self):
        conn = self._get_conn()
        try:
            yield conn
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def _create_tables_on_conn(self, conn: sqlite3.Connection) -> None:
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

    def _recover_corrupted_db(self, exc: Exception) -> None:
        """Recovers from a malformed database by backing it up and creating a clean fresh one."""
        logger.warning(
            "Database at %s is malformed or corrupted (%s). Initiating automatic self-healing recovery...",
            self.db_path,
            exc,
        )
        try:
            if os.path.exists(self.db_path):
                corrupt_backup = f"{self.db_path}.corrupt.{int(time.time())}"
                shutil.move(self.db_path, corrupt_backup)
                for ext in ["-wal", "-shm", "-journal"]:
                    aux = f"{self.db_path}{ext}"
                    if os.path.exists(aux):
                        try:
                            os.remove(aux)
                        except Exception:
                            pass
                logger.info("Moved corrupted database to %s", corrupt_backup)
        except Exception as move_exc:
            logger.error("Failed to move corrupted database: %s", move_exc)

        # Recreate fresh DB and reload from json state if available
        try:
            with self._managed_conn() as conn:
                self._create_tables_on_conn(conn)
        except Exception as rec_exc:
            logger.error("Error creating fresh database after recovery: %s", rec_exc)

        self._restore_from_json_backup()

    def _init_db(self) -> None:
        try:
            with self._managed_conn() as conn:
                cur = conn.execute("PRAGMA quick_check;")
                res = cur.fetchone()
                if not res or res[0] != "ok":
                    raise sqlite3.DatabaseError(f"Quick check failed: {res}")
                self._create_tables_on_conn(conn)
        except (sqlite3.DatabaseError, sqlite3.OperationalError) as exc:
            self._recover_corrupted_db(exc)

    def _save_json_backup(self, asin: str, payload: str) -> None:
        """Maintains a lightweight JSON backup of candidates to prevent state loss."""
        try:
            state = {}
            if os.path.exists(self.json_backup_path):
                try:
                    with open(self.json_backup_path, "r", encoding="utf-8") as f:
                        state = json.load(f)
                except Exception:
                    state = {}
            state[asin] = payload
            tmp_path = f"{self.json_backup_path}.tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(state, f)
            os.replace(tmp_path, self.json_backup_path)
        except Exception as exc:
            logger.debug("Could not write json state backup: %s", exc)

    def _restore_from_json_backup(self) -> None:
        """Restores candidates from json backup into newly initialized database."""
        if not os.path.exists(self.json_backup_path):
            return
        try:
            with open(self.json_backup_path, "r", encoding="utf-8") as f:
                state = json.load(f)
            now_str = datetime.now(timezone.utc).isoformat()
            with self._managed_conn() as conn:
                for asin, payload in state.items():
                    try:
                        cand = ProductCandidate.model_validate_json(payload)
                        conn.execute(
                            """
                            INSERT OR REPLACE INTO candidates (asin, canonical_url, run_id, stage, data_json, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            (asin, cand.canonical_url, "restored", cand.lifecycle_stage.value, payload, now_str),
                        )
                    except Exception:
                        pass
                conn.commit()
            logger.info("Successfully restored %d candidates from JSON state backup into fresh SQLite DB.", len(state))
        except Exception as exc:
            logger.warning("Failed to restore from JSON state backup: %s", exc)

    def save_candidate(self, run_id: str, candidate: ProductCandidate) -> None:
        now_str = datetime.now(timezone.utc).isoformat()
        payload = candidate.model_dump_json()

        for attempt in range(2):
            try:
                with self._managed_conn() as conn:
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
                self._save_json_backup(candidate.asin, payload)
                return
            except (sqlite3.DatabaseError, sqlite3.OperationalError) as exc:
                if attempt == 0:
                    self._recover_corrupted_db(exc)
                else:
                    logger.error("Failed to save candidate %s after recovery: %s", candidate.asin, exc)

    def get_candidate(self, asin: str) -> Optional[ProductCandidate]:
        try:
            with self._managed_conn() as conn:
                cur = conn.execute("SELECT data_json FROM candidates WHERE asin = ?", (asin,))
                row = cur.fetchone()
                if row:
                    return ProductCandidate.model_validate_json(row["data_json"])
            return None
        except (sqlite3.DatabaseError, sqlite3.OperationalError) as exc:
            self._recover_corrupted_db(exc)
            return None

    def get_run_candidates(self, run_id: str) -> List[ProductCandidate]:
        candidates: List[ProductCandidate] = []
        try:
            with self._managed_conn() as conn:
                cur = conn.execute(
                    "SELECT data_json FROM candidates WHERE run_id = ? ORDER BY updated_at ASC",
                    (run_id,),
                )
                for row in cur.fetchall():
                    candidates.append(ProductCandidate.model_validate_json(row["data_json"]))
            return candidates
        except (sqlite3.DatabaseError, sqlite3.OperationalError) as exc:
            self._recover_corrupted_db(exc)
            return candidates

    def get_all_candidates(self) -> List[ProductCandidate]:
        candidates: List[ProductCandidate] = []
        try:
            with self._managed_conn() as conn:
                cur = conn.execute(
                    "SELECT data_json FROM candidates ORDER BY updated_at DESC"
                )
                for row in cur.fetchall():
                    try:
                        candidates.append(ProductCandidate.model_validate_json(row["data_json"]))
                    except Exception:
                        pass
            return candidates
        except (sqlite3.DatabaseError, sqlite3.OperationalError) as exc:
            self._recover_corrupted_db(exc)
            try:
                with self._managed_conn() as conn:
                    cur = conn.execute("SELECT data_json FROM candidates ORDER BY updated_at DESC")
                    for row in cur.fetchall():
                        try:
                            candidates.append(ProductCandidate.model_validate_json(row["data_json"]))
                        except Exception:
                            pass
            except Exception:
                pass
            return candidates

    def get_all_processed_asins(self, completed_only: bool = False) -> Set[str]:
        query = (
            "SELECT asin FROM candidates WHERE stage IN ('FINAL_WINNER', 'REJECTED', 'COMMITTED')"
            if completed_only
            else "SELECT asin FROM candidates"
        )
        try:
            with self._managed_conn() as conn:
                cur = conn.execute(query)
                return {row["asin"] for row in cur.fetchall()}
        except (sqlite3.DatabaseError, sqlite3.OperationalError) as exc:
            self._recover_corrupted_db(exc)
            try:
                with self._managed_conn() as conn:
                    cur = conn.execute(query)
                    return {row["asin"] for row in cur.fetchall()}
            except Exception:
                return set()

    def get_uncompleted_candidates(self) -> List[ProductCandidate]:
        try:
            with self._managed_conn() as conn:
                cur = conn.execute(
                    "SELECT data_json FROM candidates WHERE stage NOT IN ('FINAL_WINNER', 'REJECTED', 'COMMITTED')"
                )
                return [ProductCandidate.model_validate_json(row["data_json"]) for row in cur.fetchall()]
        except (sqlite3.DatabaseError, sqlite3.OperationalError) as exc:
            self._recover_corrupted_db(exc)
            return []

    def quarantine_candidate(self, asin: str, stage: str, error_detail: str) -> None:
        now_str = datetime.now(timezone.utc).isoformat()
        try:
            with self._managed_conn() as conn:
                conn.execute(
                    """
                    INSERT INTO dead_letter (asin, stage, error_detail, quarantined_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (asin, stage, error_detail, now_str),
                )
                conn.commit()
        except (sqlite3.DatabaseError, sqlite3.OperationalError) as exc:
            self._recover_corrupted_db(exc)

