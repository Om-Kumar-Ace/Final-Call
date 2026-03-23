import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# --- SECURITY ---
SECRET_KEY = os.getenv('SECRET_KEY', 'fallback-secret-key')
DEBUG = os.getenv('DEBUG', 'False') == 'True'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '*').split(',')

# --- APPS ---
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'auction_engine',
    "corsheaders",
]

# --- MIDDLEWARE ---
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # correct position ✅
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    "corsheaders.middleware.CorsMiddleware",
]

ROOT_URLCONF = 'sports_auction.urls'

# --- TEMPLATES ---
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # cleaner ✅
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'sports_auction.wsgi.application'

# --- DATABASE (SQLITE - FIXED) ---
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# --- PASSWORD VALIDATION ---
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# --- STATIC FILES ---
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# WhiteNoise storage (good for deployment)
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# --- INTERNATIONAL ---
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",   
    "http://127.0.0.1:3000",   
    "https://tp3gjtch-8000.inc1.devtunnels.ms",  
    "http://localhost:8000",   
    "http://127.0.0.1:8000", 
    "https://tp3gjtch-3000.inc1.devtunnels.ms"
]

CORS_ALLOW_ALL_ORIGINS = True

CORS_ALLOW_HEADERS = [
    "content-type",
    "authorization",
    "x-csrftoken",
    "accept",
    "origin",
]
