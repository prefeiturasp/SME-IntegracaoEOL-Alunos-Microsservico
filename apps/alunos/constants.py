"""Constantes e mapeamentos simples do domínio Alunos."""

from datetime import datetime

DATA_DEFAULT_LEGADO = datetime(1, 1, 1)
DATA_PADRAO_LEGADO = "0001-01-01T00:00:00"

CODIGOS_RACA = {
    "BRANCA": 1,
    "PRETA": 2,
    "PARDA": 3,
    "AMARELA": 4,
    "INDIGENA": 5,
    "INDÍGENA": 5,
    "NAO INFORMADA": 6,
    "NÃO INFORMADA": 6,
}

MODALIDADE_POR_ETAPA = {
    1: "EI",
    2: "EJA",
    3: "EJA",
    7: "EJA",
    11: "EJA",
    4: "EF",
    5: "EF",
    12: "EF",
    13: "EF",
    6: "EM",
    8: "EM",
    9: "EM",
    14: "EM",
    17: "EM",
}

TIPOS_ESCOLA_INFANTIL = (2, 17, 28, 31)
MODALIDADES_CONTRATO = {1, 3, 5, 6}


def codigo_raca(raca_cor: str | None) -> int | None:
    """Retorna o código legado da raça/cor quando conhecido."""
    if not raca_cor:
        return None
    return CODIGOS_RACA.get(raca_cor.strip().upper())
