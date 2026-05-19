"""Configuração do app core de alunos."""

from django.apps import AppConfig


class AlunosConfig(AppConfig):
    """App de leitura do domínio Alunos."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.alunos"
    label = "alunos"
