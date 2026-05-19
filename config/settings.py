"""Configurações Django do SME-IntegracaoEOL-Alunos-Microsservico.

Microsserviço de leitura/escrita do domínio Alunos (alunos, matrículas,
turmas, responsáveis, necessidades especiais). Lê do banco alunos_db,
populado pelo SME-IntegracaoEOL-MS-ETL. As escritas (PUT/POST de
responsáveis) são gravadas em tabelas do próprio domínio mantidas por
este microsserviço.
"""

import os
import sys
import urllib.parse
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent

DB_POOL_SIZE = int(os.environ.get("DB_POOL_SIZE", "5"))
_POOL_OPTIONS = {
    "POOL_SIZE": DB_POOL_SIZE,
    "MAX_OVERFLOW": 0,
    "POOL_TIMEOUT": 30,
    "POOL_RECYCLE": 1800,
    "PRE_PING": True,
}


def _parse_db_url(url: Any) -> dict:
    """Faz o parse de uma URL postgres para dict de configuração Django."""
    if not url:
        return {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }

    if isinstance(url, bytes):
        url = url.decode("utf-8")

    parsed = urllib.parse.urlparse(str(url))
    return {
        "ENGINE": "dj_db_conn_pool.backends.postgresql",
        "NAME": parsed.path.lstrip("/"),
        "USER": parsed.username or "postgres",
        "PASSWORD": parsed.password or "postgres",
        "HOST": parsed.hostname or "localhost",
        "PORT": str(parsed.port or 5432),
        "POOL_OPTIONS": _POOL_OPTIONS,
    }


SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY", "dev-secret-not-for-production"
)

DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "*").split(",")
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "apps.core",
    "apps.alunos",
]

MIDDLEWARE = [
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
ASGI_APPLICATION = "config.asgi.application"

URL_BANCO_ALUNOS = os.environ.get("URL_BANCO_ALUNOS")

DATABASES = {
    "default": _parse_db_url(URL_BANCO_ALUNOS),
}

MODO_TESTE = "test" in sys.argv or os.environ.get(
    "USE_SQLITE_TEST", "False"
).lower() in ("true", "1")
if MODO_TESTE:
    DATABASES["default"] = {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }

TEST_RUNNER = "config.test_runner.AlunosTestRunner"

AUTH_PASSWORD_VALIDATORS: list[dict[str, object]] = []

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

NOME_APLICACAO = os.environ.get(
    "NOME_APLICACAO", "SME-IntegracaoEOL-Alunos-Microsservico"
)
AMBIENTE_APLICACAO = os.environ.get("AMBIENTE_APLICACAO", "local")
NIVEL_LOG = os.environ.get("NIVEL_LOG", "INFO")

API_KEY = (
    "test-api-key"
    if MODO_TESTE
    else os.environ.get("API_KEY", "dev-key-default")
)
API_KEY_HEADER = os.environ.get("API_KEY_HEADER", "X-API-Key")

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.core.authentication.ApiKeyAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

SPECTACULAR_SETTINGS = {
    "TITLE": "SME-IntegracaoEOL-Alunos-Microsservico API",
    "DESCRIPTION": (
        "Endpoints do domínio Alunos (alunos, matrículas, turmas, "
        "responsáveis, necessidades especiais).\n\n"
        "Substituem os endpoints legados do Pedagogico-API "
        "(AlunoController, MatriculaController e os endpoints E05/E24 "
        "do EscolaController) que hoje consultam EOL/Elastic. Os dados "
        "vêm de alunos_db, populado pelo SME-IntegracaoEOL-MS-ETL.\n\n"
        "Consumido pelo Transition Gateway, que agrega dados deste "
        "microsserviço com os domínios Pedagógico e Programas."
    ),
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "APPEND_COMPONENTS": {
        "securitySchemes": {
            "ApiKeyAuth": {
                "type": "apiKey",
                "in": "header",
                "name": API_KEY_HEADER,
            }
        }
    },
    "SECURITY": [{"ApiKeyAuth": []}],
    "SWAGGER_UI_SETTINGS": {"syntaxHighlight": False},
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "padrao": {
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "padrao",
        }
    },
    "root": {
        "handlers": ["console"],
        "level": NIVEL_LOG,
    },
}
