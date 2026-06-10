"""Utilitários genéricos compartilhados entre apps."""

from datetime import date, datetime
from typing import cast

from django.utils import timezone
from rest_framework.request import Request


def to_int(valor: str, nome_param: str) -> int:
    """Transforma um path/query param em inteiro.

    Args:
        valor: Valor recebido na URL.
        nome_param: Nome usado na mensagem de erro.

    Returns:
        Valor convertido para inteiro.

    Raises:
        ValueError: Se ``valor`` não puder ser convertido.
    """
    try:
        return int(valor)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Parâmetro '{nome_param}' deve ser um inteiro válido: "
            f"recebido {valor!r}."
        ) from exc


def to_bool(valor: str, nome_param: str) -> bool:
    """Transforma um path/query param em booleano.

    Args:
        valor: Valor recebido (``true``/``false`` e variantes em PT/EN).
        nome_param: Nome usado na mensagem de erro.

    Returns:
        Valor convertido para booleano.

    Raises:
        ValueError: Se ``valor`` for ``None`` ou não representar booleano.
    """
    if valor is None:
        raise ValueError(f"Parâmetro '{nome_param}' obrigatório.")
    val = str(valor).strip().lower()
    if val in ("true", "1", "t", "yes", "sim"):
        return True
    if val in ("false", "0", "f", "no", "nao", "não"):
        return False
    raise ValueError(
        f"Parâmetro '{nome_param}' deve ser booleano: recebido {valor!r}."
    )


def to_datetime(valor: str, nome_param: str) -> datetime:
    """Transforma um path/query param em datetime.

    Aceita formato ISO 8601 com ou sem horário; ``Z`` é tratado como UTC.

    Args:
        valor: Valor recebido na URL.
        nome_param: Nome usado na mensagem de erro.

    Returns:
        Valor convertido para datetime.

    Raises:
        ValueError: Se o valor não for uma data ISO válida.
    """
    try:
        if "T" in valor or " " in valor:
            return datetime.fromisoformat(valor.replace("Z", "+00:00"))
        return datetime.strptime(valor, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError(
            f"Parâmetro '{nome_param}' deve ser uma data ISO 8601 válida:"
            f" recebido {valor!r}."
        ) from exc


def query_int_list(request: Request, nome: str) -> list[int]:
    """Extrai uma lista de inteiros da query string.

    Args:
        request: Requisição DRF.
        nome: Nome do parâmetro repetível.

    Returns:
        Inteiros recebidos, ignorando entradas vazias.

    Raises:
        ValueError: Se qualquer entrada não puder ser convertida.
    """
    raw = request.query_params.getlist(nome)
    saida: list[int] = []
    for v in raw:
        if v == "":
            continue
        try:
            saida.append(int(v))
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Parâmetro '{nome}' deve conter inteiros: recebido {v!r}."
            ) from exc
    return saida


def calcular_idade(
    nascimento: date | datetime | None, referencia: date | None = None
) -> int | None:
    """Calcula idade em anos completos.

    Args:
        nascimento: Data de nascimento usada no cálculo.
        referencia: Data de referência. Quando ausente, usa a data atual.

    Returns:
        Idade calculada, ou ``None`` quando não houver nascimento.
    """
    if nascimento is None:
        return None
    if isinstance(nascimento, datetime):
        nascimento = nascimento.date()
    ref = referencia or timezone.now().date()
    idade = ref.year - nascimento.year
    if (ref.month, ref.day) < (nascimento.month, nascimento.day):
        idade -= 1
    return idade


def numero_chamada_int(numero_chamada: str | None) -> int | None:
    """Transforma número de chamada em inteiro, preservando ausência.

    Args:
        numero_chamada: Número de chamada como texto, ou ``None``.

    Returns:
        Número convertido, ou ``None`` quando vazio ou inválido.
    """
    if numero_chamada in (None, ""):
        return None
    try:
        return int(cast(str, numero_chamada))
    except (TypeError, ValueError):
        return None
