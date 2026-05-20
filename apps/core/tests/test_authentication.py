"""Testes da autenticação por API Key."""

from __future__ import annotations

from django.test import RequestFactory, TestCase, override_settings
from rest_framework import exceptions

from apps.core.authentication import ApiKeyAuthentication


@override_settings(API_KEY="chave-correta", API_KEY_HEADER="X-API-Key")
class ApiKeyAuthenticationTestCase(TestCase):
    """Valida o fluxo de autenticação por API key."""

    def setUp(self) -> None:
        """Configura o RequestFactory e o autenticador dos testes."""
        self.factory = RequestFactory()
        self.auth = ApiKeyAuthentication()

    def test_sem_header_retorna_none(self) -> None:
        """Verifica que a ausência do header X-API-Key retorna None."""
        request = self.factory.get("/api/alunos")
        self.assertIsNone(self.auth.authenticate(request))

    def test_chave_invalida_lanca_permission_denied(self) -> None:
        """Verifica que uma chave incorreta levanta PermissionDenied."""
        request = self.factory.get(
            "/api/alunos", HTTP_X_API_KEY="chave-errada"
        )
        with self.assertRaises(exceptions.PermissionDenied):
            self.auth.authenticate(request)

    def test_chave_correta_retorna_usuario(self) -> None:
        """Verifica que a chave correta autentica e devolve o usuário."""
        request = self.factory.get(
            "/api/alunos", HTTP_X_API_KEY="chave-correta"
        )
        result = self.auth.authenticate(request)
        self.assertIsNotNone(result)
        assert result is not None
        usuario, token = result
        self.assertTrue(usuario.is_authenticated)
        self.assertIsNone(token)

    def test_authenticate_header_retorna_nome_configurado(self) -> None:
        """Verifica que o header configurado é exposto pelo autenticador."""
        request = self.factory.get("/api/alunos")
        self.assertEqual(self.auth.authenticate_header(request), "X-API-Key")

    def test_api_user_str(self) -> None:
        """Verifica a string amigável do pseudo-usuário."""
        request = self.factory.get(
            "/api/alunos", HTTP_X_API_KEY="chave-correta"
        )
        result = self.auth.authenticate(request)
        assert result is not None
        usuario, _ = result
        self.assertEqual(str(usuario), "api-user")
