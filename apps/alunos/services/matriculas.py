"""Services de matrículas e consolidações."""

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from django.db.models import Count, Min

from apps.alunos import repositories
from apps.alunos.enums import SITUACOES_MATRICULA_VALIDAS
from apps.alunos.models import (
    Aluno,
    Matricula,
    MatriculaAnoAnterior,
    MatriculaTurma,
)
from apps.core.utils import fim_do_dia


def _consolidacao_por_turma(
    ano_letivo: int, ue_codigo: str
) -> list[dict[str, Any]]:
    """Conta matrículas válidas por turma."""
    qs = Matricula.objects.filter(
        ano_letivo=ano_letivo,
        codigo_ue=ue_codigo,
    ).values_list("codigo_matricula", flat=True)
    codigos = list(qs)
    if not codigos:
        return []

    agrupado = (
        MatriculaTurma.objects.filter(
            codigo_matricula__in=codigos,
            codigo_situacao_aluno__in=SITUACOES_MATRICULA_VALIDAS,
        )
        .values("codigo_turma")
        .annotate(quantidade=Count("codigo_matricula", distinct=True))
        .order_by("codigo_turma")
    )
    return list(agrupado)


def obter_matriculas_ano_atual(
    ano_letivo: int, ue_codigo: str
) -> list[dict[str, Any]]:
    """Consolida matrículas válidas do ano atual por turma."""
    return _consolidacao_por_turma(ano_letivo=ano_letivo, ue_codigo=ue_codigo)


def obter_matriculas_anos_anteriores(
    ano_letivo: int, ue_codigo: str
) -> list[dict[str, Any]]:
    """Consolida matrículas válidas de ano anterior por turma."""
    rows = (
        MatriculaAnoAnterior.objects.filter(
            ano_letivo=ano_letivo,
            codigo_ue=ue_codigo,
        )
        .values("codigo_turma", "quantidade")
        .order_by("codigo_turma")
    )
    return list(rows)


def obter_quantidade_alunos_por_turma_da_escola(
    codigo_escola: str,
) -> list[dict[str, Any]]:
    """Lista total de matrículas por turma da escola."""
    ultimo_ano = (
        Matricula.objects.filter(codigo_ue=codigo_escola)
        .order_by("-ano_letivo")
        .values_list("ano_letivo", flat=True)
        .first()
    )
    if ultimo_ano is None:
        return []
    return _consolidacao_por_turma(
        ano_letivo=ultimo_ano, ue_codigo=codigo_escola
    )


def obter_total_matriculas_por_turno_ue(ue_codigo: str) -> list[Any]:
    """Retorna total de matrículas por turno da UE."""
    _ = ue_codigo
    return []


def obter_total_matriculas_por_turno_dre(dre_codigo: str) -> list[Any]:
    """Retorna total de matrículas por turno da DRE."""
    _ = dre_codigo
    return []


def obter_matriculas_aluno_na_escola(
    codigo_escola: str, codigo_aluno: int
) -> list[dict[str, Any]]:
    """Lista matrículas do aluno em uma escola."""
    matriculas = list(
        Matricula.objects.filter(
            codigo_ue=codigo_escola, aluno_id=codigo_aluno
        )
        .values(
            "codigo_matricula",
            "aluno_id",
            "ano_letivo",
            "codigo_situacao_matricula",
            "situacao_matricula",
            "data_situacao_matricula",
        )
        .order_by("-ano_letivo")
    )
    if not matriculas:
        return []

    aluno = (
        Aluno.objects.filter(codigo_aluno=codigo_aluno)
        .values("nome", "nome_social")
        .first()
        or {}
    )
    mts = repositories.matricula_turma_por_matricula(
        [m["codigo_matricula"] for m in matriculas]
    )
    return [
        {
            "matricula": m,
            "aluno": aluno,
            "matricula_turma": mts.get(m["codigo_matricula"], {}),
        }
        for m in matriculas
    ]


def contar_matriculas_turmas_periodo(
    codigos_turmas: Sequence[int],
    data_fim: datetime,
) -> int:
    """Conta alocações válidas nas turmas cuja matrícula começou até a data.

    O grão da contagem é a alocação (matrícula + sequência), não o aluno
    distinto: um aluno com várias alocações válidas conta várias vezes. Só
    entram as alocações em situação regular cuja matrícula tem a primeira
    alocação com data anterior ou igual a ``data_fim``.

    Args:
        codigos_turmas: Códigos EOL das turmas consideradas.
        data_fim: Limite superior para a data de início da matrícula.

    Returns:
        Quantidade de alocações que atendem aos critérios.
    """
    if not codigos_turmas:
        return 0
    alocacoes = list(
        MatriculaTurma.objects.filter(
            codigo_turma__in=codigos_turmas,
            codigo_situacao_aluno__in=SITUACOES_MATRICULA_VALIDAS,
        ).values_list("codigo_matricula", flat=True)
    )
    if not alocacoes:
        return 0
    no_periodo = set(
        MatriculaTurma.objects.filter(codigo_matricula__in=set(alocacoes))
        .values("codigo_matricula")
        .annotate(primeira=Min("data_situacao_aluno_data_hora"))
        .filter(primeira__lte=fim_do_dia(data_fim))
        .values_list("codigo_matricula", flat=True)
    )
    return sum(1 for matricula in alocacoes if matricula in no_periodo)
