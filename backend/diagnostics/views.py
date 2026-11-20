from django.contrib.auth import authenticate, login, logout
from django.core.exceptions import RequestDataTooBig
from django.db.models import Count, F, Q
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework.exceptions import APIException, Throttled, ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.parsers import JSONParser
from rest_framework.permissions import BasePermission
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Attempt, Item, Student
from .pagination import DiagnosticPagination
from .serializers import (
    AnswerSerializer, AttemptSerializer, ItemSerializer, ListFilters, LoginSerializer,
    RegistrationSerializer, ResultFilters, StartSerializer, StudentListSerializer,
)
from .services import ATTEMPT_FIELDS, BANDS, ApiError, import_bank, rate_limit, report, required, start_test, update_test

MAX_BODY = 2_000_000


def csrf_failure(request, reason=""):
    return JsonResponse({"error": "Бетті жаңартып, қайта көріңіз."}, status=403,
                        headers={"Cache-Control": "private, no-store"})


def not_found(request):
    return JsonResponse({"error": "Дерек табылмады."}, status=404,
                        headers={"Cache-Control": "private, no-store"})


def health(request):
    Student.objects.exists()
    return JsonResponse({"ok": True}, headers={"Cache-Control": "no-store"})


class TeacherPermission(BasePermission):
    def has_permission(self, request, view):
        if request.user.is_authenticated and request.user.is_staff:
            return True
        raise ApiError(401, "Әкімші ретінде кіріңіз.")


class StudentPermission(BasePermission):
    def has_permission(self, request, view):
        request.student = Student.objects.filter(pk=request.session.get("student_id")).first()
        if request.student:
            return True
        raise ApiError(401, "Алдымен тіркеліңіз.")


@method_decorator(csrf_protect, name="dispatch")
class DiagnosticAPIView(APIView):
    renderer_classes = [JSONRenderer]
    parser_classes = [JSONParser]
    rate_category = "write"
    rate_ceiling = 240

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if request.method == "POST":
            wait = rate_limit(request, self.rate_category, self.rate_ceiling)
            if wait:
                raise Throttled(wait=wait, detail="Әрекет тым жиі қайталанды. Бір минуттан кейін көріңіз.")
            if len(request.body) > MAX_BODY:
                raise RequestDataTooBig

    def finalize_response(self, request, response, *args, **kwargs):
        response["Cache-Control"] = "private, no-store"
        return super().finalize_response(request, response, *args, **kwargs)

    def handle_exception(self, exc):
        if isinstance(exc, RequestDataTooBig):
            return Response({"error": "Файл 2 МБ-тан аспауы керек."}, status=413)
        if isinstance(exc, ApiError):
            return Response({"error": exc.message}, status=exc.status)
        if isinstance(exc, ValueError):
            return Response({"error": str(exc)}, status=400)
        response = super().handle_exception(exc)
        if isinstance(exc, APIException):
            detail = response.data.get("detail") if isinstance(response.data, dict) else None
            response.data = {"error": str(detail or "Деректерді тексеріңіз.")}
            if isinstance(exc, ValidationError):
                response.data["fields"] = exc.detail
        return response

    def validated(self, serializer_class, data):
        serializer = serializer_class(data=data)
        serializer.is_valid(raise_exception=True)
        return serializer


class CsrfView(DiagnosticAPIView):
    def get(self, request):
        return Response({"csrf": get_token(request)})


class RegisterStudent(DiagnosticAPIView):
    rate_category, rate_ceiling = "login", 30

    def post(self, request):
        student = self.validated(RegistrationSerializer, request.data).save()
        request.session.cycle_key()
        request.session["student_id"] = student.pk
        return Response(RegistrationSerializer(student).data)


class LogoutStudent(DiagnosticAPIView):
    def post(self, request):
        request.session.pop("student_id", None)
        request.session.cycle_key()
        return Response({})


class StudentHome(DiagnosticAPIView):
    permission_classes = [StudentPermission]

    def get(self, request):
        student = request.student
        own = Attempt.objects.filter(student=student)
        return Response({
            "student": RegistrationSerializer(student).data,
            "active": own.filter(finished_at__isnull=True).values("id", "band").first(),
            "last": own.filter(finished_at__isnull=False).order_by("-pk").values_list("pk", flat=True).first(),
            "bands": [{"id": key, "allowed": low <= student.grade <= high, "min": low, "max": high}
                      for key, (low, high) in BANDS.items()],
        })


class StudentTests(DiagnosticAPIView):
    permission_classes = [StudentPermission]

    def post(self, request):
        data = self.validated(StartSerializer, request.data).validated_data
        return Response(start_test(request.student, data["band"]))


class StudentTestDetail(DiagnosticAPIView):
    permission_classes = [StudentPermission]
    is_result = False

    def get(self, request, pk):
        attempt = required(Attempt.objects.filter(pk=pk, student=request.student).values(*ATTEMPT_FIELDS).first())
        if self.is_result:
            if not attempt["finished_at"]:
                return not_found(request)
            return Response(report(attempt))
        items = Item.objects.filter(attempt_id=pk).order_by("pk")
        return Response(attempt | {"questions": ItemSerializer(items, many=True).data})


class StudentTestAction(DiagnosticAPIView):
    permission_classes = [StudentPermission]
    action = None

    def post(self, request, pk):
        data = self.validated(AnswerSerializer, request.data).validated_data if self.action == "answer" else {}
        return Response(update_test(request.student, pk, self.action, data))


class TeacherLogin(DiagnosticAPIView):
    rate_category, rate_ceiling = "admin", 10

    def post(self, request):
        data = self.validated(LoginSerializer, request.data).validated_data
        account = authenticate(request, **data)
        if not account or not account.is_staff:
            raise ApiError(401, "Пайдаланушы аты немесе құпиясөз қате.")
        login(request, account)
        request.session.set_expiry(8 * 3600)
        return Response({"csrf": get_token(request)})


class TeacherSession(DiagnosticAPIView):
    permission_classes = [TeacherPermission]

    def get(self, request):
        return Response({"authenticated": True})


class TeacherLogout(DiagnosticAPIView):
    permission_classes = [TeacherPermission]

    def post(self, request):
        student_id = request.session.get("student_id")
        logout(request)
        if student_id:
            request.session["student_id"] = student_id
        return Response({})


class QuestionImport(DiagnosticAPIView):
    permission_classes = [TeacherPermission]

    def post(self, request):
        return Response({"imported": import_bank(request.data)})


class TeacherList(DiagnosticAPIView, ListAPIView):
    permission_classes = [TeacherPermission]
    pagination_class = DiagnosticPagination


class StudentList(TeacherList):
    serializer_class = StudentListSerializer

    def get_queryset(self):
        filters = self.validated(ListFilters, self.request.query_params).validated_data
        queryset = Student.objects.filter(name__icontains=filters.get("q", ""))
        if "grade" in filters:
            queryset = queryset.filter(grade=filters["grade"])
        return queryset.annotate(attempts=Count("attempt")).order_by("-pk")


class ResultList(TeacherList):
    serializer_class = AttemptSerializer

    def get_queryset(self):
        filters = self.validated(ResultFilters, self.request.query_params).validated_data
        queryset = Attempt.objects.filter(student__name__icontains=filters.get("q", ""))
        if "grade" in filters:
            queryset = queryset.filter(student__grade=filters["grade"])
        if "status" in filters:
            queryset = queryset.filter(finished_at__isnull=filters["status"] == "in_progress")
        if pk := self.kwargs.get("pk"):
            queryset = queryset.filter(student_id=pk)
        return queryset.annotate(
            name=F("student__name"), grade=F("student__grade"), total=Count("items"),
            answered=Count("items", filter=Q(items__selected__isnull=False)),
            correct=Count("items", filter=Q(items__selected=F("items__correct"))),
        ).order_by("-pk")

    def list(self, request, *args, **kwargs):
        pk = self.kwargs.get("pk")
        student = required(Student.objects.filter(pk=pk).first()) if pk else None
        response = super().list(request, *args, **kwargs)
        if student:
            response.data["student"] = RegistrationSerializer(student).data
        return response


class ResultDetail(DiagnosticAPIView):
    permission_classes = [TeacherPermission]

    def get(self, request, pk):
        attempt = required(Attempt.objects.select_related("student").filter(pk=pk).first())
        data = {field: getattr(attempt, field) for field in ATTEMPT_FIELDS}
        return Response(report(data, include_questions=True) | {"student": RegistrationSerializer(attempt.student).data})
