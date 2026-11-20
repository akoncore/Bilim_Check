import os

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")
DEBUG = os.getenv("DJANGO_DEBUG") == "1"
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
ROOT_URLCONF = "bilim.urls"
INSTALLED_APPS = ["django.contrib.auth", "django.contrib.contenttypes", "django.contrib.sessions", "diagnostics"]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
]
DATABASES = {"default": {
    "ENGINE": "django.db.backends.postgresql",
    "HOST": os.getenv("POSTGRES_HOST", "localhost"),
    "PORT": os.getenv("POSTGRES_PORT", "5432"),
    "NAME": os.getenv("POSTGRES_DB", "bilim"),
    "USER": os.getenv("POSTGRES_USER", "bilim"),
    "PASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
    "CONN_MAX_AGE": 60,
}}
SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = os.getenv("COOKIE_SECURE") == "1"
SESSION_COOKIE_SAMESITE = CSRF_COOKIE_SAMESITE = "Strict"
SESSION_COOKIE_AGE = 7 * 86400
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_CONTENT_TYPE_NOSNIFF = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
CSRF_FAILURE_VIEW = "diagnostics.views.csrf_failure"
