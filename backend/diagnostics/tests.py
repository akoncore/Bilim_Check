from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.test import Client, TestCase

from .models import Question


class DiagnosticFlow(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_questions")
        get_user_model().objects.create_user(username="teacher", password="test-only", is_staff=True)

    def setUp(self):
        cache.clear()
        self.client = Client(enforce_csrf_checks=True)

    def send(self, route, body=None, status=200, client=None):
        client = client or self.client
        if body is None:
            result = client.get("/api/" + route)
        else:
            csrf = client.get("/api/csrf/").json()["csrf"]
            result = client.post("/api/" + route, body, content_type="application/json", HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(result.status_code, status, result.content)
        return result.json()

    def test_diagnostic(self):
        self.send("admin/results/", status=401)
        no_csrf = self.client.post("/api/login/", {"name": "Test", "grade": 7}, content_type="application/json")
        self.assertEqual(no_csrf.status_code, 403)
        student = self.send("login/", {"name": "Аружан Тест", "grade": 7})
        self.send("admin/login/", {"username": "teacher", "password": "test-only"})
        rows = self.send("admin/students/?page_size=1")["items"]
        self.assertEqual(rows[0]["id"], student["id"])
        self.send("test/", {"band": "9-11"}, status=403)
        attempt = self.send("test/", {"band": "5-9"})["id"]
        self.assertEqual(attempt, self.send("test/", {"band": "5-9"})["id"])
        base = f"test/{attempt}/"
        items = self.send(base)["questions"]
        self.assertEqual(len(items), 18)
        self.assertEqual({q["grade"] for q in items}, {5, 6, 7})
        self.assertTrue(all("correct" not in q for q in items))
        self.send(base + "finish/", {}, status=409)
        other = Client(enforce_csrf_checks=True)
        self.send("login/", {"name": "Оқушы", "grade": 4}, client=other)
        self.send("test/", {"band": "5-9"}, status=403, client=other)
        self.send(base, status=404, client=other)
        detail = f"admin/results/{attempt}/"
        before = self.send(detail)
        self.assertIsNone(before["finished_at"])
        self.assertTrue(before["started_at"])
        valid = {"id": "new", "grade": 6, "topic": "Рационал сандар", "prompt": "1 + 1 = ?",
                 "options": ["2", "3"], "correct_index": 0}
        self.send("admin/questions/import/", {"questions": [valid, {}]}, status=400)
        self.assertFalse(Question.objects.filter(pk="new").exists())
        self.assertEqual(self.send("admin/questions/import/", {"questions": [valid]})["imported"], 1)
        for item in before["questions"]:
            selected = item["correct"] if item["grade"] != 6 else (item["correct"] + 1) % len(item["options"])
            self.send(base + "answer/", {"question_id": item["id"], "selected": selected})
        self.send(base + "finish/", {})
        self.send(base + "finish/", {})
        report = self.send(base + "result/")
        self.assertEqual(report["recommended_grade"], 6)
        self.assertNotIn("questions", report)
        history = self.send(f"admin/student/{student['id']}/result/")
        self.assertEqual(history["items"][0]["correct"], 12)
        self.assertEqual(self.send("admin/results/")["items"][0]["answered"], 18)
        final = self.send(detail)
        self.assertTrue(all(q["answered_at"] for q in final["questions"]))
        self.send("admin/logout/", {})
        self.send("admin/results/", status=401)
        self.assertEqual(self.send("home/")["student"]["id"], student["id"])

    def test_rate_limit(self):
        from unittest.mock import patch

        with patch("diagnostics.views.time.time", return_value=1_700_000_000):
            for _ in range(10):
                self.send("admin/login/", {"username": "teacher", "password": "wrong"}, status=401)
            self.send("admin/login/", {"username": "teacher", "password": "test-only"}, status=429)
