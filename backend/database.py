"""C-SSRS SQLite database layer"""
import sqlite3
import json
import random
import string
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent / "cssrs.db"

# Characters safe for typing: no 0/O, 1/I/l ambiguity
CODE_CHARS = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
CODE_LEN = 6

# Doctor PIN: 4 digits
PIN_LEN = 4


def generate_access_code() -> str:
    return "".join(random.choices(CODE_CHARS, k=CODE_LEN))


def create_session(session_id: str, patient_id: str, version: str = "baseline", patient_phone: Optional[str] = None, doctor_pin: Optional[str] = None):
    conn = get_db()
    access_code = generate_access_code()
    # Ensure uniqueness
    while conn.execute("SELECT 1 FROM cssrs_sessions WHERE access_code = ?", (access_code,)).fetchone():
        access_code = generate_access_code()
    conn.execute(
        "INSERT INTO cssrs_sessions (session_id, patient_id, version, access_code, patient_phone, doctor_pin) VALUES (?, ?, ?, ?, ?, ?)",
        (session_id, patient_id, version, access_code, patient_phone, doctor_pin),
    )
    conn.commit()
    conn.close()
    return access_code


def get_session(session_id: str) -> Optional[dict]:
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM cssrs_sessions WHERE session_id = ?", (session_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def resolve_access_code(code: str) -> Optional[dict]:
    """Look up a session by its short access code"""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM cssrs_sessions WHERE access_code = ?", (code.upper(),)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cssrs_sessions (
            session_id TEXT PRIMARY KEY,
            patient_id TEXT NOT NULL,
            version TEXT DEFAULT 'baseline',
            access_code TEXT UNIQUE,
            patient_phone TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    # Migration: add patient_phone column if it doesn't exist
    columns = [row[1] for row in conn.execute("PRAGMA table_info(cssrs_sessions)").fetchall()]
    if "patient_phone" not in columns:
        conn.execute("ALTER TABLE cssrs_sessions ADD COLUMN patient_phone TEXT")
        conn.commit()
    if "doctor_pin" not in columns:
        conn.execute("ALTER TABLE cssrs_sessions ADD COLUMN doctor_pin TEXT")
        conn.commit()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cssrs_assessments (
            session_id TEXT PRIMARY KEY,
            patient_id TEXT NOT NULL,
            patient_phone TEXT,
            assessment_date TEXT NOT NULL,
            version TEXT DEFAULT 'baseline',
            screener_result TEXT,
            i1_wish_dead INTEGER, i1_onset TEXT, i1_duration TEXT, i1_frequency INTEGER,
            i2_non_specific INTEGER, i2_nature TEXT, i2_frequency INTEGER, i2_duration INTEGER,
            i3_with_method INTEGER, i3_method TEXT, i3_location TEXT, i3_timing TEXT,
            i4_with_intent INTEGER, i4_intent_strength INTEGER,
            i5_with_plan_and_intent INTEGER,
            intensity_frequency INTEGER, intensity_duration INTEGER,
            intensity_controllability INTEGER, intensity_deterrents INTEGER, intensity_reason INTEGER,
            intensity_total INTEGER, intensity_level TEXT,
            b1_actual_attempt INTEGER, b1_date TEXT, b1_method TEXT,
            b1_medical_damage INTEGER, b1_lethal_intent INTEGER, b1_medical_intervention INTEGER,
            b2_interrupted INTEGER, b2_date TEXT, b2_method TEXT, b2_interrupted_by TEXT,
            b3_aborted INTEGER, b3_date TEXT, b3_method TEXT, b3_stopped_by TEXT,
            b4_preparatory INTEGER, b4_behavior TEXT, b4_date TEXT, b4_has_plan INTEGER,
            b5_nssi INTEGER, b5_behavior_type TEXT, b5_frequency TEXT, b5_motivation TEXT,
            lethality_level INTEGER,
            severity_score INTEGER, severity_name TEXT,
            risk_level TEXT, risk_label TEXT,
            immediate_actions TEXT,
            follow_up TEXT, documentation TEXT, warning_signals TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    # Migration: add patient_phone to assessments
    columns2 = [row[1] for row in conn.execute("PRAGMA table_info(cssrs_assessments)").fetchall()]
    if "patient_phone" not in columns2:
        conn.execute("ALTER TABLE cssrs_assessments ADD COLUMN patient_phone TEXT")
        conn.commit()
    if "doctor_pin" not in columns2:
        conn.execute("ALTER TABLE cssrs_assessments ADD COLUMN doctor_pin TEXT")
        conn.commit()
    conn.commit()
    conn.close()


def save_assessment(result: dict):
    """Insert an assessment row. result is to_dict() output merged with raw inputs."""
    conn = get_db()
    columns = [
        "session_id", "patient_id", "patient_phone", "doctor_pin", "assessment_date", "version", "screener_result",
        "i1_wish_dead", "i1_onset", "i1_duration", "i1_frequency",
        "i2_non_specific", "i2_nature", "i2_frequency", "i2_duration",
        "i3_with_method", "i3_method", "i3_location", "i3_timing",
        "i4_with_intent", "i4_intent_strength", "i5_with_plan_and_intent",
        "intensity_frequency", "intensity_duration", "intensity_controllability",
        "intensity_deterrents", "intensity_reason", "intensity_total", "intensity_level",
        "b1_actual_attempt", "b1_date", "b1_method",
        "b1_medical_damage", "b1_lethal_intent", "b1_medical_intervention",
        "b2_interrupted", "b2_date", "b2_method", "b2_interrupted_by",
        "b3_aborted", "b3_date", "b3_method", "b3_stopped_by",
        "b4_preparatory", "b4_behavior", "b4_date", "b4_has_plan",
        "b5_nssi", "b5_behavior_type", "b5_frequency", "b5_motivation",
        "lethality_level",
        "severity_score", "severity_name",
        "risk_level", "risk_label",
        "immediate_actions", "follow_up", "documentation", "warning_signals",
    ]
    placeholders = ", ".join("?" for _ in columns)
    col_names = ", ".join(columns)
    values = [
        result["session_id"], result["patient_id"], result.get("patient_phone"), result.get("doctor_pin"), result["assessment_date"],
        result.get("version", "baseline"), result.get("screener_result"),
        # Ideation
        result.get("i1_wish_dead"), result.get("i1_onset"), result.get("i1_duration"), result.get("i1_frequency"),
        result.get("i2_non_specific"), result.get("i2_nature"), result.get("i2_frequency"), result.get("i2_duration"),
        result.get("i3_with_method"), result.get("i3_method"), result.get("i3_location"), result.get("i3_timing"),
        result.get("i4_with_intent"), result.get("i4_intent_strength"), result.get("i5_with_plan_and_intent"),
        # Intensity
        result.get("intensity_frequency"), result.get("intensity_duration"), result.get("intensity_controllability"),
        result.get("intensity_deterrents"), result.get("intensity_reason"),
        result.get("intensity_total"), result.get("intensity_level"),
        # Behavior
        result.get("b1_actual_attempt"), result.get("b1_date"), result.get("b1_method"),
        result.get("b1_medical_damage"), result.get("b1_lethal_intent"), result.get("b1_medical_intervention"),
        result.get("b2_interrupted"), result.get("b2_date"), result.get("b2_method"), result.get("b2_interrupted_by"),
        result.get("b3_aborted"), result.get("b3_date"), result.get("b3_method"), result.get("b3_stopped_by"),
        result.get("b4_preparatory"), result.get("b4_behavior"), result.get("b4_date"), result.get("b4_has_plan"),
        result.get("b5_nssi"), result.get("b5_behavior_type"), result.get("b5_frequency"), result.get("b5_motivation"),
        result.get("lethality_level"),
        # Result
        result.get("severity_score"), result.get("severity_name"),
        result.get("risk_level"), result.get("risk_label"),
        _to_csv(result.get("immediate_actions", [])),
        result.get("follow_up", ""),
        result.get("documentation", ""),
        _to_csv(result.get("warning_signals", [])),
    ]
    assert len(columns) == len(values), f"Column count mismatch: {len(columns)} cols vs {len(values)} vals"
    sql = f"INSERT INTO cssrs_assessments ({col_names}) VALUES ({placeholders})"
    conn.execute(sql, values)
    conn.commit()
    conn.close()


def get_assessment(session_id: str) -> Optional[dict]:
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM cssrs_assessments WHERE session_id = ?", (session_id,)
    ).fetchone()
    conn.close()
    if row is None:
        return None
    return _row_to_dict(row)


def list_assessments() -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM cssrs_assessments ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def list_assessments_by_doctor(pin: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM cssrs_assessments WHERE doctor_pin = ? ORDER BY created_at DESC",
        (pin,),
    ).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def get_patient_history(patient_id: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM cssrs_assessments WHERE patient_id = ? ORDER BY created_at DESC",
        (patient_id,),
    ).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def search_by_phone(phone: str) -> list[dict]:
    """Find all assessments for a given phone number (partial match)."""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM cssrs_assessments WHERE patient_phone LIKE ? ORDER BY created_at DESC",
        (f"%{phone}%",),
    ).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def _to_csv(value) -> str:
    if isinstance(value, list):
        return ",".join(str(v) for v in value)
    return str(value) if value else ""


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    # Parse comma-separated fields back to lists for JSON output
    for field in ("immediate_actions", "warning_signals"):
        if d.get(field):
            d[field] = [x.strip() for x in d[field].split(",") if x.strip()]
    return d


# ── Doctor PIN management ──

def init_doctor_pins_table():
    """Create cssrs_doctor_pins table if not exists."""
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cssrs_doctor_pins (
            pin TEXT PRIMARY KEY,
            doctor_name TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now')),
            revoked_at TEXT
        )
    """)
    conn.commit()
    conn.close()


def verify_doctor_pin(pin: str) -> Optional[dict]:
    """Check if PIN is valid and active. Returns doctor info or None."""
    conn = get_db()
    row = conn.execute(
        "SELECT pin, doctor_name, is_active, created_at FROM cssrs_doctor_pins WHERE pin = ?",
        (pin,),
    ).fetchone()
    conn.close()
    if row is None:
        return None
    d = dict(row)
    if not d["is_active"]:
        return {"error": "revoked", "doctor_name": d["doctor_name"]}
    return d


def create_doctor_pin(doctor_name: str, pin: Optional[str] = None) -> dict:
    """Create a new doctor PIN. Auto-generates 4-digit PIN if not provided."""
    if pin is None:
        pin = "".join(random.choices("0123456789", k=PIN_LEN))
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO cssrs_doctor_pins (pin, doctor_name) VALUES (?, ?)",
            (pin, doctor_name),
        )
        conn.commit()
        return {"pin": pin, "doctor_name": doctor_name, "is_active": True}
    except sqlite3.IntegrityError:
        return {"error": "PIN already exists"}
    finally:
        conn.close()


def revoke_doctor_pin(pin: str) -> bool:
    """Revoke a doctor PIN. Returns True if found and revoked."""
    conn = get_db()
    cursor = conn.execute(
        "UPDATE cssrs_doctor_pins SET is_active = 0, revoked_at = datetime('now') WHERE pin = ?",
        (pin,),
    )
    conn.commit()
    changed = cursor.rowcount > 0
    conn.close()
    return changed


def list_doctor_pins() -> list[dict]:
    """List all doctor PINs with their status."""
    conn = get_db()
    rows = conn.execute(
        "SELECT pin, doctor_name, is_active, created_at, revoked_at FROM cssrs_doctor_pins ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Admin PIN management ──

def init_admin_pins_table() -> Optional[str]:
    """Create cssrs_admin_pins table. Auto-generates admin PIN on first run.
    Returns the generated PIN string, or None if one already exists."""
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cssrs_admin_pins (
            pin TEXT PRIMARY KEY,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now')),
            revoked_at TEXT
        )
    """)
    existing = conn.execute("SELECT pin FROM cssrs_admin_pins WHERE is_active = 1").fetchone()
    if existing:
        conn.close()
        return None

    # Bootstrap: no admin PIN exists yet, generate one
    admin_pin = "".join(random.choices("0123456789", k=6))
    conn.execute("INSERT INTO cssrs_admin_pins (pin) VALUES (?)", (admin_pin,))
    conn.commit()
    conn.close()
    return admin_pin


def verify_admin_pin(pin: str) -> bool:
    """Check if admin PIN is valid and active."""
    conn = get_db()
    row = conn.execute(
        "SELECT is_active FROM cssrs_admin_pins WHERE pin = ?",
        (pin,),
    ).fetchone()
    conn.close()
    if row is None:
        return False
    return bool(row["is_active"])


def has_admin_pin() -> bool:
    """Check if any active admin PIN exists."""
    conn = get_db()
    row = conn.execute("SELECT 1 FROM cssrs_admin_pins WHERE is_active = 1").fetchone()
    conn.close()
    return row is not None


def set_admin_pin(new_pin: str, old_pin: Optional[str] = None) -> dict:
    """Set a new admin PIN. If old_pin is provided, verifies it first.
    Returns {"ok": True} or {"error": "..."}."""
    conn = get_db()
    try:
        if old_pin:
            row = conn.execute(
                "SELECT is_active FROM cssrs_admin_pins WHERE pin = ?", (old_pin,)
            ).fetchone()
            if not row or not row["is_active"]:
                return {"error": "旧密码错误"}
            # Revoke old PIN and insert new one
            conn.execute(
                "UPDATE cssrs_admin_pins SET is_active = 0, revoked_at = datetime('now') WHERE pin = ?",
                (old_pin,),
            )
        else:
            # No old PIN to verify — check if any active admin exists
            existing = conn.execute(
                "SELECT 1 FROM cssrs_admin_pins WHERE is_active = 1"
            ).fetchone()
            if existing:
                return {"error": "管理员已配置，请使用旧密码修改"}

        conn.execute("INSERT INTO cssrs_admin_pins (pin) VALUES (?)", (new_pin,))
        conn.commit()
        return {"ok": True}
    except sqlite3.IntegrityError:
        return {"error": "该密码已存在，请换一个"}
    finally:
        conn.close()
