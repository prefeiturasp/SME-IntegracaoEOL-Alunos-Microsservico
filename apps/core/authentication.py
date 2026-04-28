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
        """Autentica via header configurado (RFC 7235)."""
        header_name = getattr(settings, "API_KEY_HEADER", "x-api-key")
        api_key = getattr(settings, "API_KEY", "")
        meta_key = "HTTP_" + header_name.upper().replace("-", "_")
        key_fornecida = request.META.get(meta_key)

        if key_fornecida is None:
            return None
        if key_fornecida != api_key:
            raise exceptions.AuthenticationFailed("API Key inválida.")
        return (_ApiAuth(), None)

    def authenticate_header(self, request: Request) -> str:
        """Retorna header esperado para 401."""
        return getattr(settings, "API_KEY_HEADER", "x-api-key")


ApiKeyPermission = IsAuthenticated
