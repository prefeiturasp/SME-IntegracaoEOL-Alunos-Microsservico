"""Services de autocomplete de alunos."""

from collections import defaultdict
from collections.abc import Iterator, Sequence
from datetime import date, datetime
from typing import Any

from django.db.models import Q, QuerySet
from django.utils import timezone

from apps.alunos.constants import MODALIDADE_POR_ETAPA
from apps.alunos.enums import (
    SITUACOES_MATRICULA_ATIVAS_TURMA,
    SITUACOES_MATRICULA_VALIDAS,
)
from apps.alunos.models import Matricula, MatriculaTurma


def _mts_autocomplete_ue(
    codigo_ue: str,
    ano_letivo: int,
    historico: bool,
    matriculas: QuerySet[Matricula] | None = None,
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
    if matriculas is not None:
        qs = qs.filter(
            codigo_matricula__in=matriculas.values("codigo_matricula")
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


def _matriculas_autocomplete_qs(
    historico: bool,
    nome_aluno: str | None,
    codigo_aluno: int | None,
) -> QuerySet[Matricula]:
    """Seleciona matrículas pela origem e pelos filtros de aluno.

    Args:
        historico: Indica a consulta a matrículas históricas.
        nome_aluno: Trecho do nome, desconsiderando espaços nas extremidades.
        codigo_aluno: Código do aluno, quando informado.

    Returns:
        Matrículas que atendem aos filtros, sem avaliar a consulta.
    """
    qs = Matricula.objects.filter(origem_atual=not historico)
    if historico:
        qs = qs.filter(
            codigo_situacao_matricula__in=SITUACOES_MATRICULA_VALIDAS
        )
    if codigo_aluno is not None:
        qs = qs.filter(aluno_id=codigo_aluno)
    if nome_aluno and nome_aluno.strip():
        qs = qs.filter(aluno__nome__icontains=nome_aluno.strip())
    return qs


def _matriculas_autocomplete_idx(
    codigos_matricula: list[int],
    matriculas: QuerySet[Matricula],
) -> dict[int, dict[str, Any]]:
    """Indexa as matrículas selecionadas com os nomes dos alunos.

    Args:
        codigos_matricula: Códigos com vínculo elegível de turma.
        matriculas: Consulta com os filtros de aluno e origem.

    Returns:
        Dados de identificação indexados pelo código da matrícula.
    """
    if not codigos_matricula:
        return {}
    qs = matriculas.filter(codigo_matricula__in=codigos_matricula)
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


def _origens_autocomplete(ano_letivo: int, eh_historico: bool) -> list[bool]:
    """Define as origens atual e histórica consultadas.

    Args:
        ano_letivo: Ano da consulta; zero seleciona ambas as origens.
        eh_historico: Solicita a origem histórica mesmo no ano corrente.

    Returns:
        Indicadores de origem histórica, na ordem de consulta.
    """
    if not ano_letivo:
        return [False, True]
    return [eh_historico or ano_letivo != timezone.now().year]


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
    try:
        codigo_aluno = int(codigo_eol) if codigo_eol else None
    except (TypeError, ValueError):
        return []
    ramos = _origens_autocomplete(ano_letivo, eh_historico)

    alunos_programa: set[int] = (
        _alunos_com_turma_programa(codigo_turmas) if codigo_turmas else set()
    )

    saida: list[dict[str, Any]] = []
    vistos: set[tuple[int, int]] = set()
    for historico in ramos:
        matriculas = _matriculas_autocomplete_qs(
            historico, nome_aluno, codigo_aluno
        )

        mts = _mts_autocomplete_ue(
            codigo_ue,
            ano_letivo,
            historico,
            matriculas if codigo_aluno is not None else None,
        )
        matriculas_idx = _matriculas_autocomplete_idx(
            [mt["codigo_matricula"] for mt in mts],
            matriculas,
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
    qs = Matricula.objects.filter(codigo_ue=ue_codigo, origem_atual=True)
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
) -> dict[int, list[dict[str, Any]]]:
    """Agrupa todos os vínculos atuais elegíveis de cada matrícula."""
    mts = (
        MatriculaTurma.objects.filter(
            codigo_matricula__in=codigos_matricula,
            origem_atual=True,
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
    indice: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for mt in mts:
        indice[mt["codigo_matricula"]].append(mt)
    return dict(indice)


def _chave_sugestao_ativa(
    matricula: dict[str, Any], vinculo: dict[str, Any]
) -> tuple[Any, ...]:
    """Identifica sugestões iguais pelos campos apresentados ao consumidor.

    Args:
        matricula: Identificação e nomes do aluno.
        vinculo: Turma, chamada e etapa de ensino do vínculo.

    Returns:
        Valores que distinguem uma sugestão de autocomplete.
    """
    return (
        matricula["aluno_id"],
        matricula["aluno__nome"],
        matricula["aluno__nome_social"],
        vinculo["codigo_turma"],
        vinculo["numero_chamada"],
        vinculo["nome_turma"],
        MODALIDADE_POR_ETAPA.get(vinculo["codigo_etapa_ensino"]),
    )


def _linhas_autocomplete_ativos(
    matriculas: list[dict[str, Any]],
    mts_idx: dict[int, list[dict[str, Any]]],
    nome_l: str,
    limite: int,
) -> list[dict[str, Any]]:
    """Agrupa os registros de autocomplete de alunos ativos."""
    saida: list[dict[str, Any]] = []
    vistos: set[tuple[Any, ...]] = set()
    for m in sorted(
        matriculas,
        key=lambda item: (
            item["aluno__nome"],
            item["aluno__nome_social"] or "",
        ),
    ):
        a = {
            "nome": m["aluno__nome"],
            "nome_social": m["aluno__nome_social"],
        }
        nome = a.get("nome") or ""
        if nome_l and nome_l not in nome.lower():
            continue
        for mt in mts_idx[m["codigo_matricula"]]:
            chave = _chave_sugestao_ativa(m, mt)
            if chave in vistos:
                continue
            vistos.add(chave)
            saida.append(
                {
                    "matricula": m,
                    "matricula_turma": mt,
                    "aluno": a,
                }
            )
            if len(saida) >= limite:
                return saida
    return saida


def buscar_alunos_ativos_autocomplete(
    ue_codigo: str,
    aluno_nome: str | None = None,
    aluno_codigo: int = 0,
    data_referencia: datetime | date | None = None,
    limite: int = 10,
) -> list[dict[str, Any]]:
    """Busca alunos ativos para autocomplete.

    Args:
        ue_codigo: Código da unidade educacional.
        aluno_nome: Trecho do nome para busca.
        aluno_codigo: Código do aluno; zero não filtra por código.
        data_referencia: Data da consulta; se ausente, usa a data local atual.
        limite: Quantidade máxima de sugestões.

    Returns:
        Sugestões de alunos com vínculos elegíveis na unidade.
    """
    referencia = (
        data_referencia.date()
        if isinstance(data_referencia, datetime)
        else data_referencia or timezone.localdate()
    )
    nome_l = (aluno_nome or "").strip().lower()
    qs = _qs_matriculas_ativas_ue(ue_codigo, referencia, aluno_codigo, nome_l)
    matriculas = list(
        qs.values(
            "codigo_matricula",
            "aluno_id",
            "codigo_ue",
            "aluno__nome",
            "aluno__nome_social",
        )[: limite + 500]
    )
    if not matriculas:
        return []

    mts_idx = _mts_ativas_idx([m["codigo_matricula"] for m in matriculas])
    matriculas = [m for m in matriculas if m["codigo_matricula"] in mts_idx]
    if not matriculas:
        return []

    return _linhas_autocomplete_ativos(matriculas, mts_idx, nome_l, limite)
