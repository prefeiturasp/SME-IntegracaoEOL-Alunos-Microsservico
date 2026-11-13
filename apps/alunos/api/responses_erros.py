"""Funções de ajuda para construir respostas de erro da API."""

from rest_framework import status
from rest_framework.response import Response


def _erro_400(detalhe: str) -> Response:
    """Constrói uma resposta 400 com a mensagem informada."""
    return Response({"detail": detalhe}, status=status.HTTP_400_BAD_REQUEST)


def _erro(
    mensagem: str, http_status: int = status.HTTP_400_BAD_REQUEST
) -> Response:
    """Constrói uma resposta de erro padrão."""
    return Response({"detail": mensagem}, status=http_status)


def _erro_legado(mensagem: str) -> Response:
    """Replica a resposta de erro do legado com a mensagem informada."""
    return Response(mensagem, status=status.HTTP_400_BAD_REQUEST)


# Código de status usado pelo legado nos erros de negócio.
_STATUS_NEGOCIO_LEGADO = 601


def _erro_negocio_legado(mensagem: str) -> Response:
    """Replica o erro de negócio do legado (status 601, corpo string)."""
    resposta = Response(mensagem, status=status.HTTP_400_BAD_REQUEST)
    # O construtor do Django limita o status a 100-599; o legado usa 601,
    # então o código é atribuído após a construção.
    resposta.status_code = _STATUS_NEGOCIO_LEGADO
    return resposta
