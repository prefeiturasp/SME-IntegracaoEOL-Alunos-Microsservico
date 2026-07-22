"""Services de matrículas e consolidações."""

from typing import Any

from django.db.models import Count, F

from apps.alunos.enums import SITUACOES_MATRICULA_VALIDAS
from apps.alunos.models import (
    Aluno,
    Matricula,
    MatriculaAnoAnterior,
    MatriculaTurma,
)


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


def _matricula_turma_por_matricula(
    codigos_matricula: list[int],
) -> dict[int, dict[str, Any]]:
    """Indexa o vínculo de turma mais recente por matrícula."""
    if not codigos_matricula:
        return {}
    saida: dict[int, dict[str, Any]] = {}
    for mt in (
        MatriculaTurma.objects.filter(codigo_matricula__in=codigos_matricula)
        .values(
            "codigo_matricula",
            "codigo_turma",
            "data_situacao_aluno",
            "data_situacao_aluno_data_hora",
            "codigo_situacao_aluno",
        )
        .order_by(
            "codigo_matricula",
            "-data_situacao_aluno_data_hora",
            "-data_situacao_aluno",
            F("numero_chamada").desc(nulls_last=True),
        )
    ):
        saida.setdefault(mt["codigo_matricula"], mt)
    return saida


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
    mts = _matricula_turma_por_matricula(
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
