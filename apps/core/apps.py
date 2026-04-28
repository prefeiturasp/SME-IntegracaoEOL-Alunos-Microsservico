"""Configuracao do app core."""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    """App de utilitarios compartilhados."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    label = "core"
