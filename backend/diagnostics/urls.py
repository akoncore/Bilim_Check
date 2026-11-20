from django.urls import re_path

from . import views


def endpoint(route, view, **options):
    return re_path(rf"^{route}/?$", view.as_view(**options))


identifier = r"(?P<pk>[0-9]{1,18})"
urlpatterns = [
    endpoint("csrf", views.CsrfView),
    endpoint("login", views.RegisterStudent),
    endpoint("logout", views.LogoutStudent),
    endpoint("home", views.StudentHome),
    endpoint("test", views.StudentTests),
    endpoint(f"test/{identifier}", views.StudentTestDetail),
    endpoint(f"test/{identifier}/result", views.StudentTestDetail, is_result=True),
    endpoint(f"test/{identifier}/answer", views.StudentTestAction, action="answer"),
    endpoint(f"test/{identifier}/finish", views.StudentTestAction, action="finish"),
    endpoint("admin/login", views.TeacherLogin),
    endpoint("admin/logout", views.TeacherLogout),
    endpoint("admin/session", views.TeacherSession),
    endpoint("admin/questions/import", views.QuestionImport),
    endpoint("admin/students", views.StudentList),
    endpoint("admin/results", views.ResultList),
    endpoint(f"admin/results/{identifier}", views.ResultDetail),
    endpoint(f"admin/student/{identifier}/result", views.ResultList),
    re_path(r"^.*$", views.not_found),
]
