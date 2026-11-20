from django.urls import include, path, re_path
from diagnostics.views import health

urlpatterns = [
    path("api/v1/", include("diagnostics.urls")),
    path("api/", include("diagnostics.urls")),
    re_path(r"^health/?$", health),
]
