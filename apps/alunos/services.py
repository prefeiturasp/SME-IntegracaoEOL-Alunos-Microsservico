"""Services do domínio Alunos."""

import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import date, datetime
from typing import Any

from django.db import connection
from django.db.models import Count, Max
from django.utils import timezone

from apps.alunos.enums import (
    SITUACOES_MATRICULA_ATIVAS,
    SITUACOES_MATRICULA_VALIDAS,
)
from apps.alunos.models import (
    Aluno,
    Matricula,
    MatriculaTurma,
    NecessidadeEspecialAluno,
    ResponsavelAluno,
    TipoNecessidadeEspecial,
)

# ---------------------------------------------------------------------------
# DTOs de saída (1 por endpoint ou família de endpoints)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TurmaDoAlunoDTO:
    """Dados de uma matrícula/turma do aluno."""

    codigo_aluno: int
    ano_letivo: int
    nome_aluno: str
    nome_social_aluno: str | None
    codigo_situacao_matricula: int
    situacao_matricula: str
    data_situacao: date | None
    data_nascimento: date | None
    numero_aluno_chamada: str | None
    codigo_turma: int
    data_atualizacao_contato: date | None


@dataclass(frozen=True)
class AlunoAutocompleteDTO:
    """Dados básicos do aluno para autocomplete."""

    codigo_aluno: int
    nome_aluno: str
    nome_social_aluno: str | None
    codigo_turma: int
    numero_aluno_chamada: str | None


@dataclass(frozen=True)
class AlunoAtivoTurmaDTO:
    """Dados de alunos ativos em uma turma."""

    codigo_aluno: int
    nome_aluno: str
    nome_social_aluno: str | None
    data_nascimento: date | None
    codigo_situacao_matricula: int
    situacao_matricula: str
    data_situacao: date | None
    numero_aluno_chamada: str | None
    possui_deficiencia: bool
    codigo_matricula: int
    codigo_turma: int
    codigo_escola: str
    ano_letivo: int


@dataclass(frozen=True)
class NecessidadeEspecialDTO:
    """Necessidade especial vinculada ao aluno."""

    codigo_aluno: int
    tipo_necessidade_especial: int
    descricao_necessidade_especial: str


@dataclass(frozen=True)
class InformacoesAlunoDTO:
    """Informações do Aluno."""

    codigo_aluno: int
    nome_aluno: str
    nome_social_aluno: str | None
    nome_mae: str | None
    sexo: str | None
    nacionalidade: str | None
    raca_cor: str | None
    nis: str | None
    cpf: str | None
    data_nascimento: date | None
    possui_deficiencia: bool


@dataclass(frozen=True)
class InformacoesAlunoTurmaDTO:
    """Resumo dos alunos de uma turma."""

    numero_aluno_chamada: str | None
    codigo_aluno: int
    nome_aluno: str
    nome_social_aluno: str | None
    sexo: str | None
    raca_cor: str | None


@dataclass(frozen=True)
class QuantidadeMatriculadosCCDTO:
    """Quantidade de matrículas por ano letivo."""

    codigo_turma: int
    quantidade: int
    ordem: int


@dataclass(frozen=True)
class QuantidadeMatriculadosDTO:
    """Quantidade de matrículas por turma, sem distinção de ano letivo."""

    quantidade: int
    ordem: int
    codigo_turma: int
    ue_codigo: str


@dataclass(frozen=True)
class DadosAcompanhamentoEscolarDTO:
    """Dados de acompanhamento escolar do aluno."""

    codigo_eol: int
    nome_responsavel: str | None
    cpf_responsavel: str | None
    nome: str
    nome_social: str | None
    codigo_escola: str
    tipo_responsavel: int | None
    codigo_turma: int
    situacao_matricula: str
    data_nascimento: date | None
    data_situacao_matricula: date | None
    ano_letivo: int


@dataclass(frozen=True)
class ResponsavelTurmaDTO:
    """Dados do responsável agrupado por turma."""

    codigo_ue: str
    codigo_turma: int
    cpf_responsavel: str
    codigo_aluno: int


@dataclass(frozen=True)
class DadosResponsavelDTO:
    """Dados do responsável do aluno, incluindo vínculo e contatos."""

    codigo_responsavel: int
    cpf: str | None
    email: str | None
    nome: str | None
    tipo_responsavel: int | None
    nome_aluno: str
    nome_social_aluno: str | None
    data_nascimento_aluno: date | None
    codigo_aluno: str
    ddd_celular: str | None
    numero_celular: str | None
    autoriza_sms: str | None
    logradouro: str | None
    cep: int | None
    data_fim_vinculo: date | None


@dataclass(frozen=True)
class DadosResponsavelResumidoDTO:
    """Dados do responsável resumidos."""

    codigo_responsavel: int
    cpf: str | None
    email: str | None
    nome: str | None
    tipo_responsavel: int | None
    ddd_celular: str | None
    numero_celular: str | None
    codigo_aluno: str


@dataclass(frozen=True)
class TotalAlunosAtivosPeriodoDTO:
    """Total de alunos distintos ativos no intervalo informado."""

    quantidade: int


@dataclass(frozen=True)
class ConsolidacaoMatriculaDTO:
    """Total de matrículas válidas agrupadas por turma."""

    turma_codigo: str
    quantidade: int


@dataclass(frozen=True)
class MatriculaEscolaAlunoDTO:
    """Matrícula do aluno em uma escola específica."""

    codigo_aluno: int
    nome_aluno: str
    nome_social_aluno: str | None
    codigo_situacao_matricula: int
    situacao_matricula: str
    data_situacao: date | None
    codigo_turma: int
    codigo_matricula: int
    ano_letivo: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _calcular_idade(
    nascimento: date | datetime | None, referencia: date | None = None
) -> int | None:
    """Calcula idade em anos completos na data de referência."""
    if nascimento is None:
        return None
    if isinstance(nascimento, datetime):
        nascimento = nascimento.date()
    ref = referencia or timezone.now().date()
    idade = ref.year - nascimento.year
    if (ref.month, ref.day) < (nascimento.month, nascimento.day):
        idade -= 1
    return idade


def _alunos_indexados(
    codigos_alunos: Sequence[int],
) -> dict[int, dict[str, Any]]:
    """Indexa dados básicos do aluno por ``codigo_aluno``."""
    if not codigos_alunos:
        return {}
    return {
        a["codigo_aluno"]: a
        for a in Aluno.objects.filter(codigo_aluno__in=codigos_alunos).values(
            "codigo_aluno",
            "nome",
            "nome_social",
            "data_nascimento",
            "cpf",
            "sexo",
            "raca_cor",
            "nome_mae",
            "nacionalidade",
            "nis",
            "data_atualizacao_contato",
            "possui_deficiencia",
        )
    }


def _matricula_turma_por_matricula(
    codigos_matricula: Sequence[int],
) -> dict[int, dict[str, Any]]:
    """Indexa dados de vínculo de matrícula com a turma."""
    if not codigos_matricula:
        return {}
    saida: dict[int, dict[str, Any]] = {}
    for mt in MatriculaTurma.objects.filter(
        codigo_matricula__in=codigos_matricula
    ).values(
        "codigo_matricula",
        "codigo_turma",
        "numero_chamada",
        "data_situacao_aluno",
    ):
        saida.setdefault(mt["codigo_matricula"], mt)
    return saida


def _matriculas_por_codigos_turma(
    codigos_turma: Sequence[int],
) -> list[dict[str, Any]]:
    """Consulta as matrículas vinculadas a uma lista de códigos de turma."""
    if not codigos_turma:
        return []
    mts = list(
        MatriculaTurma.objects.filter(codigo_turma__in=codigos_turma).values(
            "codigo_matricula",
            "codigo_turma",
            "numero_chamada",
            "data_situacao_aluno",
        )
    )
    if not mts:
        return []
    codigos_matricula = [
        mt["codigo_matricula"] for mt in mts if mt["codigo_matricula"]
    ]
    matriculas_idx = {
        m["codigo_matricula"]: m
        for m in Matricula.objects.filter(
            codigo_matricula__in=codigos_matricula
        ).values(
            "codigo_matricula",
            "aluno_id",
            "codigo_ue",
            "ano_letivo",
            "data_situacao_matricula",
            "codigo_situacao_matricula",
            "situacao_matricula",
        )
    }
    saida: list[dict[str, Any]] = []
    for mt in mts:
        matricula = matriculas_idx.get(mt["codigo_matricula"])
        if matricula:
            saida.append({**matricula, **mt})
    return saida


def _responsavel_principal(
    codigo_aluno: int,
) -> dict[str, Any] | None:
    """Retorna o responsável vigente prioritário do aluno."""
    return (
        ResponsavelAluno.objects.filter(
            aluno_id=codigo_aluno,
            data_fim_vinculo__isnull=True,
        )
        .order_by("tipo_responsavel")
        .values(
            "codigo_responsavel",
            "tipo_responsavel",
            "nome",
            "cpf",
            "email",
            "ddd_celular",
            "numero_celular",
        )
        .first()
    )


def _consultar_turmas_do_aluno(
    codigo_aluno: int,
    ano_letivo: int | None = None,
    historico: bool = False,
    filtrar_situacao: bool = True,
) -> list[TurmaDoAlunoDTO]:
    """Consulta as turmas/matrículas do aluno.

    As são turmas ordenadas por ano letivo decrescente e situação ascendente.
    """
    qs = Matricula.objects.filter(aluno_id=codigo_aluno)
    if ano_letivo is not None:
        qs = qs.filter(ano_letivo=ano_letivo)
    if filtrar_situacao:
        qs = qs.filter(
            codigo_situacao_matricula__in=SITUACOES_MATRICULA_VALIDAS
        )
    if not historico:
        ano_corrente = timezone.now().year
        qs = qs.filter(ano_letivo=ano_corrente)

    matriculas = list(
        qs.values(
            "codigo_matricula",
            "aluno_id",
            "codigo_ue",
            "ano_letivo",
            "codigo_situacao_matricula",
            "situacao_matricula",
            "data_situacao_matricula",
        ).order_by("-ano_letivo", "codigo_situacao_matricula")
    )
    if not matriculas:
        return []

    aluno = (
        Aluno.objects.filter(codigo_aluno=codigo_aluno)
        .values(
            "codigo_aluno",
            "nome",
            "nome_social",
            "data_nascimento",
            "cpf",
            "data_atualizacao_contato",
        )
        .first()
        or {}
    )
    mts = _matricula_turma_por_matricula(
        [m["codigo_matricula"] for m in matriculas]
    )

    saida: list[TurmaDoAlunoDTO] = []
    for m in matriculas:
        mt = mts.get(m["codigo_matricula"], {})
        saida.append(
            TurmaDoAlunoDTO(
                codigo_aluno=m["aluno_id"],
                ano_letivo=m["ano_letivo"],
                nome_aluno=aluno.get("nome", ""),
                nome_social_aluno=aluno.get("nome_social"),
                codigo_situacao_matricula=m["codigo_situacao_matricula"],
                situacao_matricula=m["situacao_matricula"],
                data_situacao=m["data_situacao_matricula"],
                data_nascimento=aluno.get("data_nascimento"),
                numero_aluno_chamada=mt.get("numero_chamada"),
                codigo_turma=mt.get("codigo_turma") or 0,
                data_atualizacao_contato=aluno.get("data_atualizacao_contato"),
            )
        )
    return saida


def buscar_turmas_do_aluno(
    codigo_aluno: int,
    ano_letivo: int | None = None,
    historico: bool = False,
    filtrar_situacao: bool = True,
) -> list[TurmaDoAlunoDTO]:
    """Retorna as turmas do aluno no ano corrente, salvo histórico."""
    return _consultar_turmas_do_aluno(
        codigo_aluno=codigo_aluno,
        ano_letivo=ano_letivo,
        historico=historico,
        filtrar_situacao=filtrar_situacao,
    )


def buscar_turmas_do_aluno_por_situacao_matricula(
    codigo_aluno: int,
    ano_letivo: int | None,
    filtrar_situacao_matricula: bool = True,
) -> list[TurmaDoAlunoDTO]:
    """Busca turmas filtradas por situação de matrícula."""
    eh_historico = bool(
        ano_letivo and ano_letivo > 0 and ano_letivo != timezone.now().year
    )
    return _consultar_turmas_do_aluno(
        codigo_aluno=codigo_aluno,
        ano_letivo=ano_letivo,
        historico=eh_historico,
        filtrar_situacao=filtrar_situacao_matricula,
    )


def buscar_alunos_da_ue(
    codigo_ue: str,
    ano_letivo: int,
    nome_aluno: str | None = None,
    codigo_eol: str | None = None,
) -> list[TurmaDoAlunoDTO]:
    """Lista alunos da UE no ano letivo, filtrável por nome/código."""
    qs = Matricula.objects.filter(
        codigo_ue=codigo_ue,
        ano_letivo=ano_letivo,
        codigo_situacao_matricula__in=SITUACOES_MATRICULA_VALIDAS,
    )
    if codigo_eol:
        try:
            qs = qs.filter(aluno_id=int(codigo_eol))
        except (TypeError, ValueError):
            return []

    matriculas = list(
        qs.values(
            "codigo_matricula",
            "aluno_id",
            "codigo_ue",
            "ano_letivo",
            "codigo_situacao_matricula",
            "situacao_matricula",
            "data_situacao_matricula",
        )
    )
    if not matriculas:
        return []

    codigos_alunos = {m["aluno_id"] for m in matriculas}
    alunos_idx = _alunos_indexados(list(codigos_alunos))

    if nome_aluno:
        nome_l = nome_aluno.strip().lower()
        codigos_alunos = {
            c
            for c, a in alunos_idx.items()
            if nome_l in (a.get("nome") or "").lower()
        }
        matriculas = [m for m in matriculas if m["aluno_id"] in codigos_alunos]
        if not matriculas:
            return []

    mts = _matricula_turma_por_matricula(
        [m["codigo_matricula"] for m in matriculas]
    )

    return [
        TurmaDoAlunoDTO(
            codigo_aluno=m["aluno_id"],
            ano_letivo=m["ano_letivo"],
            nome_aluno=alunos_idx.get(m["aluno_id"], {}).get("nome", ""),
            nome_social_aluno=alunos_idx.get(m["aluno_id"], {}).get(
                "nome_social"
            ),
            codigo_situacao_matricula=m["codigo_situacao_matricula"],
            situacao_matricula=m["situacao_matricula"],
            data_situacao=m["data_situacao_matricula"],
            data_nascimento=alunos_idx.get(m["aluno_id"], {}).get(
                "data_nascimento"
            ),
            numero_aluno_chamada=mts.get(m["codigo_matricula"], {}).get(
                "numero_chamada"
            ),
            codigo_turma=mts.get(m["codigo_matricula"], {}).get("codigo_turma")
            or 0,
            data_atualizacao_contato=alunos_idx.get(m["aluno_id"], {}).get(
                "data_atualizacao_contato"
            ),
        )
        for m in matriculas
    ]


def _resolver_matriculas_e_mts_idx(
    matriculas: list[dict],
    codigo_turmas: Sequence[int] | None,
) -> tuple[list[dict], dict]:
    """Resolve o índice mts; quando há filtro por turma, filtra matriculas."""
    codigos_matricula = [m["codigo_matricula"] for m in matriculas]
    if not codigo_turmas:
        return matriculas, _matricula_turma_por_matricula(codigos_matricula)

    mts = list(
        MatriculaTurma.objects.filter(
            codigo_matricula__in=codigos_matricula,
            codigo_turma__in=list(codigo_turmas),
        ).values("codigo_matricula", "codigo_turma", "numero_chamada")
    )
    codigos_match = {mt["codigo_matricula"] for mt in mts}
    matriculas = [
        m for m in matriculas if m["codigo_matricula"] in codigos_match
    ]
    return matriculas, {mt["codigo_matricula"]: mt for mt in mts}


def _autocomplete_base(
    codigo_ue: str,
    ano_letivo: int | None = None,
    codigo_turmas: Sequence[int] | None = None,
    nome_aluno: str | None = None,
    codigo_eol: str | None = None,
    somente_ativos: bool = False,
    limite: int = 10,
) -> list[AlunoAutocompleteDTO]:
    """Resolve o autocomplete de alunos a partir de filtros opcionais."""
    situacoes = (
        SITUACOES_MATRICULA_ATIVAS
        if somente_ativos
        else SITUACOES_MATRICULA_VALIDAS
    )
    qs = Matricula.objects.filter(
        codigo_ue=codigo_ue,
        codigo_situacao_matricula__in=situacoes,
    )
    if ano_letivo is not None:
        qs = qs.filter(ano_letivo=ano_letivo)
    if codigo_eol:
        try:
            qs = qs.filter(aluno_id=int(codigo_eol))
        except (TypeError, ValueError):
            return []

    matriculas = list(
        qs.values("codigo_matricula", "aluno_id")[: limite + 200]
    )
    if not matriculas:
        return []

    matriculas, mts_idx = _resolver_matriculas_e_mts_idx(
        matriculas, codigo_turmas
    )
    alunos_idx = _alunos_indexados([m["aluno_id"] for m in matriculas])

    nome_l = (nome_aluno or "").strip().lower()
    saida: list[AlunoAutocompleteDTO] = []
    for m in matriculas:
        a = alunos_idx.get(m["aluno_id"], {})
        nome = a.get("nome") or ""
        if nome_l and nome_l not in nome.lower():
            continue
        mt = mts_idx.get(m["codigo_matricula"], {})
        saida.append(
            AlunoAutocompleteDTO(
                codigo_aluno=m["aluno_id"],
                nome_aluno=nome,
                nome_social_aluno=a.get("nome_social"),
                codigo_turma=mt.get("codigo_turma") or 0,
                numero_aluno_chamada=mt.get("numero_chamada"),
            )
        )
        if len(saida) >= limite:
            break
    return saida


def buscar_alunos_autocomplete(
    codigo_ue: str,
    ano_letivo: int,
    codigo_turmas: Sequence[int] | None = None,
    nome_aluno: str | None = None,
    codigo_eol: str | None = None,
    somente_ativos: bool = False,
    eh_historico: bool = False,  # NOSONAR
    limite: int = 10,
) -> list[AlunoAutocompleteDTO]:
    """Busca alunos para autocomplete, filtrável por turmas/nome/código."""
    return _autocomplete_base(
        codigo_ue=codigo_ue,
        ano_letivo=ano_letivo,
        codigo_turmas=codigo_turmas,
        nome_aluno=nome_aluno,
        codigo_eol=codigo_eol,
        somente_ativos=somente_ativos,
        limite=limite,
    )


def buscar_alunos_ativos_autocomplete(
    ue_codigo: str,
    aluno_nome: str | None = None,
    aluno_codigo: int = 0,
    data_referencia: datetime | date | None = None,  # NOSONAR
    limite: int = 10,
) -> list[AlunoAutocompleteDTO]:
    """Busca alunos ativos para autocomplete por data de referência."""
    return _autocomplete_base(
        codigo_ue=ue_codigo,
        nome_aluno=aluno_nome,
        codigo_eol=str(aluno_codigo) if aluno_codigo else None,
        somente_ativos=True,
        limite=limite,
    )


def obter_total_alunos_ativos_periodo(
    ano_letivo: int,
    data_inicio: datetime | date,
    data_fim: datetime | date,
    ue_id: str | None = None,
    ano_turma: str | None = None,  # NOSONAR
    dre_id: str | None = None,  # NOSONAR
    modalidades: list[int] | None = None,  # NOSONAR
) -> TotalAlunosAtivosPeriodoDTO:
    """Retorna a quantidade de alunos ativos no período."""
    qs = Matricula.objects.filter(
        ano_letivo=ano_letivo,
        codigo_situacao_matricula__in=SITUACOES_MATRICULA_ATIVAS,
        data_situacao_matricula__gte=data_inicio,
        data_situacao_matricula__lte=data_fim,
    )
    if ue_id:
        qs = qs.filter(codigo_ue=ue_id)
    total = qs.values("aluno_id").distinct().count()
    return TotalAlunosAtivosPeriodoDTO(quantidade=total)


def _consultar_alunos_ativos_turma(
    codigo_turma: int,
    data_referencia_inicio: datetime | date | None = None,
    data_referencia_fim: datetime | date | None = None,
) -> list[AlunoAtivoTurmaDTO]:
    """Lista alunos da turma com filtragem opcional por janela de datas."""
    mts = list(
        MatriculaTurma.objects.filter(codigo_turma=codigo_turma).values(
            "codigo_matricula",
            "codigo_turma",
            "numero_chamada",
            "data_situacao_aluno",
        )
    )
    if not mts:
        return []

    matriculas_idx = {
        m["codigo_matricula"]: m
        for m in Matricula.objects.filter(
            codigo_matricula__in=[mt["codigo_matricula"] for mt in mts]
        ).values(
            "codigo_matricula",
            "aluno_id",
            "codigo_ue",
            "ano_letivo",
            "data_situacao_matricula",
            "codigo_situacao_matricula",
            "situacao_matricula",
        )
    }
    rows: list[dict[str, Any]] = []
    for mt in mts:
        m = matriculas_idx.get(mt["codigo_matricula"])
        if not m:
            continue
        if (
            data_referencia_inicio is not None
            and m["data_situacao_matricula"] is not None
            and m["data_situacao_matricula"]
            < (
                data_referencia_inicio.date()
                if isinstance(data_referencia_inicio, datetime)
                else data_referencia_inicio
            )
        ):
            continue
        if (
            data_referencia_fim is not None
            and m["data_situacao_matricula"] is not None
            and m["data_situacao_matricula"]
            > (
                data_referencia_fim.date()
                if isinstance(data_referencia_fim, datetime)
                else data_referencia_fim
            )
        ):
            continue
        rows.append({**m, **mt})

    if not rows:
        return []

    alunos_idx = _alunos_indexados([r["aluno_id"] for r in rows])
    return [
        AlunoAtivoTurmaDTO(
            codigo_aluno=r["aluno_id"],
            nome_aluno=alunos_idx.get(r["aluno_id"], {}).get("nome", ""),
            nome_social_aluno=alunos_idx.get(r["aluno_id"], {}).get(
                "nome_social"
            ),
            data_nascimento=alunos_idx.get(r["aluno_id"], {}).get(
                "data_nascimento"
            ),
            codigo_situacao_matricula=r["codigo_situacao_matricula"],
            situacao_matricula=r["situacao_matricula"],
            data_situacao=r["data_situacao_matricula"],
            numero_aluno_chamada=r["numero_chamada"],
            possui_deficiencia=alunos_idx.get(r["aluno_id"], {}).get(
                "possui_deficiencia", False
            ),
            codigo_matricula=r["codigo_matricula"],
            codigo_turma=r["codigo_turma"],
            codigo_escola=r["codigo_ue"],
            ano_letivo=r["ano_letivo"],
        )
        for r in rows
    ]


def obter_alunos_ativos_por_periodo_e_turma(
    codigo_turma: int,
    data_referencia_fim: datetime | date,
    data_referencia_inicio: datetime | date | None = None,
) -> list[AlunoAtivoTurmaDTO]:
    """Retorna alunos ativos em uma turma, com período de referência."""
    return _consultar_alunos_ativos_turma(
        codigo_turma=codigo_turma,
        data_referencia_inicio=data_referencia_inicio,
        data_referencia_fim=data_referencia_fim,
    )


def obter_alunos_ativos_por_turma(
    codigo_turma: int,
) -> list[AlunoAtivoTurmaDTO]:
    """Retorna alunos ativos em uma turma (sem filtro de período)."""
    return _consultar_alunos_ativos_turma(codigo_turma=codigo_turma)


def obter_necessidades_especiais_por_aluno(
    codigo_aluno: int,
) -> list[NecessidadeEspecialDTO]:
    """Retorna as necessidades especiais cadastradas para o aluno."""
    rows = list(
        NecessidadeEspecialAluno.objects.filter(aluno_id=codigo_aluno).values(
            "aluno_id", "necessidade_especial_id"
        )
    )
    if not rows:
        return []

    descricoes = {
        t["codigo_necessidade_especial"]: t["descricao"]
        for t in TipoNecessidadeEspecial.objects.filter(
            codigo_necessidade_especial__in=[
                r["necessidade_especial_id"] for r in rows
            ]
        ).values("codigo_necessidade_especial", "descricao")
    }
    return [
        NecessidadeEspecialDTO(
            codigo_aluno=r["aluno_id"],
            tipo_necessidade_especial=r["necessidade_especial_id"],
            descricao_necessidade_especial=descricoes.get(
                r["necessidade_especial_id"], ""
            ),
        )
        for r in rows
    ]


def obter_alunos_por_codigos_e_ano(
    codigos_aluno: Sequence[int], ano_letivo: int
) -> list[TurmaDoAlunoDTO]:
    """Lista turmas dos alunos informados, restrita ao ano letivo."""
    if not codigos_aluno:
        return []
    saida: list[TurmaDoAlunoDTO] = []
    for codigo in codigos_aluno:
        saida.extend(
            _consultar_turmas_do_aluno(
                codigo_aluno=codigo,
                ano_letivo=ano_letivo,
                historico=True,
                filtrar_situacao=True,
            )
        )
    return saida


def obter_alunos_por_codigos(
    codigos_aluno: Sequence[int],
) -> list[TurmaDoAlunoDTO]:
    """Lista turmas dos alunos informados sem filtro de ano."""
    if not codigos_aluno:
        return []
    saida: list[TurmaDoAlunoDTO] = []
    for codigo in codigos_aluno:
        saida.extend(
            _consultar_turmas_do_aluno(
                codigo_aluno=codigo,
                ano_letivo=None,
                historico=True,
                filtrar_situacao=True,
            )
        )
    return saida


def obter_informacoes_aluno(
    codigo_aluno: int,
) -> InformacoesAlunoDTO | None:
    """Retorna as informações cadastrais do aluno."""
    aluno = Aluno.objects.filter(codigo_aluno=codigo_aluno).first()
    if aluno is None:
        return None
    return InformacoesAlunoDTO(
        codigo_aluno=aluno.codigo_aluno,
        nome_aluno=aluno.nome,
        nome_social_aluno=aluno.nome_social,
        nome_mae=aluno.nome_mae,
        sexo=aluno.sexo,
        nacionalidade=aluno.nacionalidade,
        raca_cor=aluno.raca_cor,
        nis=aluno.nis,
        cpf=aluno.cpf,
        data_nascimento=aluno.data_nascimento,
        possui_deficiencia=aluno.possui_deficiencia,
    )


def obter_informacoes_alunos_da_turma(
    codigo_turma: int,
) -> list[InformacoesAlunoTurmaDTO]:
    """Lista os alunos de uma turma no formato chamada/diário."""
    rows = _matriculas_por_codigos_turma([codigo_turma])
    rows_validas = [
        r
        for r in rows
        if r["codigo_situacao_matricula"] in SITUACOES_MATRICULA_VALIDAS
    ]
    if not rows_validas:
        return []

    alunos_idx = _alunos_indexados([r["aluno_id"] for r in rows_validas])
    return [
        InformacoesAlunoTurmaDTO(
            numero_aluno_chamada=r["numero_chamada"],
            codigo_aluno=r["aluno_id"],
            nome_aluno=alunos_idx.get(r["aluno_id"], {}).get("nome", ""),
            nome_social_aluno=alunos_idx.get(r["aluno_id"], {}).get(
                "nome_social"
            ),
            sexo=alunos_idx.get(r["aluno_id"], {}).get("sexo"),
            raca_cor=alunos_idx.get(r["aluno_id"], {}).get("raca_cor"),
        )
        for r in rows_validas
    ]


def obter_quantidade_matriculados_por_ano_e_cc(
    ano_letivo: int,
    ue_id: str | None = None,
    componentes_curriculares: list[int] | None = None,  # NOSONAR
    dre_id: str | None = None,  # NOSONAR
) -> list[QuantidadeMatriculadosCCDTO]:
    """Agrupa matrículas por turma."""
    qs = Matricula.objects.filter(
        ano_letivo=ano_letivo,
        codigo_situacao_matricula__in=SITUACOES_MATRICULA_VALIDAS,
    )
    if ue_id:
        qs = qs.filter(codigo_ue=ue_id)

    codigos_matricula = list(qs.values_list("codigo_matricula", flat=True))
    if not codigos_matricula:
        return []

    agrupado = (
        MatriculaTurma.objects.filter(codigo_matricula__in=codigos_matricula)
        .values("codigo_turma")
        .annotate(quantidade=Count("id"))
        .order_by("codigo_turma")
    )
    return [
        QuantidadeMatriculadosCCDTO(
            codigo_turma=r["codigo_turma"],
            quantidade=r["quantidade"],
            ordem=ordem,
        )
        for ordem, r in enumerate(agrupado, start=1)
    ]


def obter_quantidade_matriculados(
    ano_letivo: int,
    ue_codigo: str = "",
    dre_codigo: str = "",  # NOSONAR
    modalidade: list[int] | None = None,  # NOSONAR
    ano: list[int] | None = None,  # NOSONAR
    turma: list[str] | None = None,  # NOSONAR
) -> list[QuantidadeMatriculadosDTO]:
    """Lista a quantidade de matriculados agregada por (UE, turma)."""
    qs = Matricula.objects.filter(
        ano_letivo=ano_letivo,
        codigo_situacao_matricula__in=SITUACOES_MATRICULA_VALIDAS,
    )
    if ue_codigo:
        qs = qs.filter(codigo_ue=ue_codigo)

    matriculas_por_ue = {
        m["codigo_matricula"]: m["codigo_ue"]
        for m in qs.values("codigo_matricula", "codigo_ue")
    }
    if not matriculas_por_ue:
        return []

    agrupado = MatriculaTurma.objects.filter(
        codigo_matricula__in=list(matriculas_por_ue.keys())
    ).values("codigo_turma", "codigo_matricula")
    grupos: dict[tuple[str, int], int] = {}
    for r in agrupado:
        ue = matriculas_por_ue.get(r["codigo_matricula"], "")
        chave = (ue, r["codigo_turma"])
        grupos[chave] = grupos.get(chave, 0) + 1

    saida: list[QuantidadeMatriculadosDTO] = []
    for ordem, ((ue, codigo_turma), qtd) in enumerate(
        sorted(grupos.items()), start=1
    ):
        saida.append(
            QuantidadeMatriculadosDTO(
                quantidade=qtd,
                ordem=ordem,
                codigo_turma=codigo_turma,
                ue_codigo=ue,
            )
        )
    return saida


def obter_dados_acompanhamento_escolar(
    codigo_ue: str | None = None,
    ano_letivo: int | None = None,
    turma_codigo: str | None = None,
    codigo_aluno: int | None = None,
    cpf_responsavel: str | None = None,
    codigo_dre: str | None = None,  # NOSONAR
    modalidade: int | None = None,  # NOSONAR
    semestre: int | None = None,  # NOSONAR
) -> list[DadosAcompanhamentoEscolarDTO]:
    """Lista os dados de acompanhamento escolar."""
    qs = Matricula.objects.filter(
        codigo_situacao_matricula__in=SITUACOES_MATRICULA_VALIDAS
    )
    if codigo_ue:
        qs = qs.filter(codigo_ue=codigo_ue)
    if ano_letivo:
        qs = qs.filter(ano_letivo=ano_letivo)
    if codigo_aluno:
        qs = qs.filter(aluno_id=codigo_aluno)
    if cpf_responsavel:
        qs = qs.filter(
            aluno_id__in=ResponsavelAluno.objects.filter(
                cpf=cpf_responsavel,
                data_fim_vinculo__isnull=True,
            ).values("aluno_id")
        )

    matriculas = list(
        qs.values(
            "codigo_matricula",
            "aluno_id",
            "codigo_ue",
            "ano_letivo",
            "codigo_situacao_matricula",
            "situacao_matricula",
            "data_situacao_matricula",
        )
    )
    if not matriculas:
        return []

    mts = _matricula_turma_por_matricula(
        [m["codigo_matricula"] for m in matriculas]
    )
    if turma_codigo:
        try:
            codigo_turma_int = int(turma_codigo)
        except (TypeError, ValueError):
            return []
        matriculas = [
            m
            for m in matriculas
            if mts.get(m["codigo_matricula"], {}).get("codigo_turma")
            == codigo_turma_int
        ]
        if not matriculas:
            return []

    codigos_alunos = [m["aluno_id"] for m in matriculas]
    alunos_idx = _alunos_indexados(codigos_alunos)
    responsaveis = {
        r["aluno_id"]: r
        for r in ResponsavelAluno.objects.filter(
            aluno_id__in=codigos_alunos,
            data_fim_vinculo__isnull=True,
        )
        .order_by("aluno_id", "tipo_responsavel")
        .values("aluno_id", "nome", "cpf", "tipo_responsavel")
    }

    saida: list[DadosAcompanhamentoEscolarDTO] = []
    for m in matriculas:
        a = alunos_idx.get(m["aluno_id"], {})
        resp = responsaveis.get(m["aluno_id"], {})
        mt = mts.get(m["codigo_matricula"], {})
        saida.append(
            DadosAcompanhamentoEscolarDTO(
                codigo_eol=m["aluno_id"],
                nome_responsavel=resp.get("nome"),
                cpf_responsavel=resp.get("cpf"),
                nome=a.get("nome", ""),
                nome_social=a.get("nome_social"),
                codigo_escola=m["codigo_ue"],
                tipo_responsavel=resp.get("tipo_responsavel"),
                codigo_turma=mt.get("codigo_turma") or 0,
                situacao_matricula=m["situacao_matricula"],
                data_nascimento=a.get("data_nascimento"),
                data_situacao_matricula=m["data_situacao_matricula"],
                ano_letivo=m["ano_letivo"],
            )
        )
    return saida


def obter_responsaveis_dre_ue_turma(
    codigo_ue: str | None = None,
    ano_letivo: int | None = None,
    codigo_dre: str | None = None,  # NOSONAR
) -> list[ResponsavelTurmaDTO]:
    """Lista responsáveis vigentes agrupados por UE/turma."""
    matriculas_qs = Matricula.objects.filter(
        codigo_situacao_matricula__in=SITUACOES_MATRICULA_ATIVAS
    )
    if codigo_ue:
        matriculas_qs = matriculas_qs.filter(codigo_ue=codigo_ue)
    if ano_letivo:
        matriculas_qs = matriculas_qs.filter(ano_letivo=ano_letivo)

    matriculas = list(
        matriculas_qs.values("codigo_matricula", "aluno_id", "codigo_ue")
    )
    if not matriculas:
        return []

    mts = _matricula_turma_por_matricula(
        [m["codigo_matricula"] for m in matriculas]
    )
    codigos_alunos = [m["aluno_id"] for m in matriculas]
    responsaveis_por_aluno: dict[int, list[dict[str, Any]]] = {}
    for r in ResponsavelAluno.objects.filter(
        aluno_id__in=codigos_alunos,
        data_fim_vinculo__isnull=True,
    ).values("aluno_id", "cpf"):
        responsaveis_por_aluno.setdefault(r["aluno_id"], []).append(r)

    saida: list[ResponsavelTurmaDTO] = []
    for m in matriculas:
        responsaveis = responsaveis_por_aluno.get(m["aluno_id"], [])
        if not responsaveis:
            continue
        mt = mts.get(m["codigo_matricula"], {})
        for r in responsaveis:
            cpf = r.get("cpf")
            if not cpf:
                continue
            saida.append(
                ResponsavelTurmaDTO(
                    codigo_ue=m["codigo_ue"],
                    codigo_turma=mt.get("codigo_turma") or 0,
                    cpf_responsavel=cpf,
                    codigo_aluno=m["aluno_id"],
                )
            )
    return saida


def obter_dados_responsavel(
    cpf_responsavel: str,
) -> list[DadosResponsavelDTO]:
    """Lista os detalhes do responsável + aluno vinculado."""
    cpf = (cpf_responsavel or "").strip()
    if not cpf:
        return []
    vinculos = list(
        ResponsavelAluno.objects.filter(cpf=cpf).values(
            "codigo_responsavel",
            "aluno_id",
            "tipo_responsavel",
            "nome",
            "email",
            "cpf",
            "ddd_celular",
            "numero_celular",
            "autoriza_sms",
            "logradouro",
            "cep",
            "data_fim_vinculo",
        )
    )
    if not vinculos:
        return []

    alunos_idx = _alunos_indexados([v["aluno_id"] for v in vinculos])
    return [
        DadosResponsavelDTO(
            codigo_responsavel=v["codigo_responsavel"],
            cpf=v["cpf"],
            email=v["email"],
            nome=v["nome"],
            tipo_responsavel=v["tipo_responsavel"],
            nome_aluno=alunos_idx.get(v["aluno_id"], {}).get("nome", ""),
            nome_social_aluno=alunos_idx.get(v["aluno_id"], {}).get(
                "nome_social"
            ),
            data_nascimento_aluno=alunos_idx.get(v["aluno_id"], {}).get(
                "data_nascimento"
            ),
            codigo_aluno=str(v["aluno_id"]),
            ddd_celular=v["ddd_celular"],
            numero_celular=v["numero_celular"],
            autoriza_sms=v["autoriza_sms"],
            logradouro=v["logradouro"],
            cep=v["cep"],
            data_fim_vinculo=v["data_fim_vinculo"],
        )
        for v in vinculos
    ]


def obter_dados_responsavel_resumido(
    cpf_responsavel: str,
) -> DadosResponsavelResumidoDTO | None:
    """Lista dados do responsável de forma resumida."""
    cpf = (cpf_responsavel or "").strip()
    if not cpf:
        return None
    v = (
        ResponsavelAluno.objects.filter(cpf=cpf)
        .order_by("tipo_responsavel")
        .values(
            "codigo_responsavel",
            "aluno_id",
            "tipo_responsavel",
            "nome",
            "email",
            "cpf",
            "ddd_celular",
            "numero_celular",
        )
        .first()
    )
    if v is None:
        return None
    return DadosResponsavelResumidoDTO(
        codigo_responsavel=v["codigo_responsavel"],
        cpf=v["cpf"],
        email=v["email"],
        nome=v["nome"],
        tipo_responsavel=v["tipo_responsavel"],
        ddd_celular=v["ddd_celular"],
        numero_celular=v["numero_celular"],
        codigo_aluno=str(v["aluno_id"]),
    )


def atualizar_dados_responsavel_busca_ativa(
    codigo_aluno: int,
    cpf_responsavel: str,
    *,
    email: str | None = None,
    ddd_celular: str | None = None,
    numero_celular: str | None = None,
) -> DadosResponsavelResumidoDTO:
    """Atualiza contatos do responsável no fluxo de busca ativa."""
    resp = ResponsavelAluno.objects.filter(
        cpf=cpf_responsavel, aluno_id=codigo_aluno
    ).first()
    if resp is None:
        return DadosResponsavelResumidoDTO(
            codigo_responsavel=0,
            cpf=cpf_responsavel,
            email=email,
            nome=None,
            tipo_responsavel=None,
            ddd_celular=ddd_celular,
            numero_celular=numero_celular,
            codigo_aluno=str(codigo_aluno),
        )

    if email is not None:
        resp.email = email
    if ddd_celular is not None:
        resp.ddd_celular = ddd_celular
    if numero_celular is not None:
        resp.numero_celular = numero_celular
    resp.save(update_fields=["email", "ddd_celular", "numero_celular"])

    return DadosResponsavelResumidoDTO(
        codigo_responsavel=resp.codigo_responsavel,
        cpf=resp.cpf,
        email=resp.email,
        nome=resp.nome,
        tipo_responsavel=resp.tipo_responsavel,
        ddd_celular=resp.ddd_celular,
        numero_celular=resp.numero_celular,
        codigo_aluno=str(codigo_aluno),
    )


def cadastrar_dados_responsavel(
    codigo_aluno: int,
    cpf_responsavel: str,
    *,
    nome: str = "",
    email: str = "",
    tipo_responsavel: int | None = None,
    ddd_celular: str = "",
    numero_celular: str = "",
) -> DadosResponsavelResumidoDTO:
    """Cria ou atualiza um vínculo responsável-aluno."""
    resp = ResponsavelAluno.objects.filter(
        cpf=cpf_responsavel, aluno_id=codigo_aluno
    ).first()
    if resp is None:
        max_pk = (
            ResponsavelAluno.objects.aggregate(m=Max("codigo_responsavel"))[
                "m"
            ]
            or 0
        )
        defaults: dict[str, Any] = {
            "codigo_responsavel": max_pk + 1,
            "aluno_id": codigo_aluno,
            "cpf": cpf_responsavel,
            "nome": nome,
            "email": email,
            "tipo_responsavel": tipo_responsavel,
            "ddd_celular": ddd_celular,
            "numero_celular": numero_celular,
        }
        resp = ResponsavelAluno(**defaults)
        resp.save()
    else:
        if nome:
            resp.nome = nome
        if email:
            resp.email = email
        if tipo_responsavel is not None:
            resp.tipo_responsavel = tipo_responsavel
        if ddd_celular:
            resp.ddd_celular = ddd_celular
        if numero_celular:
            resp.numero_celular = numero_celular
        resp.save()

    return DadosResponsavelResumidoDTO(
        codigo_responsavel=resp.codigo_responsavel,
        cpf=resp.cpf,
        email=resp.email,
        nome=resp.nome,
        tipo_responsavel=resp.tipo_responsavel,
        ddd_celular=resp.ddd_celular,
        numero_celular=resp.numero_celular,
        codigo_aluno=str(codigo_aluno),
    )


def obter_dados_responsavel_filiacao(
    codigo_aluno: int,
) -> InformacoesAlunoDTO | None:
    """Retorna os dados de filiação do aluno."""
    return obter_informacoes_aluno(codigo_aluno=codigo_aluno)


def _consolidacao_por_turma(
    ano_letivo: int, ue_codigo: str
) -> list[ConsolidacaoMatriculaDTO]:
    """Conta matrículas válidas por turma em uma UE e ano letivo."""
    qs = Matricula.objects.filter(
        ano_letivo=ano_letivo,
        codigo_ue=ue_codigo,
        codigo_situacao_matricula__in=SITUACOES_MATRICULA_VALIDAS,
    ).values_list("codigo_matricula", flat=True)
    codigos = list(qs)
    if not codigos:
        return []

    agrupado = (
        MatriculaTurma.objects.filter(codigo_matricula__in=codigos)
        .values("codigo_turma")
        .annotate(quantidade=Count("id"))
        .order_by("codigo_turma")
    )
    return [
        ConsolidacaoMatriculaDTO(
            turma_codigo=str(r["codigo_turma"]),
            quantidade=r["quantidade"],
        )
        for r in agrupado
    ]


def obter_matriculas_ano_atual(
    ano_letivo: int, ue_codigo: str
) -> list[ConsolidacaoMatriculaDTO]:
    """Consolida matrículas válidas do ano atual por turma."""
    return _consolidacao_por_turma(ano_letivo=ano_letivo, ue_codigo=ue_codigo)


def obter_matriculas_anos_anteriores(
    ano_letivo: int, ue_codigo: str
) -> list[ConsolidacaoMatriculaDTO]:
    """Consolida matrículas válidas de um ano anterior por turma."""
    return _consolidacao_por_turma(ano_letivo=ano_letivo, ue_codigo=ue_codigo)


def obter_quantidade_alunos_por_turma_da_escola(
    codigo_escola: str,
) -> list[ConsolidacaoMatriculaDTO]:
    """Lista o total de matrículas por turma da escola."""
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
    """Retorna lista vazia: total por turno da UE.

    Funcionalidade fora do escopo deste serviço; retorna sempre lista vazia.
    """
    _ = ue_codigo
    return []


def obter_total_matriculas_por_turno_dre(dre_codigo: str) -> list[Any]:
    """Retorna lista vazia: total por turno da DRE.

    Funcionalidade fora do escopo deste serviço; retorna sempre lista vazia.
    """
    _ = dre_codigo
    return []


def obter_matriculas_aluno_na_escola(
    codigo_escola: str, codigo_aluno: int
) -> list[MatriculaEscolaAlunoDTO]:
    """Lista as matrículas do aluno na escola informada."""
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
        MatriculaEscolaAlunoDTO(
            codigo_aluno=m["aluno_id"],
            nome_aluno=aluno.get("nome", ""),
            nome_social_aluno=aluno.get("nome_social"),
            codigo_situacao_matricula=m["codigo_situacao_matricula"],
            situacao_matricula=m["situacao_matricula"],
            data_situacao=m["data_situacao_matricula"],
            codigo_turma=mts.get(m["codigo_matricula"], {}).get("codigo_turma")
            or 0,
            codigo_matricula=m["codigo_matricula"],
            ano_letivo=m["ano_letivo"],
        )
        for m in matriculas
    ]


def dto_to_dict(dto: Any) -> dict[str, Any]:
    """Faz a conversão de um DTO em dicionário."""
    return asdict(dto) if dto is not None else {}


def _exec_json_agg(sql: str, params: dict[str, Any]) -> bytes:
    """Executa consulta SQL que retorna JSON_AGG."""
    with connection.cursor() as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
    if not row or row[0] is None:
        return b"[]"
    return row[0].encode("utf-8")


def _dump_json_camel(payload: list[dict[str, Any]]) -> bytes:
    """Codifica payload Python em bytes JSON sem caracteres ASCII escapados."""
    return json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")


_SQL_A15_QUANTIDADE_POR_ANO_E_CC = """
SELECT json_agg(row_to_json(t))::text AS j FROM (
    SELECT
        mt.codigo_turma AS "codigo_turma",
        COUNT(*) AS quantidade,
        ROW_NUMBER() OVER (ORDER BY mt.codigo_turma) AS ordem
    FROM matricula m
    JOIN matricula_turma mt ON mt.codigo_matricula = m.codigo_matricula
    WHERE m.ano_letivo = %(ano)s
      AND m.codigo_situacao_matricula = ANY(%(situacoes)s)
      AND (%(ue)s::text IS NULL OR m.codigo_ue = %(ue)s)
    GROUP BY mt.codigo_turma
    ORDER BY mt.codigo_turma
) t
"""


def obter_quantidade_matriculados_por_ano_e_cc_json(
    ano_letivo: int,
    ue_id: str | None = None,
    componentes_curriculares: list[int] | None = None,  # NOSONAR
    dre_id: str | None = None,  # NOSONAR
) -> bytes:
    """Lista a quantidade de matriculados por ano e componente curricular."""
    if connection.vendor == "postgresql":
        return _exec_json_agg(
            _SQL_A15_QUANTIDADE_POR_ANO_E_CC,
            {
                "ano": ano_letivo,
                "situacoes": list(SITUACOES_MATRICULA_VALIDAS),
                "ue": ue_id or None,
            },
        )
    rows = obter_quantidade_matriculados_por_ano_e_cc(
        ano_letivo=ano_letivo,
        ue_id=ue_id,
        componentes_curriculares=componentes_curriculares,
        dre_id=dre_id,
    )
    return _dump_json_camel(
        [
            {
                "codigo_turma": r.codigo_turma,
                "quantidade": r.quantidade,
                "ordem": r.ordem,
            }
            for r in rows
        ]
    )


_SQL_A16_QUANTIDADE = """
SELECT json_agg(row_to_json(t))::text AS j FROM (
    SELECT
        COUNT(*) AS quantidade,
        ROW_NUMBER() OVER (ORDER BY m.codigo_ue, mt.codigo_turma) AS ordem,
        mt.codigo_turma AS "codigo_turma",
        m.codigo_ue AS "ue_codigo"
    FROM matricula m
    JOIN matricula_turma mt ON mt.codigo_matricula = m.codigo_matricula
    WHERE m.ano_letivo = %(ano)s
      AND m.codigo_situacao_matricula = ANY(%(situacoes)s)
      AND (%(ue)s::text IS NULL OR m.codigo_ue = %(ue)s)
    GROUP BY m.codigo_ue, mt.codigo_turma
    ORDER BY m.codigo_ue, mt.codigo_turma
) t
"""


def obter_quantidade_matriculados_json(
    ano_letivo: int,
    ue_codigo: str = "",
    dre_codigo: str = "",  # NOSONAR
    modalidade: list[int] | None = None,  # NOSONAR
    ano: list[int] | None = None,  # NOSONAR
    turma: list[str] | None = None,  # NOSONAR
) -> bytes:
    """Lista a quantidade de matriculados por turma e UE."""
    if connection.vendor == "postgresql":
        return _exec_json_agg(
            _SQL_A16_QUANTIDADE,
            {
                "ano": ano_letivo,
                "situacoes": list(SITUACOES_MATRICULA_VALIDAS),
                "ue": ue_codigo or None,
            },
        )
    rows = obter_quantidade_matriculados(
        ano_letivo=ano_letivo,
        ue_codigo=ue_codigo,
        dre_codigo=dre_codigo,
        modalidade=modalidade,
        ano=ano,
        turma=turma,
    )
    return _dump_json_camel(
        [
            {
                "quantidade": r.quantidade,
                "ordem": r.ordem,
                "codigo_turma": r.codigo_turma,
                "ueCodigo": r.ue_codigo,
            }
            for r in rows
        ]
    )


_SQL_A18_ACOMPANHAMENTO = """
SELECT json_agg(row_to_json(t))::text AS j FROM (
    SELECT
        m.codigo_aluno AS "codigo_eol",
        r.nome AS "nome_responsavel",
        r.cpf AS "cpf_responsavel",
        a.nome AS "nome",
        a.nome_social AS "nome_social",
        m.codigo_ue AS "codigo_escola",
        r.tipo_responsavel AS "tipo_responsavel",
        COALESCE(mt.codigo_turma, 0) AS "codigo_turma",
        m.situacao_matricula AS "situacao_matricula",
        a.data_nascimento AS "data_nascimento",
        m.data_situacao_matricula AS "data_situacao_matricula",
        m.ano_letivo AS "ano_letivo"
    FROM matricula m
    JOIN aluno a ON a.codigo_aluno = m.codigo_aluno
    LEFT JOIN LATERAL (
        SELECT codigo_turma
        FROM matricula_turma
        WHERE codigo_matricula = m.codigo_matricula
        LIMIT 1
    ) mt ON TRUE
    LEFT JOIN LATERAL (
        SELECT nome, cpf, tipo_responsavel
        FROM responsavel_aluno
        WHERE codigo_aluno = a.codigo_aluno
          AND data_fim_vinculo IS NULL
        ORDER BY tipo_responsavel DESC NULLS FIRST
        LIMIT 1
    ) r ON TRUE
    WHERE m.codigo_situacao_matricula = ANY(%(situacoes)s)
      AND (%(codigo_aluno)s::bigint IS NULL
           OR m.codigo_aluno = %(codigo_aluno)s::bigint)
      AND (%(codigo_ue)s::text IS NULL OR m.codigo_ue = %(codigo_ue)s)
      AND (%(ano_letivo)s::int IS NULL
           OR m.ano_letivo = %(ano_letivo)s::int)
      AND (%(turma_codigo)s::bigint IS NULL
           OR mt.codigo_turma = %(turma_codigo)s::bigint)
      AND (%(cpf)s::text IS NULL OR EXISTS (
          SELECT 1 FROM responsavel_aluno r2
          WHERE r2.codigo_aluno = m.codigo_aluno
            AND r2.cpf = %(cpf)s
            AND r2.data_fim_vinculo IS NULL
      ))
) t
"""


def obter_dados_acompanhamento_escolar_json(
    codigo_ue: str | None = None,
    ano_letivo: int | None = None,
    turma_codigo: str | None = None,
    codigo_aluno: int | None = None,
    cpf_responsavel: str | None = None,
    codigo_dre: str | None = None,  # NOSONAR
    modalidade: int | None = None,  # NOSONAR
    semestre: int | None = None,  # NOSONAR
) -> bytes:
    """Lista os dados de acompanhamento escolar, com filtros opcionais."""
    if connection.vendor == "postgresql":
        try:
            turma_int = int(turma_codigo) if turma_codigo else None
        except (TypeError, ValueError):
            return b"[]"
        return _exec_json_agg(
            _SQL_A18_ACOMPANHAMENTO,
            {
                "situacoes": list(SITUACOES_MATRICULA_VALIDAS),
                "codigo_aluno": codigo_aluno,
                "codigo_ue": codigo_ue or None,
                "ano_letivo": ano_letivo,
                "turma_codigo": turma_int,
                "cpf": cpf_responsavel or None,
            },
        )
    rows = obter_dados_acompanhamento_escolar(
        codigo_ue=codigo_ue,
        ano_letivo=ano_letivo,
        turma_codigo=turma_codigo,
        codigo_aluno=codigo_aluno,
        cpf_responsavel=cpf_responsavel,
        codigo_dre=codigo_dre,
        modalidade=modalidade,
        semestre=semestre,
    )
    return _dump_json_camel(
        [
            {
                "codigo_eol": r.codigo_eol,
                "nome_responsavel": r.nome_responsavel,
                "cpf_responsavel": r.cpf_responsavel,
                "nome": r.nome,
                "nome_social": r.nome_social,
                "codigo_escola": r.codigo_escola,
                "tipo_responsavel": r.tipo_responsavel,
                "codigo_turma": r.codigo_turma,
                "situacao_matricula": r.situacao_matricula,
                "data_nascimento": (
                    r.data_nascimento.isoformat()
                    if r.data_nascimento
                    else None
                ),
                "data_situacao_matricula": (
                    r.data_situacao_matricula.isoformat()
                    if r.data_situacao_matricula
                    else None
                ),
                "ano_letivo": r.ano_letivo,
            }
            for r in rows
        ]
    )


_SQL_A19_RESPONSAVEIS = """
SELECT json_agg(row_to_json(t))::text AS j FROM (
    SELECT
        m.codigo_ue AS "codigo_ue",
        COALESCE(mt.codigo_turma, 0) AS "codigo_turma",
        r.cpf AS "cpf_responsavel",
        m.codigo_aluno AS "codigo_aluno"
    FROM matricula m
    JOIN responsavel_aluno r
        ON r.codigo_aluno = m.codigo_aluno
       AND r.data_fim_vinculo IS NULL
       AND r.cpf IS NOT NULL
       AND r.cpf <> ''
    LEFT JOIN LATERAL (
        SELECT codigo_turma
        FROM matricula_turma
        WHERE codigo_matricula = m.codigo_matricula
        LIMIT 1
    ) mt ON TRUE
    WHERE m.codigo_situacao_matricula = ANY(%(situacoes)s)
      AND (%(codigo_ue)s::text IS NULL OR m.codigo_ue = %(codigo_ue)s)
      AND (%(ano_letivo)s::int IS NULL
           OR m.ano_letivo = %(ano_letivo)s::int)
) t
"""


def obter_responsaveis_dre_ue_turma_json(
    codigo_ue: str | None = None,
    ano_letivo: int | None = None,
    codigo_dre: str | None = None,  # NOSONAR
) -> bytes:
    """Lista os responsáveis vigentes agrupados por UE/turma."""
    if connection.vendor == "postgresql":
        return _exec_json_agg(
            _SQL_A19_RESPONSAVEIS,
            {
                "situacoes": list(SITUACOES_MATRICULA_ATIVAS),
                "codigo_ue": codigo_ue or None,
                "ano_letivo": ano_letivo,
            },
        )
    rows = obter_responsaveis_dre_ue_turma(
        codigo_ue=codigo_ue,
        ano_letivo=ano_letivo,
        codigo_dre=codigo_dre,
    )
    return _dump_json_camel(
        [
            {
                "codigo_ue": r.codigo_ue,
                "codigo_turma": r.codigo_turma,
                "cpf_responsavel": r.cpf_responsavel,
                "codigo_aluno": r.codigo_aluno,
            }
            for r in rows
        ]
    )


__all__ = [
    "AlunoAtivoTurmaDTO",
    "AlunoAutocompleteDTO",
    "ConsolidacaoMatriculaDTO",
    "DadosAcompanhamentoEscolarDTO",
    "DadosResponsavelDTO",
    "DadosResponsavelResumidoDTO",
    "InformacoesAlunoDTO",
    "InformacoesAlunoTurmaDTO",
    "MatriculaEscolaAlunoDTO",
    "NecessidadeEspecialDTO",
    "QuantidadeMatriculadosCCDTO",
    "QuantidadeMatriculadosDTO",
    "ResponsavelTurmaDTO",
    "TotalAlunosAtivosPeriodoDTO",
    "TurmaDoAlunoDTO",
    "atualizar_dados_responsavel_busca_ativa",
    "buscar_alunos_autocomplete",
    "buscar_alunos_ativos_autocomplete",
    "buscar_alunos_da_ue",
    "buscar_turmas_do_aluno",
    "buscar_turmas_do_aluno_por_situacao_matricula",
    "cadastrar_dados_responsavel",
    "dto_to_dict",
    "obter_alunos_ativos_por_periodo_e_turma",
    "obter_alunos_ativos_por_turma",
    "obter_alunos_por_codigos",
    "obter_alunos_por_codigos_e_ano",
    "obter_dados_acompanhamento_escolar",
    "obter_dados_acompanhamento_escolar_json",
    "obter_dados_responsavel",
    "obter_dados_responsavel_filiacao",
    "obter_dados_responsavel_resumido",
    "obter_informacoes_aluno",
    "obter_informacoes_alunos_da_turma",
    "obter_matriculas_ano_atual",
    "obter_matriculas_anos_anteriores",
    "obter_matriculas_aluno_na_escola",
    "obter_necessidades_especiais_por_aluno",
    "obter_quantidade_alunos_por_turma_da_escola",
    "obter_quantidade_matriculados",
    "obter_quantidade_matriculados_json",
    "obter_quantidade_matriculados_por_ano_e_cc",
    "obter_quantidade_matriculados_por_ano_e_cc_json",
    "obter_responsaveis_dre_ue_turma",
    "obter_responsaveis_dre_ue_turma_json",
    "obter_total_alunos_ativos_periodo",
    "obter_total_matriculas_por_turno_dre",
    "obter_total_matriculas_por_turno_ue",
]
