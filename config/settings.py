import os
from pathlib import Path
 
BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "local-teaching-only-key")
DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]
INSTALLED_APPS = ["monitoring"]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [], "APP_DIRS": True,
    "OPTIONS": {"context_processors": []},
}]
DATABASES = {"default": {
    "ENGINE": "django.db.backends.postgresql",
    "NAME": os.getenv("POSTGRES_DB", "monitoring"),
    "USER": os.getenv("POSTGRES_USER", "student"),
    "PASSWORD": os.getenv("POSTGRES_PASSWORD", "student_lab"),
    "HOST": os.getenv("POSTGRES_HOST", "db"),
    "PORT": "5432",
}}
LANGUAGE_CODE = "ru-ru"
TIME_ZONE = "UTC"
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
