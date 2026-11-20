from rest_framework import serializers

from .models import Attempt, Item, Student
from .services import ATTEMPT_FIELDS, BANDS, ITEM_FIELDS, STUDENT_FIELDS


class JsonInteger(serializers.IntegerField):
    def to_internal_value(self, data):
        if type(data) is not int:
            self.fail("invalid")
        return super().to_internal_value(data)


class RegistrationSerializer(serializers.ModelSerializer):
    grade = JsonInteger(min_value=1, max_value=11)

    class Meta:
        model = Student
        fields = STUDENT_FIELDS
        read_only_fields = ("id", "created_at")


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(max_length=4096, trim_whitespace=False, write_only=True)


class StartSerializer(serializers.Serializer):
    band = serializers.ChoiceField(choices=list(BANDS))


class AnswerSerializer(serializers.Serializer):
    question_id = JsonInteger(min_value=1, max_value=2**63 - 1)
    selected = JsonInteger(min_value=0, max_value=5)


class StudentListSerializer(RegistrationSerializer):
    attempts = serializers.IntegerField(read_only=True)

    class Meta(RegistrationSerializer.Meta):
        fields = (*STUDENT_FIELDS, "attempts")


class AttemptSerializer(serializers.ModelSerializer):
    name = serializers.CharField(read_only=True)
    grade = serializers.IntegerField(read_only=True)
    total = serializers.IntegerField(read_only=True)
    answered = serializers.IntegerField(read_only=True)
    correct = serializers.IntegerField(read_only=True)

    class Meta:
        model = Attempt
        fields = (*ATTEMPT_FIELDS, "name", "grade", "total", "answered", "correct")


class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = ITEM_FIELDS


class ListFilters(serializers.Serializer):
    q = serializers.CharField(max_length=120, required=False, allow_blank=True)
    grade = serializers.IntegerField(min_value=1, max_value=11, required=False)


class ResultFilters(ListFilters):
    status = serializers.ChoiceField(["completed", "in_progress"], required=False)
