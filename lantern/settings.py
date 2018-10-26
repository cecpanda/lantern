"""
Django settings for lantern project.

Generated by 'django-admin startproject' using Django 2.0.6.

For more information on this file, see
https://docs.djangoproject.com/en/2.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.0/ref/settings/
"""

import os
import sys
import datetime

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, 'apps'))
sys.path.insert(0, os.path.join(BASE_DIR, 'extra_apps'))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '8bi*l9+epvlwxn+i&np-1^+#xfdlo4d^!-5y8#x=g0+vwoggmw'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["*"]


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'corsheaders',
    'xadmin',
    'crispy_forms',
    'simditor',

    'rest_framework',
    'django_filters',
    # 'rest_framework_filters',

    'account.apps.AccountConfig',
    'tft.apps.TftConfig',
    'action.apps.ActionConfig',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'lantern.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
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

WSGI_APPLICATION = 'lantern.wsgi.application'


# Database
# https://docs.djangoproject.com/en/2.0/ref/settings/#databases
#
DATABASES = {
    # 'default': {
    #     'ENGINE': 'django.db.backends.mysql',
    #     'NAME': 'db_array',
    #     'USER': 'cim',
    #     'PASSWORD': 'cim',
    #     'HOST': '10.53.141.252',
    #     'PORT': 3306,
    # },
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'default.sqlite3'),
        'TEST': {
            'NAME': os.path.join(BASE_DIR, 'test.sqlite3'),
        }
    },
    'db': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}


# Password validation
# https://docs.djangoproject.com/en/2.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/2.0/topics/i18n/

LANGUAGE_CODE = 'zh-hans'

TIME_ZONE = 'Asia/Shanghai'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.0/howto/static-files/

STATIC_URL = '/static/'

STATIC_ROOT = os.path.join(BASE_DIR, 'static')

STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'common_static'),
)


# CORS
CORS_ORIGIN_ALLOW_ALL = True


AUTH_USER_MODEL = 'account.User'

# CACHES = {
#     "default": {
#         "BACKEND": "django_redis.cache.RedisCache",
#         "LOCATION": "redis://127.0.0.1:6379/0",
#         "OPTIONS": {
#             "CLIENT_CLASS": "django_redis.client.DefaultClient",
#         }
#     }
# }

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework_jwt.authentication.JSONWebTokenAuthentication',
    ),
    # 分页还是别全局设置了
    # 'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    # 'PAGE_SIZE': 2,
    # 'DEFAULT_PERMISSION_CLASSES': (
    #         'rest_framework.permissions.IsAuthenticated',
    #     )
    'DATETIME_FORMAT': 'iso-8601',
    'DATETIME_INPUT_FORMATS': ('iso-8601',),
    'UPLOADED_FILES_USE_URL': True,
    # 'UPLOADED_FILES_USE_PREFIX': 'http://10.53.141.255',
    }

JWT_AUTH = {
    'JWT_ALLOW_REFRESH': True,
    'JWT_EXPIRATION_DELTA': datetime.timedelta(days=7),
    'JWT_RESPONSE_PAYLOAD_HANDLER': 'account.utils.jwt_response_payload_handler',
    'JWT_LEEWAY': datetime.timedelta(hours=2)
}

REST_FRAMEWORK_EXTENSIONS = {
    'DEFAULT_CACHE_RESPONSE_TIMEOUT': 60
}

# media
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, "media")


# simditor
SIMDITOR_UPLOAD_PATH = 'uploads/'
SIMDITOR_IMAGE_BACKEND = 'pillow'

SIMDITOR_TOOLBAR = [
    'title', 'bold', 'italic', 'underline', 'strikethrough', 'fontScale',
    'color', '|', 'ol', 'ul', 'blockquote', 'code', 'table', '|', 'link',
    'image', 'hr', '|', 'indent', 'outdent', 'alignment', 'fullscreen',
    'markdown', 'emoji'
]

SIMDITOR_CONFIGS = {
    'toolbar': SIMDITOR_TOOLBAR,
    'upload': {
        'url': '/simditor/upload/',
        'fileKey': 'upload'
    },
    'emoji': {
        'imagePath': '/static/simditor/images/emoji/'
    }
}

# Group Code
# 为方便扩展，必须和数据库中定义的yizhi，大小写敏感
GROUP_CODE = {
    'TFT': {
        'MFG': 'A1M',
        'PVD': 'A2P',
        'CVD': 'A2C',
        'PHO': 'A3E',
        'DRY': 'A4D',
        'WET': 'A4W',
        'TEST': 'A5I',
        'QC': 'A6I'
    },
    'LCD': {
        'PI': ''
    }
}
