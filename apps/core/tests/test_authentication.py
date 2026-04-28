"""Testes da autenticação por API Key."""

from __future__ import annotations

from django.test import RequestFactory, TestCase, override_settings
from rest_framework import exceptions

from apps.core.authentication import ApiKeyAuthentication


@override_settings(API_KEY="chave-correta", API_KEY_HEADER="X-API-Key")
class ApiKeyAuthenticationTestCase(TestCase):
    def setUp(self) -> None:
        self.factory = RequestFactory()
        self.auth = ApiKeyAuthentication()

    def test_sem_header_retorna_none(self) -> None:
        request = self.factory.get("/api/alunos")
        self.assertIsNone(self.auth.authenticate(request))

    def test_chave_invalida_lanca_permission_denied(self) -> None:
        request = self.factory.get(
            "/api/alunos", HTTP_X_API_KEY="chave-errada"
        )
        with self.assertRaises(exceptions.PermissionDenied):
            self.auth.authenticate(request)

    def test_chave_correta_retorna_usuario(self) -> None:
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
        request = self.factory.get("/api/alunos")
        self.assertEqual(self.auth.authenticate_header(request), "X-API-Key")

    def test_api_user_str(self) -> None:
        request = self.factory.get("/api/alunos", HTTP_X_API_KEY="chave-correta")
        result = self.auth.authenticate(request)
        assert result is not None
        usuario, _ = result
        self.assertEqual(str(usuario), "api-user")
