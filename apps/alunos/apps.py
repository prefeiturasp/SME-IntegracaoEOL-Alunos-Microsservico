"""Configuração do app alunos."""

from django.apps import AppConfig


class AlunosConfig(AppConfig):
    """App de leitura/escrita do domínio Alunos.

    Lê dados consolidados de alunos_db, populado pelo
    SME-IntegracaoEOL-MS-ETL. Escritas (PUT/POST de responsáveis) são
    persistidas em tabelas próprias do domínio mantidas por este
    microsserviço.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.alunos"
    label = "alunos"
