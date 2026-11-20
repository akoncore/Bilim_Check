import os

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")
DEBUG = os.getenv("DJANGO_DEBUG") == "1"
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
ROOT_URLCONF = "bilim.urls"
INSTALLED_APPS = ["django.contrib.auth", "django.contrib.contenttypes", "django.contrib.sessions", "rest_framework", "diagnostics"]
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
TRUST_PROXY = os.getenv("TRUST_PROXY") == "1"
if TRUST_PROXY:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_CONTENT_TYPE_NOSNIFF = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
CSRF_FAILURE_VIEW = "diagnostics.views.csrf_failure"

DATA_UPLOAD_MAX_MEMORY_SIZE = 2_000_000
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
}
if redis_url := os.getenv("REDIS_URL"):
    CACHES = {"default": {
        "BACKEND": "bilim.cache.ResilientRedisCache",
        "LOCATION": redis_url,
        "KEY_PREFIX": "bilim-check",
        "OPTIONS": {"socket_connect_timeout": 0.35, "socket_timeout": 0.35, "retry_on_timeout": False},
    }}
