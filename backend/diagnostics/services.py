import random
import time

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db.models import Count, F, Window
from django.db.models.functions import Random, RowNumber
from django.utils import timezone

from .models import Attempt, BankRevision, Item, Question, RateBucket, Topic, Student

BANDS = {"1-4": (1, 4), "5-9": (5, 9), "9-11": (9, 11)}
STUDENT_FIELDS = ("id", "name", "grade", "created_at")
ATTEMPT_FIELDS = ("id", "student_id", "band", "started_at", "finished_at")
ITEM_FIELDS = ("id", "grade", "topic", "prompt", "options", "selected")


class ApiError(Exception):
    def __init__(self, status, message):
        self.status = status
        self.message = message


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
    records = []
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
        records.append((grade, topic_name, code, prompt, options, correct))
    keys = dict.fromkeys((grade, name) for grade, name, *_ in records)
    Topic.objects.bulk_create([Topic(grade=grade, name=name) for grade, name in keys], ignore_conflicts=True)
    topics = Topic.objects.filter(name__in={name for _, name in keys}).values_list("grade", "name", "pk")
    topic_ids = {(grade, name): pk for grade, name, pk in topics}
    Question.objects.bulk_create(
        [Question(code=code, topic_id=topic_ids[grade, name], prompt=prompt, options=options, correct=correct)
         for grade, name, code, prompt, options, correct in records],
        update_conflicts=True, unique_fields=["code"], update_fields=["topic", "prompt", "options", "correct"],
    )
    revision.version += 1
    revision.save(update_fields=["version"])
    return len(codes)


def bank_layout(version):
    key = f"bank-layout:v1:{version}"
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
    selected_topics = {}
    for grade in range(BANDS[band][0], student.grade + 1):
        topics = [(pk, name) for pk, level, name in layout if level == grade]
        if len(topics) < 3:
            raise ApiError(409, f"{grade}-сыныпқа үш тақырып қажет.")
        for pk, name in random.sample(topics, 3):
            selected_topics[pk] = (grade, name)
    order = {pk: index for index, pk in enumerate(selected_topics)}
    questions = Question.objects.filter(topic_id__in=selected_topics).annotate(
        position=Window(expression=RowNumber(), partition_by=F("topic_id"), order_by=Random().asc()),
    ).filter(position__lte=3)
    attempt = Attempt.objects.create(student=student, band=band)
    items = []
    for question in sorted(questions, key=lambda row: (order[row.topic_id], row.position)):
        grade, name = selected_topics[question.topic_id]
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


@transaction.atomic
def rate_limit(request, category, ceiling):
    address = request.META.get("REMOTE_ADDR", "")
    if settings.TRUST_PROXY:
        address = request.META.get("HTTP_X_REAL_IP") or address
    current = int(time.time())
    minute = current // 60
    RateBucket.objects.filter(deadline__lt=minute).delete()
    key = f"{address[:50]}:{category}:{minute}"
    bucket, _ = RateBucket.objects.select_for_update().get_or_create(key=key, defaults={"deadline": minute})
    if bucket.count >= ceiling:
        return 60 - current % 60
    bucket.count += 1
    bucket.save(update_fields=["count"])
    return 0
