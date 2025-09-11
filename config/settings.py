"""
Django settings for config project.
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "django-insecure-k7041yzfj=n@kcws-p)k5s(ud(9&=e#tx15jjg28db*6ncs=em"
DEBUG = True
ALLOWED_HOSTS = ["*"]  # ✅ 배포 환경에선 도메인만 지정하는 게 안전함


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

    # custom apps
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
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",   # ✅ 맨 위쪽에 배치 권장
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


# Database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


# Static files
STATIC_URL = "static/"

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