"""
database.py — SQLite persistence layer.

Provides initialisation, CRUD helpers, and query functions for all
six tables used by the application. Uses only the standard library
(sqlite3) so there is no ORM dependency.
"""

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import config

logger = logging.getLogger(__name__)


# ======================================================================= #
#  Schema DDL
# ======================================================================= #

DDL = """
-- ------------------------------------------------------------------ --
-- runs: one row per user-initiated generation run
-- ------------------------------------------------------------------ --
CREATE TABLE IF NOT EXISTS runs (
    id              TEXT PRIMARY KEY,
    topic           TEXT NOT NULL,
    learner_level   TEXT NOT NULL DEFAULT 'Beginner',
    status          TEXT NOT NULL DEFAULT 'IN_PROGRESS',
    retry_count     INTEGER NOT NULL DEFAULT 0,
    final_status    TEXT,
    created_at      TEXT NOT NULL,
    completed_at    TEXT
);

-- ------------------------------------------------------------------ --
-- generations: one row per lesson generation attempt within a run
-- ------------------------------------------------------------------ --
CREATE TABLE IF NOT EXISTS generations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          TEXT NOT NULL REFERENCES runs(id),
    attempt_number  INTEGER NOT NULL,
    title           TEXT,
    content         TEXT NOT NULL,
    word_count      INTEGER,
    created_at      TEXT NOT NULL
);

-- ------------------------------------------------------------------ --
-- evaluations: one row per evaluation (tied to a generation attempt)
-- ------------------------------------------------------------------ --
CREATE TABLE IF NOT EXISTS evaluations (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id                  TEXT NOT NULL REFERENCES runs(id),
    attempt_number          INTEGER NOT NULL,
    overall_status          TEXT NOT NULL,
    criteria_json           TEXT NOT NULL,   -- JSON array of CriterionResult
    failed_criteria_json    TEXT NOT NULL,   -- JSON array of strings
    regen_instructions_json TEXT NOT NULL,   -- JSON array of strings
    evaluated_at            TEXT NOT NULL
);

-- ------------------------------------------------------------------ --
-- rejection_logs: human-readable rejection records
-- ------------------------------------------------------------------ --
CREATE TABLE IF NOT EXISTS rejection_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          TEXT NOT NULL REFERENCES runs(id),
    attempt_number  INTEGER NOT NULL,
    topic           TEXT NOT NULL,
    failed_criteria TEXT NOT NULL,   -- comma-separated
    reasons_json    TEXT NOT NULL,   -- JSON array
    suggestions_json TEXT NOT NULL,  -- JSON array
    rejected_at     TEXT NOT NULL
);

-- ------------------------------------------------------------------ --
-- memory_patterns: aggregated failure patterns for self-improvement
-- ------------------------------------------------------------------ --
CREATE TABLE IF NOT EXISTS memory_patterns (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    criterion           TEXT NOT NULL UNIQUE,
    failure_count       INTEGER NOT NULL DEFAULT 0,
    last_seen           TEXT NOT NULL,
    common_reasons_json TEXT NOT NULL DEFAULT '[]',
    suggested_improvement TEXT NOT NULL DEFAULT ''
);

-- ------------------------------------------------------------------ --
-- prompt_improvements: approved generator instruction upgrades
-- ------------------------------------------------------------------ --
CREATE TABLE IF NOT EXISTS prompt_improvements (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    criterion               TEXT NOT NULL,
    improvement_instruction TEXT NOT NULL,
    approved_at             TEXT NOT NULL,
    times_applied           INTEGER NOT NULL DEFAULT 0
);
"""


def _now() -> str:
    return datetime.utcnow().isoformat()


def get_connection() -> sqlite3.Connection:
    """Return a SQLite connection with row_factory set to Row."""
    db_path = Path(config.DATABASE_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db() -> None:
    """Create all tables if they do not already exist."""
    with get_connection() as conn:
        conn.executescript(DDL)
    logger.info("Database initialised at %s", config.DATABASE_PATH)


# ======================================================================= #
#  Run helpers
# ======================================================================= #

def create_run(run_id: str, topic: str, learner_level: str = "Beginner") -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO runs (id, topic, learner_level, status, created_at) VALUES (?,?,?,?,?)",
            (run_id, topic, learner_level, "IN_PROGRESS", _now()),
        )


def update_run_status(run_id: str, status: str, retry_count: int = 0) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE runs SET status=?, final_status=?, retry_count=?, completed_at=? WHERE id=?",
            (status, status, retry_count, _now(), run_id),
        )


def get_run(run_id: str) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        return dict(row) if row else None


def get_all_runs() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM runs ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]


# ======================================================================= #
#  Generation helpers
# ======================================================================= #

def save_generation(
    run_id: str,
    attempt_number: int,
    title: str,
    content: str,
    word_count: int,
) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO generations (run_id, attempt_number, title, content, word_count, created_at) VALUES (?,?,?,?,?,?)",
            (run_id, attempt_number, title, content, word_count, _now()),
        )
        return cur.lastrowid  # type: ignore[return-value]


def get_generations_for_run(run_id: str) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM generations WHERE run_id=? ORDER BY attempt_number",
            (run_id,),
        ).fetchall()
        return [dict(r) for r in rows]


# ======================================================================= #
#  Evaluation helpers
# ======================================================================= #

def save_evaluation(
    run_id: str,
    attempt_number: int,
    overall_status: str,
    criteria: List[Dict],
    failed_criteria: List[str],
    regen_instructions: List[str],
) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO evaluations
               (run_id, attempt_number, overall_status, criteria_json,
                failed_criteria_json, regen_instructions_json, evaluated_at)
               VALUES (?,?,?,?,?,?,?)""",
            (
                run_id,
                attempt_number,
                overall_status,
                json.dumps(criteria),
                json.dumps(failed_criteria),
                json.dumps(regen_instructions),
                _now(),
            ),
        )
        return cur.lastrowid  # type: ignore[return-value]


def get_evaluations_for_run(run_id: str) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM evaluations WHERE run_id=? ORDER BY attempt_number",
            (run_id,),
        ).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["criteria_json"] = json.loads(d["criteria_json"])
            d["failed_criteria_json"] = json.loads(d["failed_criteria_json"])
            d["regen_instructions_json"] = json.loads(d["regen_instructions_json"])
            results.append(d)
        return results


# ======================================================================= #
#  Rejection log helpers
# ======================================================================= #

def save_rejection(
    run_id: str,
    attempt_number: int,
    topic: str,
    failed_criteria: List[str],
    reasons: List[str],
    suggestions: List[str],
) -> None:
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO rejection_logs
               (run_id, attempt_number, topic, failed_criteria, reasons_json, suggestions_json, rejected_at)
               VALUES (?,?,?,?,?,?,?)""",
            (
                run_id,
                attempt_number,
                topic,
                ", ".join(failed_criteria),
                json.dumps(reasons),
                json.dumps(suggestions),
                _now(),
            ),
        )


def get_rejection_history(limit: int = 50) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM rejection_logs ORDER BY rejected_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["reasons_json"] = json.loads(d["reasons_json"])
            d["suggestions_json"] = json.loads(d["suggestions_json"])
            results.append(d)
        return results


def get_rejections_for_run(run_id: str) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM rejection_logs WHERE run_id=? ORDER BY attempt_number",
            (run_id,),
        ).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["reasons_json"] = json.loads(d["reasons_json"])
            d["suggestions_json"] = json.loads(d["suggestions_json"])
            results.append(d)
        return results


# ======================================================================= #
#  Memory pattern helpers
# ======================================================================= #

def upsert_memory_pattern(criterion: str, reason: str, suggestion: str = "") -> None:
    """Increment failure count for a criterion and update metadata."""
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT * FROM memory_patterns WHERE criterion=?", (criterion,)
        ).fetchone()

        if existing:
            current_reasons: List[str] = json.loads(existing["common_reasons_json"])
            if reason and reason not in current_reasons:
                current_reasons.append(reason)
            current_reasons = current_reasons[-10:]  # keep last 10
            conn.execute(
                """UPDATE memory_patterns
                   SET failure_count=failure_count+1, last_seen=?, common_reasons_json=?, suggested_improvement=?
                   WHERE criterion=?""",
                (_now(), json.dumps(current_reasons), suggestion or existing["suggested_improvement"], criterion),
            )
        else:
            conn.execute(
                """INSERT INTO memory_patterns
                   (criterion, failure_count, last_seen, common_reasons_json, suggested_improvement)
                   VALUES (?,1,?,?,?)""",
                (criterion, _now(), json.dumps([reason] if reason else []), suggestion),
            )


def get_memory_patterns(min_failures: int = 1) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM memory_patterns WHERE failure_count >= ? ORDER BY failure_count DESC",
            (min_failures,),
        ).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["common_reasons_json"] = json.loads(d["common_reasons_json"])
            results.append(d)
        return results


# ======================================================================= #
#  Prompt improvement helpers
# ======================================================================= #

def save_prompt_improvement(criterion: str, instruction: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO prompt_improvements (criterion, improvement_instruction, approved_at) VALUES (?,?,?)",
            (criterion, instruction, _now()),
        )


def get_prompt_improvements() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM prompt_improvements ORDER BY approved_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def increment_improvement_usage(improvement_id: int) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE prompt_improvements SET times_applied=times_applied+1 WHERE id=?",
            (improvement_id,),
        )
