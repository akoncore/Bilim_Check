import io
import json
import tempfile
import unittest
from pathlib import Path
from contextlib import closing

import app


class FlowTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(setattr, app, "DB", app.DB)
        self.addCleanup(setattr, app, "PASSWORD", app.PASSWORD)
        app.DB = Path(self.temp.name) / "test.sqlite3"
        app.PASSWORD = "test-only-password"
        app.bank_layout.cache_clear()
        self.addCleanup(app.bank_layout.cache_clear)
        app.initialize()
        self.cookies = {}

    def request(self, route, body=None, status=200, cookies=None):
        jar = self.cookies if cookies is None else cookies
        route, _, query = route.partition("?")
        payload = json.dumps(body).encode() if body is not None else b""
        env = {
            "PATH_INFO": route, "QUERY_STRING": query,
            "REQUEST_METHOD": "POST" if body is not None else "GET",
            "CONTENT_LENGTH": str(len(payload)), "CONTENT_TYPE": "application/json",
            "HTTP_COOKIE": "; ".join(f"{k}={v}" for k, v in jar.items()),
            "REMOTE_ADDR": "127.0.0.1", "wsgi.input": io.BytesIO(payload), "wsgi.errors": io.StringIO(),
        }
        def start(line, headers):
            self.assertEqual(int(line.split()[0]), status, env["wsgi.errors"].getvalue())
            for key, value in headers:
                if key == "Set-Cookie":
                    name, token = value.split(";")[0].split("=", 1)
                    jar[name] = token

        raw = b"".join(app.application(env, start))
        return json.loads(raw) if route.startswith("/api/") else raw

    def test_complete_diagnostic_and_admin_review(self):
        self.assertIn(b"Bilim Check", self.request("/login/"))
        self.request("/api/admin/results/", status=401)
        student = self.request("/api/login/", {"name": "Аружан Тест", "grade": 7})
        self.request("/api/admin/login", {"password": app.PASSWORD})
        students = self.request("/api/admin/students/?page_size=1")
        self.assertEqual(students["items"][0]["id"], student["id"])
        self.assertEqual(students["total"], 1)
        self.request("/api/test/", {"band": "9-11"}, status=403)
        attempt = self.request("/api/test/", {"band": "5-9"})["id"]
        self.assertEqual(self.request("/api/test/", {"band": "5-9"})["id"], attempt)
        base = f"/api/test/{attempt}"
        questions = self.request(base)["questions"]
        self.assertEqual(len(questions), 18)
        self.assertEqual({q["grade"] for q in questions}, {5, 6, 7})
        self.assertTrue(all("correct" not in q and "correct_index" not in q for q in questions))
        self.request(base + "/result", status=404)
        self.request(base + "/finish", {}, status=409)
        other = {}
        self.request("/api/login", {"name": "Басқа оқушы", "grade": 4}, cookies=other)
        self.request("/api/test", {"band": "5-9"}, status=403, cookies=other)
        self.request("/api/test", {"band": "9-11"}, status=403, cookies=other)
        self.request(base, status=404, cookies=other)
        admin = f"/api/admin/results/{attempt}"
        before = self.request(admin)
        self.assertIsNone(before["finished_at"])
        self.assertTrue(before["started_at"])
        bank = {"questions": [
            {"id":"new", "grade":6, "topic":"Рационал сандар", "prompt":"1 + 1 = ?", "options":["2","3"], "correct_index":0},
            {"id":"bad", "grade":12, "topic":"Тест", "prompt":"?", "options":["1","2"], "correct_index":1},
        ]}
        self.request("/api/admin/questions/import", bank, status=400)
        with closing(app.connect()) as db:
            self.assertIsNone(db.execute("SELECT code FROM questions WHERE code='new'").fetchone())
        bank["questions"].pop()
        self.assertEqual(self.request("/api/admin/questions/import", bank)["imported"], 1)
        for item in before["questions"]:
            selected = item["correct"] if item["grade"] != 6 else (item["correct"] + 1) % len(item["options"])
            self.request(base + "/answer", {"question_id": item["id"], "selected": selected})
        self.assertTrue(all(q["selected"] is not None for q in self.request(base)["questions"]))
        self.request(base + "/finish", {})
        self.request(base + "/finish", {})
        result = self.request(base + "/result")
        self.assertEqual(result["recommended_grade"], 6)
        self.assertNotIn("questions", result)
        history = self.request(f"/api/admin/student/{student['id']}/result")
        self.assertEqual(history["items"][0]["correct"], 12)
        self.assertTrue(history["items"][0]["finished_at"])
        final = self.request(admin)
        self.assertEqual(sum(q["selected"] != q["correct"] for q in final["questions"]), 6)
        self.assertTrue(all(q["answered_at"] for q in final["questions"]))

    def test_admin_login_rate_limit(self):
        for _ in range(10):
            self.request("/api/admin/login", {"password":"wrong"}, status=401)
        self.request("/api/admin/login", {"password":app.PASSWORD}, status=429)


if __name__ == "__main__":
    unittest.main()
