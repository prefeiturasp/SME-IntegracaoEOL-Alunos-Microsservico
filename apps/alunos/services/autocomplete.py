"""Services de autocomplete de alunos."""

from collections.abc import Iterator, Sequence
from datetime import date, datetime
from typing import Any

from django.db.models import Q
from django.utils import timezone

from apps.alunos.enums import (
    SITUACOES_MATRICULA_ATIVAS_TURMA,
    SITUACOES_MATRICULA_VALIDAS,
)
from apps.alunos.models import Matricula, MatriculaTurma
from apps.alunos.repositories import alunos_indexados


def _mts_autocomplete_ue(
    codigo_ue: str,
    ano_letivo: int,
    historico: bool,
) -> list[dict[str, Any]]:
    """Lista vínculos de turma regular da UE para o autocomplete."""
    qs = MatriculaTurma.objects.filter(
        codigo_ue_turma=codigo_ue,
        codigo_tipo_turma=1,
        origem_atual=not historico,
    )
    if ano_letivo:
        qs = qs.filter(ano_letivo_turma=ano_letivo)
    if not historico:
        qs = qs.filter(
            codigo_situacao_aluno__in=SITUACOES_MATRICULA_VALIDAS,
            codigo_etapa_ensino__isnull=False,
        )
    return list(
        qs.values("codigo_matricula", "codigo_turma", "numero_chamada")
    )


def _alunos_com_turma_programa(codigo_turmas: Sequence[int]) -> set[int]:
    """Identifica alunos com vínculo corrente de turma-programa nas turmas."""
    codigos = list(
        MatriculaTurma.objects.filter(
            codigo_turma__in=list(codigo_turmas),
            origem_atual=True,
        )
        .exclude(codigo_tipo_turma=1)
        .values_list("codigo_matricula", flat=True)
    )
    if not codigos:
        return set()
    return set(
        Matricula.objects.filter(
            codigo_matricula__in=codigos, origem_atual=True
        ).values_list("aluno_id", flat=True)
    )


def _matriculas_autocomplete_idx(
    codigos_matricula: list[int],
    historico: bool,
    nome_aluno: str | None,
    codigo_eol: str | None,
) -> dict[int, dict[str, Any]]:
    """Indexa matrículas do autocomplete com dados do aluno."""
    if not codigos_matricula:
        return {}
    qs = Matricula.objects.filter(
        codigo_matricula__in=codigos_matricula,
        origem_atual=not historico,
    )
    if historico:
        qs = qs.filter(
            codigo_situacao_matricula__in=SITUACOES_MATRICULA_VALIDAS
        )
    if codigo_eol:
        try:
            qs = qs.filter(aluno_id=int(codigo_eol))
        except (TypeError, ValueError):
            return {}
    if nome_aluno and nome_aluno.strip():
        qs = qs.filter(aluno__nome__icontains=nome_aluno.strip())
    return {
        m["codigo_matricula"]: m
        for m in qs.values(
            "codigo_matricula",
            "aluno_id",
            "aluno__nome",
            "aluno__nome_social",
        )
    }


def _autocomplete_aceita_turma(
    codigo_turma: int,
    aluno_id: int,
    codigo_turmas: Sequence[int] | None,
    alunos_programa: set[int],
) -> bool:
    """Aplica o filtro de turmas do autocomplete."""
    if not codigo_turmas:
        return True
    return codigo_turma in codigo_turmas or aluno_id in alunos_programa


def _numero_chamada_autocomplete(numero_chamada: str | None) -> str:
    """Normaliza o número de chamada no formato numérico do legado."""
    if numero_chamada and numero_chamada.strip().isdigit():
        return str(int(numero_chamada))
    return numero_chamada or "0"


def _iter_autocomplete_validos(
    mts: Sequence[dict],
    matriculas_idx: dict[int, dict],
    codigo_turmas: Sequence[int] | None,
    alunos_programa: set[int],
) -> Iterator[tuple[dict, dict]]:
    """Gera pares turma-matrícula aceitos pelos filtros."""
    for mt in mts:
        matricula = matriculas_idx.get(mt["codigo_matricula"])
        if matricula is None:
            continue
        if _autocomplete_aceita_turma(
            mt["codigo_turma"],
            matricula["aluno_id"],
            codigo_turmas,
            alunos_programa,
        ):
            yield mt, matricula


def buscar_alunos_autocomplete(
    codigo_ue: str,
    ano_letivo: int,
    codigo_turmas: Sequence[int] | None = None,
    nome_aluno: str | None = None,
    codigo_eol: str | None = None,
    somente_ativos: bool = False,  # NOSONAR
    eh_historico: bool = False,
    limite: int = 10,
) -> list[dict[str, Any]]:
    """Busca alunos para autocomplete da UE/ano."""
    ano_corrente = timezone.now().year
    if ano_letivo:
        ramos = [eh_historico or ano_letivo != ano_corrente]
    else:
        ramos = [False, True]

    alunos_programa: set[int] = (
        _alunos_com_turma_programa(codigo_turmas) if codigo_turmas else set()
    )

    saida: list[dict[str, Any]] = []
    vistos: set[tuple[int, int]] = set()
    for historico in ramos:
        mts = _mts_autocomplete_ue(codigo_ue, ano_letivo, historico)
        matriculas_idx = _matriculas_autocomplete_idx(
            [mt["codigo_matricula"] for mt in mts],
            historico,
            nome_aluno,
            codigo_eol,
        )
        for mt, matricula in _iter_autocomplete_validos(
            mts, matriculas_idx, codigo_turmas, alunos_programa
        ):
            chave = (matricula["aluno_id"], mt["codigo_turma"])
            if chave in vistos:
                continue
            vistos.add(chave)
            saida.append(
                {
                    "matricula": matricula,
                    "matricula_turma": {
                        **mt,
                        "numero_chamada": _numero_chamada_autocomplete(
                            mt["numero_chamada"]
                        ),
                    },
                }
            )
            if len(saida) >= limite:
                return saida
    return saida


def _qs_matriculas_ativas_ue(
    ue_codigo: str,
    referencia: date | None,
    aluno_codigo: int,
    nome_l: str,
) -> Any:
    """Monta o queryset de matrículas ativas da UE para autocomplete."""
    qs = Matricula.objects.filter(codigo_ue=ue_codigo)
    if referencia is not None:
        qs = qs.filter(
            Q(codigo_situacao_matricula__in=SITUACOES_MATRICULA_VALIDAS)
            | Q(data_situacao_matricula__gt=referencia)
        )
    else:
        qs = qs.filter(
            codigo_situacao_matricula__in=SITUACOES_MATRICULA_VALIDAS
        )
    if aluno_codigo:
        qs = qs.filter(aluno_id=aluno_codigo)
    if nome_l:
        qs = qs.filter(aluno__nome__icontains=nome_l)
    return qs.order_by("aluno__nome", "aluno__nome_social")


def _mts_ativas_idx(
    codigos_matricula: list[int],
) -> dict[int, dict[str, Any]]:
    """Indexa matrículas-turma ativas regulares por matrícula."""
    mts = (
        MatriculaTurma.objects.filter(
            codigo_matricula__in=codigos_matricula,
            codigo_situacao_aluno__in=SITUACOES_MATRICULA_ATIVAS_TURMA,
            codigo_etapa_ensino__isnull=False,
        )
        .exclude(codigo_tipo_turma=3)
        .values(
            "codigo_matricula",
            "codigo_turma",
            "numero_chamada",
            "codigo_tipo_turma",
            "nome_turma",
            "codigo_etapa_ensino",
        )
        .order_by("codigo_matricula")
    )
    return {mt["codigo_matricula"]: mt for mt in mts}


def _linhas_autocomplete_ativos(
    matriculas: list[dict[str, Any]],
    mts_idx: dict[int, dict[str, Any]],
    nome_l: str,
    limite: int,
) -> list[dict[str, Any]]:
    """Agrupa os registros de autocomplete de alunos ativos."""
    alunos_idx = alunos_indexados([m["aluno_id"] for m in matriculas])
    saida: list[dict[str, Any]] = []
    for m in sorted(
        matriculas,
        key=lambda item: (
            alunos_idx.get(item["aluno_id"], {}).get("nome", ""),
            alunos_idx.get(item["aluno_id"], {}).get("nome_social") or "",
        ),
    ):
        a = alunos_idx.get(m["aluno_id"], {})
        nome = a.get("nome") or ""
        if nome_l and nome_l not in nome.lower():
            continue
        mt = mts_idx[m["codigo_matricula"]]
        saida.append(
            {
                "matricula": m,
                "matricula_turma": mt,
                "aluno": a,
            }
        )
        if len(saida) >= limite:
            break
    return saida


def buscar_alunos_ativos_autocomplete(
    ue_codigo: str,
    aluno_nome: str | None = None,
    aluno_codigo: int = 0,
    data_referencia: datetime | date | None = None,
    limite: int = 10,
) -> list[dict[str, Any]]:
    """Busca alunos ativos para autocomplete."""
    referencia = (
        data_referencia.date()
        if isinstance(data_referencia, datetime)
        else data_referencia
    )
    nome_l = (aluno_nome or "").strip().lower()
    qs = _qs_matriculas_ativas_ue(ue_codigo, referencia, aluno_codigo, nome_l)
    matriculas = list(
        qs.values("codigo_matricula", "aluno_id", "codigo_ue")[: limite + 500]
    )
    if not matriculas:
        return []

    mts_idx = _mts_ativas_idx([m["codigo_matricula"] for m in matriculas])
    matriculas = [m for m in matriculas if m["codigo_matricula"] in mts_idx]
    if not matriculas:
        return []

    return _linhas_autocomplete_ativos(matriculas, mts_idx, nome_l, limite)
