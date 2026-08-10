"""Configuracao do app core."""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    """App de utilitarios compartilhados."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    label = "core"

    def ready(self) -> None:
        """Inicializa os recursos compartilhados da aplicação."""
        from sme_sidecar_sdk import runtime

        runtime.configure()
