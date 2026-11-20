from django.db import models
from django.db.models import Q


class Student(models.Model):
    name = models.CharField(max_length=120)
    grade = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=Q(grade__range=(1, 11)), name="student_grade_range")]


class Topic(models.Model):
    grade = models.PositiveSmallIntegerField()
    name = models.CharField(max_length=90)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["grade", "name"], name="unique_topic_per_grade")]


class Question(models.Model):
    code = models.CharField(max_length=80, primary_key=True)
    topic = models.ForeignKey(Topic, on_delete=models.PROTECT)
    prompt = models.TextField()
    options = models.JSONField()
    correct = models.PositiveSmallIntegerField()


class Attempt(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    band = models.CharField(max_length=5)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=["student"], condition=Q(finished_at__isnull=True), name="one_unfinished_test"
        )]


class Item(models.Model):
    attempt = models.ForeignKey(Attempt, on_delete=models.CASCADE, related_name="items")
    grade = models.PositiveSmallIntegerField()
    topic = models.CharField(max_length=90)
    prompt = models.TextField()
    options = models.JSONField()
    correct = models.PositiveSmallIntegerField()
    selected = models.PositiveSmallIntegerField(null=True)
    answered_at = models.DateTimeField(null=True)


class BankRevision(models.Model):
    version = models.PositiveBigIntegerField(default=0)


class RateBucket(models.Model):
    key = models.CharField(max_length=100, primary_key=True)
    deadline = models.PositiveBigIntegerField(db_index=True)
    count = models.PositiveIntegerField(default=0)
