"""
Django settings for config project.
"""

from pathlib import Path
import dj_database_url
import os
import environ
import cloudinary
import cloudinary.uploader
import cloudinary.api

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# 환경변수 로더 초기화
env = environ.Env(
    DEBUG=(bool, False)
)
# .env 파일 읽기 (로컬 개발 환경에서만)
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")


# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_extensions",

    "rest_framework",
    "rest_framework.authtoken",

    # ✅ CORS 허용
    "corsheaders",
    "drf_yasg",

    # custom apps1
    "users",
    "artists",
    "spaces",
    "categories",
    "equipmentcategories",
    "artistequipments",
    "spaceequipments",
    "suggestions",
    "likes",
    "notifications",
    "postings",
    "demandapi",
    "points",
    "adminapi",
    #사진저장
    "cloudinary",
    "cloudinary_storage",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",   # ✅ 맨 위쪽에 배치 권장
    "whitenoise.middleware.WhiteNoiseMiddleware", 
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
AUTH_USER_MODEL = "users.User"


# Database
DATABASES = {
    "default": dj_database_url.parse(
        os.environ.get("DATABASE_URL", f"sqlite:///{BASE_DIR / 'db.sqlite3'}")
    )
}


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
import os

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")


# Internationalization
LANGUAGE_CODE = "ko-kr"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
# settings.py
SITE_DOMAIN = "https://spotlight-be-1.onrender.com"

# Static files
STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
# Whitenoise 압축/캐싱 모드
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ✅ DRF 설정
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "users.permissions.IsOwnerOrReadOnlyWithAdminPass"
    ],
    "EXCEPTION_HANDLER": "config.utils.custom_exception_handler",
}

# ✅ CORS 설정
CORS_ALLOW_ALL_ORIGINS = True   # 개발 단계에선 전체 허용
# 운영 시에는 특정 도메인만 허용하도록 변경 권장
# CORS_ALLOWED_ORIGINS = [
#     "http://localhost:3000",
#     "https://spotlight-fe.vercel.app",
# ]
SWAGGER_SETTINGS = {
    "SECURITY_DEFINITIONS": {
        "Token": {
            "type": "apiKey",
            "name": "Authorization",   # 헤더명
            "in": "header",
            "description": "예: Token 123abc456def...",
        }
    },
    # 필요 시 기본 보안 적용
    "DEFAULT_INFO": "config.urls.schema_info",
}

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME", "dompnei8f"),
    api_key=os.getenv("CLOUDINARY_API_KEY", "888842165311445"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET", "<your_api_secret>"),
    secure=True,
)

# Django 기본 저장소를 Cloudinary로 교체
DEFAULT_FILE_STORAGE = "cloudinary_storage.storage.MediaCloudinaryStorage"