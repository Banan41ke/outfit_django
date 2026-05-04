import os
from pathlib import Path

# Корень проекта (D:/PythonProject/outfit_django)
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-_4b6@8%qo*#paqkqo7xj!!2i1nf&ygoj&0wwp-hn=j!!30%(i5'

DEBUG = True

ALLOWED_HOSTS = []

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
    'recommendations',
    'telegram_bot',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'outfit_django.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'outfit_django.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Настройки статики (CSS, JS, логотипы)
STATIC_URL = 'static/'
STATICFILES_DIRS = [
    BASE_DIR / "static", # Здесь лежит твой logo.png
]

# Настройки медиа (фото, которые загружает пользователь через форму)
MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")
DATASET_ROOT = os.path.join(BASE_DIR, "data/raw")

# Пути к твоим данным и моделям (используются в скриптах обработки)
DATA_DIR = BASE_DIR / 'data' # D:/PythonProject/outfit_django/data
MODELS_DIR = BASE_DIR / 'models'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'