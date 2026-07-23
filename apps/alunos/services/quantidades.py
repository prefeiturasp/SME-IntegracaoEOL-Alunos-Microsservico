"""Services de quantidades e agregações de alunos."""

from collections.abc import Sequence
from typing import Any

from django.db.models import F

from apps.alunos import repositories
from apps.alunos.constants import MODALIDADES_CONTRATO, TIPOS_ESCOLA_INFANTIL
from apps.alunos.models import (
    MatriculaAnoLetivo,
    MatriculaComponenteCurricularAnoLetivo,
    MatriculaTurma,
)


def obter_quantidade_matriculados_por_ano_e_cc(
    ano_letivo: int,
    ue_id: str | None = None,
    componentes_curriculares: list[int] | None = None,  # NOSONAR
    dre_id: str | None = None,  # NOSONAR
) -> list[dict[str, Any]]:
    """Agrupa matrículas por turma no ano letivo."""
    return repositories.quantidade_matriculados_por_ano_e_cc(
        ano_letivo=ano_letivo,
        ue_id=ue_id,
        componentes_curriculares=componentes_curriculares,
        dre_id=dre_id,
    )


def obter_quantidade_matriculados(
    ano_letivo: int,
    ue_codigo: str = "",
    dre_codigo: str = "",  # NOSONAR
    modalidade: list[int] | None = None,  # NOSONAR
    ano: list[int] | None = None,  # NOSONAR
    turma: list[str] | None = None,  # NOSONAR
) -> list[dict[str, Any]]:
    """Lista quantidade de matriculados por UE e turma."""
    return repositories.quantidade_matriculados(
        ano_letivo=ano_letivo,
        ue_codigo=ue_codigo,
        dre_codigo=dre_codigo,
        modalidade=modalidade,
        ano=ano,
        turma=turma,
    )


def obter_quantidade_matriculados_cc_contrato(
    ano_letivo: int,
    componentes_curriculares: Sequence[int],
    dre_id: str | None = None,
    ue_id: str | None = None,
) -> list[dict[str, Any]]:
    """Lista matriculados por componente curricular no contrato do legado."""
    qs = MatriculaComponenteCurricularAnoLetivo.objects.filter(
        ano_letivo=ano_letivo,
        componente_curricular_id__in=list(componentes_curriculares),
    )
    if dre_id:
        qs = qs.filter(codigo_dre=dre_id)
    if ue_id:
        qs = qs.filter(codigo_ue=ue_id)
    qs = qs.order_by(
        F("ordem").asc(nulls_first=True),
        "componente_curricular_id",
        "ano",
        "turma",
    )
    return list(
        qs.values(
            "componente_curricular_id",
            "quantidade",
            "ordem",
            "modalidade",
            "ano",
            "turma",
        )
    )


def _pares_ue_turma_por_codigos(
    codigos_turma: Sequence[int],
) -> set[tuple[str, str]]:
    """Resolve códigos de turma em pares (UE, nome da turma)."""
    return {
        (mt["codigo_ue_turma"], mt["nome_turma"])
        for mt in MatriculaTurma.objects.filter(
            codigo_turma__in=list(codigos_turma),
            origem_atual=True,
        ).values("codigo_ue_turma", "nome_turma")
        if mt["codigo_ue_turma"] and mt["nome_turma"]
    }


def obter_quantidade_matriculados_contrato(
    ano_letivo: int,
    dre_codigo: str | None = None,
    ue_codigo: str | None = None,
    modalidade: Sequence[int] | None = None,
    ano: Sequence[int] | None = None,
    turma: Sequence[int] | None = None,
) -> list[dict[str, Any]]:
    """Lista a quantidade de matriculados no contrato do legado."""
    qs = MatriculaAnoLetivo.objects.filter(ano_letivo=ano_letivo)
    if dre_codigo:
        qs = qs.filter(codigo_dre=dre_codigo)
    if ue_codigo:
        qs = qs.filter(codigo_ue=ue_codigo)
    if ano and -99 not in ano:
        qs = qs.filter(ano__in=[str(a) for a in ano])
    for codigo_modalidade in modalidade or []:
        if codigo_modalidade not in MODALIDADES_CONTRATO:
            continue
        qs = qs.filter(codigo_modalidade=codigo_modalidade)
        if codigo_modalidade == 1:
            qs = qs.filter(tipo_escola__in=TIPOS_ESCOLA_INFANTIL)

    pares_turma = _pares_ue_turma_por_codigos(turma) if turma else None

    saida: list[dict[str, Any]] = []
    for r in qs.values(
        "quantidade",
        "ordem",
        "modalidade",
        "ano",
        "turma",
        "codigo_dre",
        "codigo_ue",
    ):
        if (
            pares_turma is not None
            and (r["codigo_ue"], r["turma"]) not in pares_turma
        ):
            continue
        saida.append(r)
    return saida
