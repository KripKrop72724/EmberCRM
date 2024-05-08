from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

TENANT_URLS = {
    "stage.localhost": "stage",
    # "test.ember.local": "test"
}

# Database
# https://docs.djangoproject.com/en/4.0/ref/settings/#databases
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    },
    'stage': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'staging_db',
        'USER': 'postgres',
        'PASSWORD': '1234',
        'HOST': 'localhost',
        'PORT': '5432',
    },
    # 'test': {
    #     'ENGINE': 'django.db.backends.postgresql_psycopg2',
    #     'NAME': 'testing_db',
    #     'USER': 'postgres',
    #     'PASSWORD': '1234',
    #     'HOST': 'localhost',
    #     'PORT': '5432',
    # },
}