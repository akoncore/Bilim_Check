from django.urls import re_path
from diagnostics.views import api, health

urlpatterns = [
    re_path(r"^api/(?P<route>.*?)/*$", api),
    re_path(r"^health/?$", health),
]
