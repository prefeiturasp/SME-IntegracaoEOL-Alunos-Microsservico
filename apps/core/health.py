"""Endpoints de health check."""

import time

from django.db import connection
from django.db.utils import OperationalError
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

_VERSION = "1.0.0"


def _db_ok() -> tuple[bool, float]:
    """Testa a conexão com o banco de dados.

    Returns:
        Tupla com status da conexão e latência em milissegundos.
    """
    t0 = time.monotonic()
    try:
        connection.ensure_connection()
        return True, round((time.monotonic() - t0) * 1000, 2)
    except OperationalError:
        return False, round((time.monotonic() - t0) * 1000, 2)


class HealthView(APIView):
    """Retorna o status detalhado do serviço."""

    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Verificar health",
        tags=["Health"],
        responses={200: OpenApiTypes.OBJECT, 503: OpenApiTypes.OBJECT},
    )
    def get(self, _request: Request) -> Response:
        """Retorna o status geral do serviço.

        Args:
            _request: Requisição HTTP recebida.

        Returns:
            Resposta com status geral e dependências essenciais.
        """
        db_ok, db_ms = _db_ok()
        payload = {
            "status": "ok" if db_ok else "degraded",
            "version": _VERSION,
            "checks": {
                "database": {"ok": db_ok, "latency_ms": db_ms},
            },
        }
        return Response(payload, status=200 if db_ok else 503)
