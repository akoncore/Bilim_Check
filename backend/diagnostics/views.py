import json
import random
import re
import time

from django.contrib.auth import authenticate, login, logout
from django.core.cache import cache
from django.core.exceptions import RequestDataTooBig
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, F, Q
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.utils import timezone

from .models import Attempt, BankRevision, Item, Question, RateBucket, Student, Topic

BANDS = {"1-4": (1, 4), "5-9": (5, 9), "9-11": (9, 11)}
STUDENT_FIELDS = ("id", "name", "grade", "created_at")
ATTEMPT_FIELDS = ("id", "student_id", "band", "started_at", "finished_at")
ITEM_FIELDS = ("id", "grade", "topic", "prompt", "options", "selected")


class ApiError(Exception):
    def __init__(self, status, message):
        self.status = status
        self.message = message


def response(data, status=200):
    return JsonResponse(data, status=status, headers={"Cache-Control": "no-store"})


def csrf_failure(request, reason=""):
    return response({"error": "Бетті жаңартып, қайта көріңіз."}, 403)


def health(request):
    Student.objects.exists()
    return response({"ok": True})


def required(record):
    if record is None:
        raise ApiError(404, "Дерек табылмады.")
    return record


def clean(value, length):
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= length or "\x00" in value:
        raise ValueError("Мәтін бос немесе жарамсыз.")
    value.encode("utf-8")
    return value.strip()


@transaction.atomic
def import_bank(bank, *, seed=False):
    revision, _ = BankRevision.objects.select_for_update().get_or_create(pk=1)
    if seed and revision.version:
        return 0
    rows = bank.get("questions") if isinstance(bank, dict) else None
    if not isinstance(rows, list) or not 1 <= len(rows) <= 2000:
        raise ValueError("questions тізімінде 1–2000 есеп болуы керек.")
    codes = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Әр есеп JSON объектісі болуы керек.")
        code = clean(row.get("id"), 80)
        grade = row.get("grade")
        topic_name = clean(row.get("topic"), 90)
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
        topic, _ = Topic.objects.get_or_create(grade=grade, name=topic_name)
        Question.objects.update_or_create(code=code, defaults={
            "topic": topic, "prompt": prompt, "options": options, "correct": correct,
        })
    revision.version += 1
    revision.save(update_fields=["version"])
    return len(codes)


def bank_layout(version):
    key = f"bank-layout:{version}"
    layout = cache.get(key)
    if layout is None:
        layout = list(Topic.objects.annotate(question_count=Count("question")).filter(
            question_count__gte=2
        ).values_list("id", "grade", "name"))
        cache.set(key, layout, timeout=3600)
    return layout


@transaction.atomic
def start_test(student, band):
    if not isinstance(band, str) or band not in BANDS or not BANDS[band][0] <= student.grade <= BANDS[band][1]:
        raise ApiError(403, "Бұл бөлім сіздің сыныбыңызға қолжетімсіз.")
    Student.objects.select_for_update().get(pk=student.pk)
    active = Attempt.objects.filter(student=student, finished_at__isnull=True).first()
    if active:
        if active.band != band:
            raise ApiError(409, "Алдымен басталған тестті аяқтаңыз.")
        return {"id": active.pk}
    revision = required(BankRevision.objects.select_for_update().filter(pk=1).first())
    layout = bank_layout(revision.version)
    attempt = Attempt.objects.create(student=student, band=band)
    items = []
    for grade in range(BANDS[band][0], student.grade + 1):
        topics = [(pk, name) for pk, level, name in layout if level == grade]
        if len(topics) < 3:
            raise ApiError(409, f"{grade}-сыныпқа үш тақырып қажет.")
        for pk, name in random.sample(topics, 3):
            for question in Question.objects.filter(topic_id=pk).order_by("?")[:3]:
                items.append(Item(attempt=attempt, grade=grade, topic=name, prompt=question.prompt,
                                  options=question.options, correct=question.correct))
    Item.objects.bulk_create(items)
    return {"id": attempt.pk}


def report(attempt, include_questions=False):
    grades, topics = {}, {}
    items = list(Item.objects.filter(attempt_id=attempt["id"]).order_by("pk").values(
        *ITEM_FIELDS, "correct", "answered_at"
    ))
    for item in items:
        grade, topic = item["grade"], item["topic"]
        groups = (
            grades.setdefault(grade, {"grade": grade, "correct": 0, "answered": 0, "total": 0}),
            topics.setdefault((grade, topic), {"grade": grade, "topic": topic, "correct": 0, "answered": 0, "total": 0}),
        )
        for group in groups:
            group["total"] += 1
            group["answered"] += item["selected"] is not None
            group["correct"] += item["selected"] == item["correct"]
    weak = [g["grade"] for g in grades.values() if g["answered"] == g["total"] and g["correct"] * 100 < g["total"] * 70]
    data = attempt | {"grades": list(grades.values()), "topics": list(topics.values()),
                      "recommended_grade": min(weak, default=None)}
    if include_questions:
        data["questions"] = items
    return data


def paginate(query, params):
    page = max(1, min(1_000_000, int(params.get("page", 1))))
    size = max(1, min(100, int(params.get("page_size", 20))))
    paginator = Paginator(query, size)
    offset = (page - 1) * size
    return {"items": list(query[offset:offset + size]), "total": paginator.count, "page": page, "page_size": size}


def attempts():
    return Attempt.objects.annotate(
        name=F("student__name"), grade=F("student__grade"), total=Count("items"),
        answered=Count("items", filter=Q(items__selected__isnull=False)),
        correct=Count("items", filter=Q(items__selected=F("items__correct"))),
    ).order_by("-pk").values(*ATTEMPT_FIELDS, "name", "grade", "total", "answered", "correct")


def teacher(request, route, body):
    method = request.method
    if route == "login" and method == "POST":
        username, password = body.get("username"), body.get("password")
        account = authenticate(request, username=username, password=password) if (
            isinstance(username, str) and isinstance(password, str) and len(username) <= 150
        ) else None
        if not account or not account.is_staff:
            raise ApiError(401, "Пайдаланушы аты немесе құпиясөз қате.")
        login(request, account)
        request.session.set_expiry(8 * 3600)
        return {"csrf": get_token(request)}
    if not request.user.is_authenticated or not request.user.is_staff:
        raise ApiError(401, "Әкімші ретінде кіріңіз.")
    if route == "logout" and method == "POST":
        student_id = request.session.get("student_id")
        logout(request)
        if student_id:
            request.session["student_id"] = student_id
        return {}
    if route == "session" and method == "GET":
        return {"authenticated": True}
    if route == "questions/import" and method == "POST":
        return {"imported": import_bank(body)}
    if method == "GET":
        if route == "results":
            return paginate(attempts(), request.GET)
        if route == "students":
            query = Student.objects.filter(name__icontains=request.GET.get("q", "")[:120]).annotate(
                attempts=Count("attempt")
            ).order_by("-pk").values(*STUDENT_FIELDS, "attempts")
            return paginate(query, request.GET)
        if match := re.fullmatch(r"student/([0-9]{1,18})/result", route):
            student_id = int(match[1])
            student = required(Student.objects.filter(pk=student_id).values(*STUDENT_FIELDS).first())
            return {"student": student, **paginate(attempts().filter(student_id=student_id), request.GET)}
        if match := re.fullmatch(r"results/([0-9]{1,18})", route):
            attempt = required(Attempt.objects.filter(pk=int(match[1])).values(*ATTEMPT_FIELDS).first())
            student = Student.objects.filter(pk=attempt["student_id"]).values(*STUDENT_FIELDS).get()
            return report(attempt, include_questions=True) | {"student": student}
    raise ApiError(404, "Дерек табылмады.")


@transaction.atomic
def update_test(student, pk, action, body):
    attempt = required(Attempt.objects.select_for_update().filter(pk=pk, student=student).first())
    if action == "finish":
        if attempt.items.filter(selected__isnull=True).exists():
            raise ApiError(409, "Барлық есепке жауап беріңіз.")
        if not attempt.finished_at:
            attempt.finished_at = timezone.now()
            attempt.save(update_fields=["finished_at"])
        return {"id": pk}
    if attempt.finished_at:
        raise ApiError(409, "Тест аяқталған.")
    question, selected = body.get("question_id"), body.get("selected")
    if type(question) is not int or not 1 <= question < 2**63 or type(selected) is not int:
        raise ValueError("Жауап нұсқасын таңдаңыз.")
    item = required(attempt.items.filter(pk=question).first())
    if not 0 <= selected < len(item.options):
        raise ValueError("Жауап нұсқасын таңдаңыз.")
    if item.selected != selected:
        item.selected, item.answered_at = selected, timezone.now()
        item.save(update_fields=["selected", "answered_at"])
    return {"saved": True}


def route_request(request, route, body):
    method = request.method
    if route == "csrf" and method == "GET":
        return {"csrf": get_token(request)}
    if route.startswith("admin/"):
        return teacher(request, route[6:], body)
    if route == "login" and method == "POST":
        name, grade = clean(body.get("name"), 120), body.get("grade")
        if type(grade) is not int or not 1 <= grade <= 11:
            raise ValueError("Сыныпты таңдаңыз.")
        student = Student.objects.create(name=name, grade=grade)
        request.session.cycle_key()
        request.session["student_id"] = student.pk
        return {"id": student.pk, "name": name, "grade": grade}
    if route == "logout" and method == "POST":
        request.session.pop("student_id", None)
        request.session.cycle_key()
        return {}
    student = Student.objects.filter(pk=request.session.get("student_id")).first()
    if not student:
        raise ApiError(401, "Алдымен тіркеліңіз.")
    if route == "home" and method == "GET":
        own = Attempt.objects.filter(student=student)
        return {
            "student": {key: getattr(student, key) for key in STUDENT_FIELDS},
            "active": own.filter(finished_at__isnull=True).values("id", "band").first(),
            "last": own.filter(finished_at__isnull=False).order_by("-pk").values_list("pk", flat=True).first(),
            "bands": [{"id": key, "allowed": low <= student.grade <= high, "min": low, "max": high}
                      for key, (low, high) in BANDS.items()],
        }
    if route == "test" and method == "POST":
        return start_test(student, body.get("band"))
    if match := re.fullmatch(r"test/([0-9]{1,18})(?:/(answer|finish|result))?", route):
        pk, action = int(match[1]), match[2]
        if method == "POST" and action in ("answer", "finish"):
            return update_test(student, pk, action, body)
        if method == "GET" and action in (None, "result"):
            attempt = required(Attempt.objects.filter(pk=pk, student=student).values(*ATTEMPT_FIELDS).first())
            if action == "result":
                if not attempt["finished_at"]:
                    raise ApiError(404, "Дерек табылмады.")
                return report(attempt)
            return attempt | {"questions": list(Item.objects.filter(attempt_id=pk).order_by("pk").values(*ITEM_FIELDS))}
    raise ApiError(404, "Дерек табылмады.")


@transaction.atomic
def rate_limit(request, route):
    category, ceiling = {"admin/login": ("admin", 10), "login": ("login", 30)}.get(route, ("write", 240))
    address = request.META.get("HTTP_X_REAL_IP") or request.META.get("REMOTE_ADDR", "")
    minute = int(time.time()) // 60
    RateBucket.objects.filter(deadline__lt=minute).delete()
    key = f"{address[:50]}:{category}:{minute}"
    bucket, _ = RateBucket.objects.select_for_update().get_or_create(key=key, defaults={"deadline": minute})
    if bucket.count >= ceiling:
        return False
    bucket.count += 1
    bucket.save(update_fields=["count"])
    return True


def api(request, route):
    route = route.rstrip("/")
    try:
        body = {}
        if request.method == "POST":
            if not rate_limit(request, route):
                return response({"error": "Әрекет тым жиі қайталанды. Бір минуттан кейін көріңіз."}, 429)
            if request.content_type != "application/json":
                raise ApiError(415, "JSON сұрауы қажет.")
            if len(request.body) > 2_000_000:
                raise ApiError(413, "Файл 2 МБ-тан аспауы керек.")
            body = json.loads(request.body)
            if not isinstance(body, dict):
                raise ValueError("JSON объектісі қажет.")
        return response(route_request(request, route, body))
    except RequestDataTooBig:
        return response({"error": "Файл 2 МБ-тан аспауы керек."}, 413)
    except ApiError as error:
        return response({"error": error.message}, error.status)
    except ValueError as error:
        return response({"error": str(error)}, 400)
