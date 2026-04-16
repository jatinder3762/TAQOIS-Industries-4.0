"""
TAQOIS Database Module
SQLite persistence for predictions, actions, outcomes, and audit log.
Supports the continuous-improvement loop described in the proposal.
"""

import json
import sqlite3
import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent / "taqois.db"


@contextmanager
def _connect():
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS predictions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at  TEXT NOT NULL,
                city        TEXT NOT NULL,
                corridor    TEXT NOT NULL,
                horizon_h   INTEGER NOT NULL,
                forecast_time TEXT NOT NULL,
                risk_score  REAL,
                risk_lower  REAL,
                risk_upper  REAL,
                pm25        REAL,
                pm25_lower  REAL,
                pm25_upper  REAL,
                no2         REAL,
                no2_lower   REAL,
                no2_upper   REAL,
                conditions  TEXT,
                confidence  REAL
            );

            CREATE TABLE IF NOT EXISTS actuals (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                recorded_at   TEXT NOT NULL,
                city          TEXT NOT NULL,
                corridor      TEXT NOT NULL,
                pm25_actual   REAL,
                no2_actual    REAL,
                aqi_actual    REAL,
                source        TEXT
            );

            CREATE TABLE IF NOT EXISTS actions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at  TEXT NOT NULL,
                city        TEXT NOT NULL,
                corridor    TEXT,
                action_type TEXT NOT NULL,
                description TEXT,
                triggered_by TEXT,
                status      TEXT DEFAULT 'pending'
            );

            CREATE TABLE IF NOT EXISTS audit_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp   TEXT NOT NULL,
                event_type  TEXT NOT NULL,
                details     TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_pred_city_corridor
                ON predictions(city, corridor);
            CREATE INDEX IF NOT EXISTS idx_pred_created
                ON predictions(created_at);
            CREATE INDEX IF NOT EXISTS idx_actuals_corridor
                ON actuals(city, corridor);
        """)
    logger.info("Database initialized at %s", DB_PATH)


# ---------------------------------------------------------------------------
# Predictions
# ---------------------------------------------------------------------------

def store_predictions(city: str, forecasts_df, conditions: Dict) -> int:
    now = datetime.now(timezone.utc).isoformat()
    cond_json = json.dumps(conditions)
    count = 0
    with _connect() as conn:
        for _, row in forecasts_df.iterrows():
            conn.execute(
                """INSERT INTO predictions
                   (created_at, city, corridor, horizon_h, forecast_time,
                    risk_score, risk_lower, risk_upper,
                    pm25, pm25_lower, pm25_upper,
                    no2, no2_lower, no2_upper,
                    conditions, confidence)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    now,
                    city,
                    row["corridor"],
                    int(row["horizon_hours"]),
                    row["forecast_time"],
                    row.get("risk_score"),
                    row.get("risk_score_lower"),
                    row.get("risk_score_upper"),
                    row.get("pm25"),
                    row.get("pm25_lower"),
                    row.get("pm25_upper"),
                    row.get("no2"),
                    row.get("no2_lower"),
                    row.get("no2_upper"),
                    cond_json,
                    row.get("risk_score_confidence"),
                ),
            )
            count += 1
    log_event("predictions_stored", {"city": city, "count": count})
    return count


def get_recent_predictions(city: str, limit: int = 200) -> List[Dict]:
    with _connect() as conn:
        rows = conn.execute(
            """SELECT * FROM predictions
               WHERE city = ?
               ORDER BY created_at DESC
               LIMIT ?""",
            (city, limit),
        ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Actuals (for future comparison with predictions)
# ---------------------------------------------------------------------------

def store_actual(city: str, corridor: str, pm25: float = None,
                 no2: float = None, aqi: float = None, source: str = "") -> None:
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute(
            """INSERT INTO actuals
               (recorded_at, city, corridor, pm25_actual, no2_actual, aqi_actual, source)
               VALUES (?,?,?,?,?,?,?)""",
            (now, city, corridor, pm25, no2, aqi, source),
        )
    log_event("actual_stored", {"city": city, "corridor": corridor})


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------

def store_action(city: str, corridor: Optional[str], action_type: str,
                 description: str, triggered_by: str = "system") -> int:
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        cur = conn.execute(
            """INSERT INTO actions
               (created_at, city, corridor, action_type, description, triggered_by)
               VALUES (?,?,?,?,?,?)""",
            (now, city, corridor, action_type, description, triggered_by),
        )
        action_id = cur.lastrowid
    log_event("action_created", {"city": city, "action_type": action_type, "id": action_id})
    return action_id


def get_recent_actions(city: str, limit: int = 50) -> List[Dict]:
    with _connect() as conn:
        rows = conn.execute(
            """SELECT * FROM actions
               WHERE city = ?
               ORDER BY created_at DESC
               LIMIT ?""",
            (city, limit),
        ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------

def log_event(event_type: str, details: Dict = None) -> None:
    now = datetime.now(timezone.utc).isoformat()
    details_json = json.dumps(details) if details else None
    try:
        with _connect() as conn:
            conn.execute(
                "INSERT INTO audit_log (timestamp, event_type, details) VALUES (?,?,?)",
                (now, event_type, details_json),
            )
    except Exception:
        pass


def get_audit_log(limit: int = 100) -> List[Dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Analytics helpers
# ---------------------------------------------------------------------------

def prediction_accuracy_report(city: str) -> List[Dict]:
    """Compare predictions with recorded actuals where timestamps overlap."""
    with _connect() as conn:
        rows = conn.execute(
            """SELECT
                 p.corridor,
                 AVG(ABS(p.pm25 - a.pm25_actual)) AS mae_pm25,
                 AVG(ABS(p.no2 - a.no2_actual)) AS mae_no2,
                 COUNT(*) AS n_comparisons
               FROM predictions p
               JOIN actuals a
                 ON p.city = a.city
                 AND p.corridor = a.corridor
                 AND ABS(JULIANDAY(p.forecast_time) - JULIANDAY(a.recorded_at)) < 0.125
               WHERE p.city = ?
               GROUP BY p.corridor
               ORDER BY mae_pm25 DESC""",
            (city,),
        ).fetchall()
    return [dict(r) for r in rows]


def prediction_count_by_day(city: str, days: int = 30) -> List[Dict]:
    with _connect() as conn:
        rows = conn.execute(
            """SELECT DATE(created_at) AS day, COUNT(*) AS n
               FROM predictions
               WHERE city = ?
               GROUP BY DATE(created_at)
               ORDER BY day DESC
               LIMIT ?""",
            (city, days),
        ).fetchall()
    return [dict(r) for r in rows]
