# db.py — SQLite tabanlı kalıcılık katmanı: kullanıcılar, oturumlar, seyahat planları, maliyet geçmişi

import os
import json
import hashlib
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta

VERI_KLASORU = "data"
DB_PATH      = os.path.join(VERI_KLASORU, "smarttravel.db")
USERS_JSON   = os.path.join(VERI_KLASORU, "users.json")
MALIYET_JSON = os.path.join(VERI_KLASORU, "maliyet_gecmisi.json")

PBKDF2_ITERASYON     = 260_000   # OWASP 2023 önerisi (PBKDF2-HMAC-SHA256)
OTURUM_GECERLILIK_GUN = 7


@contextmanager
def _conn():
    os.makedirs(VERI_KLASORU, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL DEFAULT '',
                hash_algo TEXT NOT NULL DEFAULT 'pbkdf2_sha256',
                email TEXT,
                mbti_type TEXT,
                created_at TEXT NOT NULL
            )
        """)
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username ON users(username)")

        c.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS travel_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                destination TEXT, start_date TEXT, end_date TEXT,
                duration_days INTEGER, group_size INTEGER,
                transport TEXT, budget_category TEXT, mbti_type TEXT,
                estimated_cost REAL, plan_summary TEXT,
                plan_json TEXT NOT NULL,
                saved_at TEXT NOT NULL
            )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_travel_plans_username ON travel_plans(username)")

        c.execute("""
            CREATE TABLE IF NOT EXISTS maliyet_gecmisi (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                sehir TEXT, gun_sayisi INTEGER, butce_kategorisi TEXT,
                standart_plan_tl REAL, ozellestirilmis_plan_tl REAL,
                tasarruf_yuzdesi REAL, tarih TEXT NOT NULL
            )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_maliyet_username ON maliyet_gecmisi(username)")

    _migrate_json_to_sqlite()


# ---------------------------------------------------------------------------
# PAROLA GÜVENLİĞİ
# ---------------------------------------------------------------------------

def _hash_password(password: str, salt_hex: str | None = None) -> tuple[str, str]:
    salt_hex = salt_hex or secrets.token_hex(16)
    salt = bytes.fromhex(salt_hex)
    h = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERASYON)
    return h.hex(), salt_hex


def _legacy_sha256(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _verify_password(password: str, stored_hash: str, salt: str, algo: str) -> bool:
    if algo == "pbkdf2_sha256":
        h, _ = _hash_password(password, salt)
        return secrets.compare_digest(h, stored_hash)
    if algo == "legacy_sha256":
        return secrets.compare_digest(_legacy_sha256(password), stored_hash)
    return False


# ---------------------------------------------------------------------------
# OTURUM BELİRTEÇLERİ (SESSION TOKENS)
# ---------------------------------------------------------------------------

def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(username: str) -> str:
    """Ham token'ı SADECE burada, bir kez döner — DB'ye yalnızca hash'i yazılır."""
    token = secrets.token_urlsafe(32)
    now = datetime.now()
    expires = now + timedelta(days=OTURUM_GECERLILIK_GUN)
    with _conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO sessions (token_hash, username, created_at, expires_at) "
            "VALUES (?, ?, ?, ?)",
            (_token_hash(token), username, now.isoformat(), expires.isoformat()),
        )
    return token


def validate_session(token: str | None) -> str | None:
    if not token:
        return None
    with _conn() as c:
        row = c.execute(
            "SELECT username, expires_at FROM sessions WHERE token_hash=?",
            (_token_hash(token),),
        ).fetchone()
        if not row:
            return None
        if datetime.fromisoformat(row["expires_at"]) < datetime.now():
            c.execute("DELETE FROM sessions WHERE token_hash=?", (_token_hash(token),))
            return None
        return row["username"]


def invalidate_session(token: str | None):
    if not token:
        return
    with _conn() as c:
        c.execute("DELETE FROM sessions WHERE token_hash=?", (_token_hash(token),))


# ---------------------------------------------------------------------------
# KULLANICI YÖNETİMİ
# ---------------------------------------------------------------------------

def register_user(username: str, password: str, email: str = "") -> tuple[bool, str]:
    if len(username) < 3:
        return False, "Kullanıcı adı en az 3 karakter olmalıdır."
    if len(password) < 6:
        return False, "Şifre en az 6 karakter olmalıdır."
    pw_hash, salt = _hash_password(password)
    with _conn() as c:
        exists = c.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone()
        if exists:
            return False, "Bu kullanıcı adı zaten alınmış."
        c.execute(
            "INSERT INTO users (username, password_hash, salt, hash_algo, email, mbti_type, created_at) "
            "VALUES (?, ?, ?, 'pbkdf2_sha256', ?, NULL, ?)",
            (username, pw_hash, salt, email, datetime.now().strftime("%Y-%m-%d %H:%M")),
        )
    return True, "Kayıt başarılı!"


def login_user(username: str, password: str) -> tuple[bool, str, str | None]:
    with _conn() as c:
        row = c.execute(
            "SELECT username, password_hash, salt, hash_algo FROM users WHERE username=?",
            (username,),
        ).fetchone()
        if not row:
            return False, "Kullanıcı adı bulunamadı.", None
        if not _verify_password(password, row["password_hash"], row["salt"], row["hash_algo"]):
            return False, "Şifre hatalı.", None
        if row["hash_algo"] != "pbkdf2_sha256":
            # Doğru parola girildi — kullanıcı fark etmeden modern hash'e yükselt
            # (eski kayıtlar salt'sız düz SHA-256 idi, zorla parola sıfırlatmadan geçiş).
            new_hash, new_salt = _hash_password(password)
            c.execute(
                "UPDATE users SET password_hash=?, salt=?, hash_algo='pbkdf2_sha256' WHERE username=?",
                (new_hash, new_salt, username),
            )
    token = create_session(username)
    return True, "Giriş başarılı!", token


def get_user_profile(username: str) -> dict:
    with _conn() as c:
        row = c.execute(
            "SELECT username, email, mbti_type, created_at FROM users WHERE username=?",
            (username,),
        ).fetchone()
        if not row:
            return {}
        profile = dict(row)
    profile["travel_history"] = get_travel_plans(username)
    return profile


def update_user_mbti(username: str, mbti_type: str):
    with _conn() as c:
        c.execute("UPDATE users SET mbti_type=? WHERE username=?", (mbti_type, username))


def save_travel_history(username: str, travel_record: dict):
    saved_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    record_to_store = {**travel_record, "saved_at": saved_at}
    with _conn() as c:
        c.execute(
            """INSERT INTO travel_plans
               (username, destination, start_date, end_date, duration_days, group_size,
                transport, budget_category, mbti_type, estimated_cost, plan_summary,
                plan_json, saved_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                username,
                travel_record.get("destination"),
                travel_record.get("start_date"),
                travel_record.get("end_date"),
                travel_record.get("duration_days"),
                travel_record.get("group_size"),
                travel_record.get("transport"),
                travel_record.get("budget"),
                travel_record.get("mbti_type"),
                travel_record.get("estimated_cost"),
                travel_record.get("plan_ozeti", ""),
                json.dumps(record_to_store, ensure_ascii=False),
                saved_at,
            ),
        )


def get_travel_plans(username: str) -> list:
    """Her kayıt orijinal dict şeklinde döner (destination/start_date/... + varsa full_plan),
    silme işlemi için ayrıca "_id" (travel_plans.id) alanı eklenir."""
    with _conn() as c:
        rows = c.execute(
            "SELECT id, plan_json FROM travel_plans WHERE username=? ORDER BY id ASC",
            (username,),
        ).fetchall()
    out = []
    for r in rows:
        try:
            rec = json.loads(r["plan_json"])
            rec["_id"] = r["id"]
            out.append(rec)
        except Exception:
            continue
    return out


def delete_travel_plan(username: str, plan_id: int) -> bool:
    """Yalnızca kaydın sahibi kendi planını silebilir. Başarılıysa True döner."""
    with _conn() as c:
        cur = c.execute(
            "DELETE FROM travel_plans WHERE id=? AND username=?",
            (plan_id, username),
        )
        return cur.rowcount > 0


# ---------------------------------------------------------------------------
# MALİYET GEÇMİŞİ
# ---------------------------------------------------------------------------

def maliyet_kaydet(kullanici, sehir, gun, kat, standart, ozel, tasarruf):
    with _conn() as c:
        c.execute(
            """INSERT INTO maliyet_gecmisi
               (username, sehir, gun_sayisi, butce_kategorisi, standart_plan_tl,
                ozellestirilmis_plan_tl, tasarruf_yuzdesi, tarih)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (kullanici, sehir, gun, kat, standart, ozel, round(tasarruf, 2),
             datetime.now().strftime("%Y-%m-%d %H:%M")),
        )


def maliyet_gecmisi_oku() -> list:
    with _conn() as c:
        rows = c.execute("SELECT * FROM maliyet_gecmisi ORDER BY id ASC").fetchall()
    return [
        {
            "tarih": r["tarih"], "kullanici": r["username"], "sehir": r["sehir"],
            "gun_sayisi": r["gun_sayisi"], "butce_kategorisi": r["butce_kategorisi"],
            "standart_plan_tl": r["standart_plan_tl"],
            "ozellestirilmis_plan_tl": r["ozellestirilmis_plan_tl"],
            "tasarruf_yuzdesi": r["tasarruf_yuzdesi"],
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# JSON → SQLite TEK SEFERLİK MİGRASYON
# ---------------------------------------------------------------------------

def _migrate_json_to_sqlite():
    """init_db() içinden çağrılır. İdempotent: tablolar dolu ise hiçbir şey yapmaz.
    Eski parolalar 'legacy_sha256' olarak işaretlenir — ilk girişte otomatik
    PBKDF2'ye yükselir (bkz. login_user). Orijinal JSON dosyaları silinmez."""
    with _conn() as c:
        user_count = c.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]

    if user_count == 0 and os.path.exists(USERS_JSON):
        try:
            with open(USERS_JSON, "r", encoding="utf-8") as f:
                users = json.load(f)
        except Exception:
            users = {}
        with _conn() as c:
            for uname, u in users.items():
                c.execute(
                    "INSERT OR IGNORE INTO users "
                    "(username, password_hash, salt, hash_algo, email, mbti_type, created_at) "
                    "VALUES (?, ?, '', 'legacy_sha256', ?, ?, ?)",
                    (
                        uname, u.get("password_hash", ""), u.get("email", ""),
                        u.get("mbti_type"),
                        u.get("created_at", datetime.now().strftime("%Y-%m-%d %H:%M")),
                    ),
                )
                for rec in u.get("travel_history", []):
                    c.execute(
                        """INSERT INTO travel_plans
                           (username, destination, start_date, end_date, duration_days, group_size,
                            transport, budget_category, mbti_type, estimated_cost, plan_summary,
                            plan_json, saved_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            uname, rec.get("destination"), rec.get("start_date"), rec.get("end_date"),
                            rec.get("duration_days"), rec.get("group_size"), rec.get("transport"),
                            rec.get("budget"), rec.get("mbti_type"), rec.get("estimated_cost"),
                            rec.get("plan_ozeti", ""), json.dumps(rec, ensure_ascii=False),
                            rec.get("saved_at", ""),
                        ),
                    )

    with _conn() as c:
        cost_count = c.execute("SELECT COUNT(*) AS n FROM maliyet_gecmisi").fetchone()["n"]

    if cost_count == 0 and os.path.exists(MALIYET_JSON):
        try:
            with open(MALIYET_JSON, "r", encoding="utf-8") as f:
                mal = json.load(f)
        except Exception:
            mal = {}
        with _conn() as c:
            for rec in mal.get("kayitlar", []):
                c.execute(
                    """INSERT INTO maliyet_gecmisi
                       (username, sehir, gun_sayisi, butce_kategorisi, standart_plan_tl,
                        ozellestirilmis_plan_tl, tasarruf_yuzdesi, tarih)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        rec.get("kullanici"), rec.get("sehir"), rec.get("gun_sayisi"),
                        rec.get("butce_kategorisi"), rec.get("standart_plan_tl"),
                        rec.get("ozellestirilmis_plan_tl"), rec.get("tasarruf_yuzdesi"),
                        rec.get("tarih", ""),
                    ),
                )
