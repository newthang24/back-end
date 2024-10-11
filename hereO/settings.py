import math
from datetime import datetime
from pathlib import Path
from . import secret_key
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = secret_key.SECRET_KEY
DEBUG = True
ALLOWED_HOSTS = [
    'ec2-43-203-221-193.ap-northeast-2.compute.amazonaws.com',
    'hereomyreport.com',
    '43.203.96.162',
    'localhost',       # 로컬 테스트를 위해 추가
    '127.0.0.1',       # 로컬 테스트를 위해 추가
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    'server',
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
]

AUTH_USER_MODEL = 'server.User'

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "hereO.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "hereO.wsgi.application"

from . import my_settings
DATABASES = my_settings.DATABASES

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Asia/Seoul"

USE_I18N = True

USE_TZ = False

STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.TokenAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
}

STATIC_ROOT = os.path.join(BASE_DIR, 'static')

# CORS 설정
CORS_ALLOW_ALL_ORIGINS = False  # 모든 도메인을 허용하지 않음
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',  # React 앱의 출처 (프론트엔드 주소)
    'http://127.0.0.1:3000',  # 로컬 주소 (필요한 경우)
    'http://ec2-43-203-221-193.ap-northeast-2.compute.amazonaws.com',  # 배포된 서버 주소
    'https://hereo.netlify.app',
]