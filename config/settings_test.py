"""Settings de teste — força SQLite em memória.

Usado por ``manage.py test --settings=config.settings_test``. Os models
do app ``alunos`` declaram ``Meta.managed = False`` em produção (DDL
gerada pelo MS-ETL); o ``AlunosTestRunner`` marca todos os models como
gerenciáveis antes do ``setup_databases`` para que o schema seja criado
em SQLite e os testes possam manipular dados normalmente.
"""

from config.settings import *  # noqa: F401,F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

API_KEY = "test-api-key"

TEST_RUNNER = "config.test_runner.AlunosTestRunner"
