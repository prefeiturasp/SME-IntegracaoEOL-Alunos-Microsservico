"""Testes dos endpoints de health check."""

from unittest.mock import patch

from django.test import Client, SimpleTestCase


class HealthCheckTest(SimpleTestCase):
    """Valida respostas públicas de health check."""

    def setUp(self) -> None:
        self.client = Client()

    @patch("apps.core.health._db_ok", return_value=(True, 1.2))
    def test_health_retorna_dependencias(self, _db_ok) -> None:
        response = self.client.get("/api/v1/alunos/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["checks"]["database"]["ok"], True)

    @patch("apps.core.health._db_ok", return_value=(False, 1.2))
    def test_health_retorna_degraded_quando_banco_falha(self, _db_ok) -> None:
        response = self.client.get("/api/v1/alunos/health/")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["status"], "degraded")
