import functools
import hashlib
import hmac
import json
import os
import random
import re
import secrets
import sqlite3
import time
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server
from socketserver import ThreadingMixIn
from wsgiref.simple_server import WSGIServer

ROOT = Path(__file__).resolve().parent
DB = Path(os.getenv("DB_PATH", ROOT / "data" / "school.sqlite3"))
BANDS = {"1-4": (1, 4), "5-9": (5, 9), "9-11": (9, 11)}
PASSWORD = os.getenv("ADMIN_PASSWORD", "")
COOKIE_SECURE = os.getenv("COOKIE_SECURE") == "1"
SCHEMA = """
CREATE TABLE IF NOT EXISTS students(id INTEGER PRIMARY KEY, name TEXT NOT NULL, grade INTEGER NOT NULL CHECK(grade BETWEEN 1 AND 11), token TEXT UNIQUE NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS topics(id INTEGER PRIMARY KEY, grade INTEGER NOT NULL, name TEXT NOT NULL, UNIQUE(grade,name));
CREATE TABLE IF NOT EXISTS questions(code TEXT PRIMARY KEY, topic_id INTEGER NOT NULL REFERENCES topics(id), prompt TEXT NOT NULL, options TEXT NOT NULL, correct INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS attempts(id INTEGER PRIMARY KEY, student_id INTEGER NOT NULL REFERENCES students(id), band TEXT NOT NULL, started_at TEXT NOT NULL, finished_at TEXT);
CREATE INDEX IF NOT EXISTS attempts_student ON attempts(student_id,id);
CREATE UNIQUE INDEX IF NOT EXISTS one_active ON attempts(student_id) WHERE finished_at IS NULL;
CREATE TABLE IF NOT EXISTS items(id INTEGER PRIMARY KEY, attempt_id INTEGER NOT NULL REFERENCES attempts(id), grade INTEGER NOT NULL, topic TEXT NOT NULL, prompt TEXT NOT NULL, options TEXT NOT NULL, correct INTEGER NOT NULL, selected INTEGER, answered_at TEXT);
CREATE INDEX IF NOT EXISTS items_attempt ON items(attempt_id,id);
CREATE TABLE IF NOT EXISTS limits(bucket TEXT PRIMARY KEY, count INTEGER NOT NULL, deadline INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
"""


def connect():
    db = sqlite3.connect(DB, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    return db


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def clean(value, max_length):
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= max_length:
        raise ValueError("Мәтін бос немесе тым ұзын.")
    return value.strip()


def import_bank(db, bank):
    rows = bank.get("questions") if isinstance(bank, dict) else None
    if not isinstance(rows, list) or not 1 <= len(rows) <= 2000:
        raise ValueError("questions тізімінде 1–2000 есеп болуы керек.")
    codes = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Әр есеп JSON объектісі болуы керек.")
        code = clean(row.get("id"), 80)
        grade = row.get("grade")
        topic = clean(row.get("topic"), 90)
        prompt = clean(row.get("prompt"), 1000)
        options = row.get("options")
        correct = row.get("correct_index")
        if code in codes or type(grade) is not int or not 1 <= grade <= 11:
            raise ValueError("Есеп ID бірегей, сынып 1–11 аралығында болуы керек.")
        if not isinstance(options, list) or not 2 <= len(options) <= 6:
            raise ValueError("Әр есепте 2–6 жауап нұсқасы болуы керек.")
        options = [clean(option, 300) for option in options]
        if len(set(options)) != len(options) or type(correct) is not int or not 0 <= correct < len(options):
            raise ValueError("Жауаптар бірегей, correct_index дұрыс нұсқаны көрсетуі керек.")
        codes.add(code)
        db.execute("INSERT OR IGNORE INTO topics(grade,name) VALUES(?,?)", (grade, topic))
        topic_id = db.execute("SELECT id FROM topics WHERE grade=? AND name=?", (grade, topic)).fetchone()["id"]
        db.execute("""INSERT INTO questions VALUES(?,?,?,?,?) ON CONFLICT(code) DO UPDATE
                      SET topic_id=excluded.topic_id,prompt=excluded.prompt,options=excluded.options,correct=excluded.correct""",
                   (code, topic_id, prompt, json.dumps(options, ensure_ascii=False), correct))
    db.execute("UPDATE settings SET value=CAST(value AS INTEGER)+1 WHERE key='bank_revision'")
    return len(codes)


def initialize():
    DB.parent.mkdir(parents=True, exist_ok=True)
    with closing(connect()) as db, db:
        db.execute("PRAGMA journal_mode=WAL")
        db.executescript(SCHEMA)
        db.execute("INSERT OR IGNORE INTO settings VALUES('secret',?)", (secrets.token_hex(32),))
        cursor = db.execute("INSERT OR IGNORE INTO settings VALUES('bank_revision','0')")
        if cursor.rowcount:
            import_bank(db, json.loads((ROOT / "question-bank.json").read_text(encoding="utf-8")))


@functools.lru_cache(maxsize=32)
def bank_layout(revision):
    with closing(connect()) as db:
        return tuple((row["grade"], row["name"]) for row in db.execute("""
          SELECT grade,name FROM topics JOIN questions ON topic_id=id GROUP BY topics.id HAVING COUNT(*)>=2
          ORDER BY grade,topics.id"""))


class Error(Exception):
    def __init__(self, status, message):
        self.status = status
        self.message = message


def missing():
    raise Error("404 Not Found", "Дерек табылмады.")


def cookie(name, value, age):
    secure = "; Secure" if COOKIE_SECURE else ""
    return ("Set-Cookie", f"{name}={value}; Path=/; HttpOnly; SameSite=Strict; Max-Age={age}{secure}")


def signature(db, expiry):
    key = db.execute("SELECT value FROM settings WHERE key='secret'").fetchone()[0]
    return hmac.new(key.encode(), f"{expiry}:{PASSWORD}".encode(), hashlib.sha256).hexdigest()


def admin_ok(db, cookies):
    expiry, _, mac = cookies.get("admin", "").partition(".")
    return bool(PASSWORD and expiry.isascii() and expiry.isdecimal() and len(expiry) <= 12
                and int(expiry) > time.time() and hmac.compare_digest(mac.encode(), signature(db, expiry).encode()))


def student_for(db, cookies):
    return db.execute("SELECT id,name,grade,created_at FROM students WHERE token=?", (cookies.get("student", ""),)).fetchone()


def summary(db, attempt_id):
    attempt = db.execute("SELECT * FROM attempts WHERE id=?", (attempt_id,)).fetchone()
    if not attempt:
        missing()
    details = []
    grades = {}
    topics = {}
    for row in db.execute("SELECT * FROM items WHERE attempt_id=? ORDER BY id", (attempt_id,)):
        item = dict(row)
        item.pop("attempt_id")
        item["options"] = json.loads(item["options"])
        details.append(item)
        for counters, key, base in (
            (grades, item["grade"], {"grade": item["grade"]}),
            (topics, (item["grade"], item["topic"]), {"grade": item["grade"], "topic": item["topic"]}),
        ):
            record = counters.setdefault(key, dict(base, correct=0, answered=0, total=0))
            record["total"] += 1
            if item["selected"] is not None:
                record["answered"] += 1
                record["correct"] += int(item["selected"] == item["correct"])
    weak = [entry["grade"] for entry in grades.values() if entry["answered"] == entry["total"] and entry["correct"] * 100 < entry["total"] * 70]
    return dict(attempt) | {"questions": details, "grades": list(grades.values()),
                            "topics": list(topics.values()), "recommended_grade": min(weak, default=None)}


def test_view(db, attempt):
    items = [dict(row) for row in db.execute("SELECT id,grade,topic,prompt,options,selected FROM items WHERE attempt_id=? ORDER BY id", (attempt["id"],))]
    for item in items:
        item["options"] = json.loads(item["options"])
    return dict(attempt) | {"questions": items}


LIST_SQL = """
SELECT a.*,s.name,s.grade,
 (SELECT COUNT(*) FROM items WHERE attempt_id=a.id) AS total,
 (SELECT COUNT(*) FROM items WHERE attempt_id=a.id AND selected IS NOT NULL) AS answered,
 (SELECT COUNT(*) FROM items WHERE attempt_id=a.id AND selected=correct) AS correct
FROM attempts a JOIN students s ON a.student_id=s.id
"""


def paginate(db, sql, args, query, order):
    try:
        page = max(1, min(1000000, int(query.get("page", ["1"])[0])))
        size = max(1, min(100, int(query.get("page_size", ["20"])[0])))
    except ValueError:
        raise Error("400 Bad Request", "Бет нөмірі сан болуы керек.")
    total = db.execute(f"SELECT COUNT(*) FROM ({sql})", args).fetchone()[0]
    rows = db.execute(f"{sql} ORDER BY {order} LIMIT ? OFFSET ?", (*args, size, (page-1)*size))
    return {"items": [dict(row) for row in rows], "page": page, "page_size": size, "total": total}


def dispatch(db, method, route, query, cookies, body, headers):
    student = student_for(db, cookies)

    if route == "/api/login" and method == "POST":
        name = clean(body.get("name"), 120)
        grade = body.get("grade")
        if type(grade) is not int or not 1 <= grade <= 11:
            raise ValueError("Сыныпты таңдаңыз.")
        token = secrets.token_urlsafe(32)
        identifier = db.execute("INSERT INTO students(name,grade,token,created_at) VALUES(?,?,?,?)", (name,grade,token,now())).lastrowid
        headers.append(cookie("student", token, 7*86400))
        return {"id": identifier, "name": name, "grade": grade}
    if route == "/api/logout" and method == "POST":
        headers.append(cookie("student", "", 0))
        return {}
    if route == "/api/admin/login" and method == "POST":
        supplied = body.get("password")
        if not PASSWORD or not isinstance(supplied, str) or not hmac.compare_digest(PASSWORD.encode(), supplied.encode()):
            raise Error("401 Unauthorized", "Құпиясөз қате немесе әкімші кіруі бапталмаған.")
        expiry = str(int(time.time()) + 8*3600)
        headers.append(cookie("admin", f"{expiry}.{signature(db, expiry)}", 8*3600))
        return {}
    if route == "/api/admin/logout" and method == "POST":
        headers.append(cookie("admin", "", 0))
        return {}
    if route.startswith("/api/admin/"):
        if not admin_ok(db, cookies):
            raise Error("401 Unauthorized", "Әкімші ретінде кіріңіз.")
        endpoint = route.removeprefix("/api/admin/")
        if endpoint == "session" and method == "GET":
            return {"authenticated": True}
        if endpoint == "questions/import" and method == "POST":
            return {"imported": import_bank(db, body)}
        if endpoint == "results" and method == "GET":
            return paginate(db, LIST_SQL, (), query, "id DESC")
        if endpoint == "students" and method == "GET":
            search = query.get("q", [""])[0][:120].casefold()
            db.create_function("casefold", 1, str.casefold)
            return paginate(db, """SELECT id,name,grade,created_at,
              (SELECT COUNT(*) FROM attempts WHERE student_id=students.id) AS attempts
              FROM students WHERE INSTR(casefold(name),?) > 0 OR ?=''""", (search,search), query, "id DESC")
        if match := re.fullmatch(r"student/(\d+)/result", endpoint):
            if method == "GET":
                record = db.execute("SELECT id,name,grade,created_at FROM students WHERE id=?", (int(match[1]),)).fetchone()
                if not record:
                    missing()
                return {"student": dict(record), **paginate(db, LIST_SQL+" WHERE student_id=?", (record["id"],), query, "id DESC")}
        if match := re.fullmatch(r"results/(\d+)", endpoint):
            if method == "GET":
                result = summary(db, int(match[1]))
                result["student"] = dict(db.execute("SELECT id,name,grade FROM students WHERE id=?", (result["student_id"],)).fetchone())
                return result
        missing()

    if not student:
        raise Error("401 Unauthorized", "Алдымен тіркеліңіз.")
    if route == "/api/home" and method == "GET":
        active = db.execute("SELECT id,band FROM attempts WHERE student_id=? AND finished_at IS NULL", (student["id"],)).fetchone()
        last = db.execute("SELECT id FROM attempts WHERE student_id=? AND finished_at IS NOT NULL ORDER BY id DESC LIMIT 1", (student["id"],)).fetchone()
        return {"student": dict(student), "active": dict(active) if active else None, "last": last["id"] if last else None,
                "bands": [{"id": key, "allowed": low <= student["grade"] <= high, "min": low, "max": high} for key,(low,high) in BANDS.items()]}
    if route == "/api/test" and method == "POST":
        band = body.get("band")
        if not isinstance(band,str) or band not in BANDS or not BANDS[band][0] <= student["grade"] <= BANDS[band][1]:
            raise Error("403 Forbidden", "Бұл бөлім сіздің сыныбыңызға қолжетімсіз.")
        db.execute("BEGIN IMMEDIATE")
        active = db.execute("SELECT id,band FROM attempts WHERE student_id=? AND finished_at IS NULL", (student["id"],)).fetchone()
        if active:
            if active["band"] != band:
                raise Error("409 Conflict", "Алдымен басталған тестті аяқтаңыз.")
            return {"id": active["id"]}
        revision = db.execute("SELECT value FROM settings WHERE key='bank_revision'").fetchone()[0]
        layout = bank_layout(revision)
        attempt = db.execute("INSERT INTO attempts(student_id,band,started_at) VALUES(?,?,?)", (student["id"],band,now())).lastrowid
        for grade in range(BANDS[band][0], student["grade"]+1):
            topics = [name for level,name in layout if level == grade]
            if len(topics) < 3:
                raise Error("409 Conflict", f"{grade}-сыныпқа үш тақырып қажет.")
            for topic in random.sample(topics, 3):
                db.execute("""INSERT INTO items(attempt_id,grade,topic,prompt,options,correct)
                  SELECT ?,grade,name,prompt,options,correct FROM questions JOIN topics ON topic_id=id
                  WHERE grade=? AND name=? ORDER BY RANDOM() LIMIT 3""", (attempt,grade,topic))
        return {"id": attempt}
    match = re.fullmatch(r"/api/test/(\d+)(?:/(answer|finish|result))?", route)
    if match:
        identifier = int(match[1])
        action = match[2]
        if method == "POST":
            db.execute("BEGIN IMMEDIATE")
        attempt = db.execute("SELECT * FROM attempts WHERE id=? AND student_id=?", (identifier,student["id"])).fetchone()
        if not attempt:
            missing()
        if action is None and method == "GET":
            return test_view(db, attempt)
        if action == "result" and method == "GET" and attempt["finished_at"]:
            result = summary(db, identifier)
            result.pop("questions")
            return result
        if action == "answer" and method == "POST" and not attempt["finished_at"]:
            item_id, selected = body.get("question_id"), body.get("selected")
            if type(item_id) is not int or type(selected) is not int or not 0 < item_id < 2**63:
                raise ValueError("Жауап нұсқасын таңдаңыз.")
            item = db.execute("SELECT options FROM items WHERE id=? AND attempt_id=?", (item_id,identifier)).fetchone()
            if not item or not 0 <= selected < len(json.loads(item["options"])):
                raise ValueError("Жауап нұсқасын таңдаңыз.")
            db.execute("UPDATE items SET selected=?,answered_at=? WHERE id=? AND selected IS NOT ?", (selected,now(),item_id,selected))
            return {"saved": True}
        if action == "finish" and method == "POST":
            if db.execute("SELECT 1 FROM items WHERE attempt_id=? AND selected IS NULL LIMIT 1", (identifier,)).fetchone():
                raise Error("409 Conflict", "Барлық есепке жауап беріңіз.")
            db.execute("UPDATE attempts SET finished_at=? WHERE id=? AND finished_at IS NULL", (now(),identifier))
            return {"id": identifier}
    missing()


def rate_limit(db, env, route):
    if env["REQUEST_METHOD"] != "POST":
        return
    address = env.get("REMOTE_ADDR", "")
    if os.getenv("TRUST_NGINX") == "1":
        address = env.get("HTTP_X_REAL_IP") or address
    category, ceiling = {"/api/admin/login": ("admin", 10), "/api/login": ("login", 30)}.get(route, ("write", 240))
    deadline = (int(time.time())//60+1)*60
    key = f"{address}|{category}|{deadline}"
    with db:
        db.execute("DELETE FROM limits WHERE deadline<=?", (int(time.time()),))
        count = db.execute("""INSERT INTO limits VALUES(?,1,?) ON CONFLICT(bucket)
                              DO UPDATE SET count=count+1 RETURNING count""", (key,deadline)).fetchone()[0]
    if count > ceiling:
        raise Error("429 Too Many Requests", "Әрекет тым жиі қайталанды. Бір минуттан кейін көріңіз.")


def application(env, start):
    route = env["PATH_INFO"].rstrip("/") or "/"
    method = env["REQUEST_METHOD"]
    headers = [("X-Content-Type-Options", "nosniff"), ("X-Frame-Options", "DENY"),
               ("Referrer-Policy", "same-origin"), ("Cache-Control", "no-store"),
               ("Content-Security-Policy", "default-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")]
    status = "200 OK"
    mime = "application/json; charset=utf-8"
    try:
        if route == "/health" and method == "GET":
            with closing(connect()) as db:
                db.execute("SELECT id FROM students LIMIT 1")
            response = b'{"ok":true}'
        elif route.startswith("/api/"):
            cookies = dict(part.strip().split("=",1) for part in env.get("HTTP_COOKIE","").split(";") if "=" in part)
            body = {}
            if method == "POST":
                if env.get("HTTP_SEC_FETCH_SITE") == "cross-site" or env.get("CONTENT_TYPE","").split(";")[0] != "application/json":
                    raise Error("415 Unsupported Media Type", "JSON сұрауы қажет.")
                size = int(env.get("CONTENT_LENGTH") or "0")
                if not 0 <= size <= 2_000_000:
                    raise Error("413 Payload Too Large", "Файл 2 МБ-тан аспауы керек.")
                body = json.loads(env["wsgi.input"].read(size))
                if not isinstance(body, dict):
                    raise ValueError("JSON объектісі қажет.")
            with closing(connect()) as db:
                rate_limit(db, env, route)
                with db:
                    data = dispatch(db,method,route,parse_qs(env.get("QUERY_STRING","")),cookies,body,headers)
            response = json.dumps(data, ensure_ascii=False).encode()
        elif method == "GET":
            assets = {"/app.js": ("app.js","text/javascript"), "/style.css": ("style.css","text/css")}
            pages = {"/","/login","/home","/test","/test/result","/admin"}
            if route in assets:
                name,mime = assets[route]
                mime += "; charset=utf-8"
            elif route in pages:
                name,mime = "index.html","text/html; charset=utf-8"
            else:
                missing()
            response = (ROOT / "web" / name).read_bytes()
        else:
            missing()
    except (Error, ValueError, OverflowError, sqlite3.Error) as exc:
        if isinstance(exc, Error):
            status, message = exc.status, exc.message
        elif isinstance(exc, sqlite3.Error):
            env["wsgi.errors"].write(f"Database error: {exc}\n")
            status, message = "503 Service Unavailable", "Дерекқор уақытша қолжетімсіз."
        else:
            status, message = "400 Bad Request", str(exc)
        response = json.dumps({"error": message}, ensure_ascii=False).encode()
    start(status, headers+[("Content-Type",mime),("Content-Length",str(len(response)))])
    return [response]


class ThreadedServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


if __name__ == "__main__":
    initialize()
    host, port = os.getenv("HOST","127.0.0.1"), int(os.getenv("PORT","8000"))
    with make_server(host, port, application, server_class=ThreadedServer) as server:
        print(f"Bilim Check: http://{host}:{port}", flush=True)
        server.serve_forever()
