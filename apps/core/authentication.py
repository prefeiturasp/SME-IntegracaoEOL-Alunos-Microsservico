"""Autenticação por API Key."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.conf import settings
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication
from rest_framework.permissions import IsAuthenticated

if TYPE_CHECKING:
    from rest_framework.request import Request


class _ApiAuth:
    """Pseudo-usuário para autenticação via API Key."""

    is_authenticated = True
    is_active = True
    is_staff = False
    is_anonymous = False

    def __str__(self) -> str:
        return "api-user"


class ApiKeyAuthentication(BaseAuthentication):
    """Valida requisições via API Key."""

    def authenticate(self, request: Request) -> tuple[_ApiAuth, None] | None:
        """Autentica a requisição pelo header de API Key.

        Args:
            request: Requisição recebida pela view.

        Returns:
            Par com o pseudo-usuário autenticado e credencial vazia, ou
            ``None`` quando o header não foi enviado.

        Raises:
            PermissionDenied: Se a API Key recebida não for igual à
                configurada.
        """
        header_name = getattr(settings, "API_KEY_HEADER", "x-api-key")
        api_key = getattr(settings, "API_KEY", "")
        meta_key = "HTTP_" + header_name.upper().replace("-", "_")
        key_fornecida = request.META.get(meta_key)

        if key_fornecida is None:
            return None
        if key_fornecida != api_key:
            raise exceptions.PermissionDenied("API Key inválida.")
        return (_ApiAuth(), None)

    def authenticate_header(self, request: Request) -> str:
        """Retorna o header de autenticação esperado."""
        return getattr(settings, "API_KEY_HEADER", "x-api-key")


ApiKeyPermission = IsAuthenticated
