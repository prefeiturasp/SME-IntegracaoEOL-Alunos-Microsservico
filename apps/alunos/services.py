"""Services do domínio Alunos."""

import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import date, datetime
from typing import Any, cast

from django.db import connection
from django.db.models import Count, F, Max, Min, Q
from django.utils import timezone

from apps.alunos.enums import (
    SITUACOES_MATRICULA_ATIVAS,
    SITUACOES_MATRICULA_ATIVAS_TURMA,
    SITUACOES_MATRICULA_VALIDAS,
    SituacaoMatricula,
)
from apps.alunos.models import (
    Aluno,
    Matricula,
    MatriculaTurma,
    NecessidadeEspecialAluno,
    ResponsavelAluno,
    TipoNecessidadeEspecial,
)
from apps.core.utils import fim_do_dia, numero_chamada_int


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
    documento_cpf: str | None
    data_matricula: date | None
    numero_aluno_chamada: str | None
    codigo_turma: int
    data_atualizacao_contato: date | datetime | None
    nome_responsavel: str | None = None
    tipo_responsavel: int | None = None
    ddd_celular: str | None = None
    numero_celular: str | None = None
    codigo_escola: str | None = None
    codigo_tipo_turma: int | None = None
    data_atualizacao_tabela: date | datetime | None = None


@dataclass(frozen=True)
class AlunoAutocompleteDTO:
    """Dados básicos do aluno para autocomplete."""

    codigo_aluno: int
    nome_aluno: str
    nome_social_aluno: str | None
    codigo_turma: int
    numero_aluno_chamada: str | None
    turma: str | None = None
    modalidade: str | None = None


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
class AlunoAtivoDataAulaDTO:
    """Aluno ativo em uma turma até uma data de aula."""

    codigo_aluno: int
    nome_aluno: str
    nome_social_aluno: str | None
    data_nascimento: date | None
    codigo_situacao_matricula: int
    situacao_matricula: str
    data_situacao: datetime | None
    numero_aluno_chamada: str | None
    possui_deficiencia: bool
    codigo_matricula: int
    codigo_turma: int
    codigo_escola: str
    ano_letivo: int
    data_matricula: datetime | None
    nome_responsavel: str | None
    tipo_responsavel: int | None
    celular_responsavel: str | None
    data_atualizacao_contato: datetime | None
    sequencia: int | None
    codigo_dre: str


@dataclass(frozen=True)
class NecessidadeEspecialDTO:
    """Necessidade especial vinculada ao aluno."""

    codigo_aluno: int
    tipo_necessidade_especial: int
    descricao_necessidade_especial: str
    tipo_recurso: int | None
    descricao_recurso: str | None


@dataclass(frozen=True)
class InformacoesAlunoDTO:
    """Dados cadastrais do aluno."""

    codigo_aluno: int
    nome_aluno: str
    nome_social_aluno: str | None
    nome_mae: str | None
    sexo: str | None
    nacionalidade: str | None
    raca_cor: str | None
    nis: str | None
    cpf: str | None
    cns: str | None
    endereco: dict[str, Any] | None
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
    numero_chamada: int | None = None
    raca: str | None = None
    codigo_raca: int | None = None


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

    id: int
    cpf: str | None
    email: str | None
    nome: str | None
    tipo_responsavel: int | None
    data_nascimento: date | None
    data_atualizacao: date | datetime | None
    nome_mae: str | None
    ddd_celular: str | None
    numero_celular: str | None
    codigo_aluno: str | None


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

SITUACOES_MATRICULA_TURMA_ATIVAS = (1, 6, 10, 13)
_CODIGOS_RACA = {
    "BRANCA": 1,
    "PRETA": 2,
    "PARDA": 3,
    "AMARELA": 4,
    "INDIGENA": 5,
    "INDÍGENA": 5,
    "NAO INFORMADA": 6,
    "NÃO INFORMADA": 6,
}


def _modalidade_por_etapa(codigo_etapa_ensino: int | None) -> str | None:
    """Mapeia etapa de ensino para sigla de modalidade legada."""
    if codigo_etapa_ensino == 1:
        return "EI"
    if codigo_etapa_ensino in {2, 3, 7, 11}:
        return "EJA"
    if codigo_etapa_ensino in {4, 5, 12, 13}:
        return "EF"
    if codigo_etapa_ensino in {6, 8, 9, 14, 17}:
        return "EM"
    return None


def _codigo_raca(raca_cor: str | None) -> int | None:
    """Retorna o código legado da raça/cor quando conhecido."""
    if not raca_cor:
        return None
    return _CODIGOS_RACA.get(raca_cor.strip().upper())


def _colunas_responsavel_aluno() -> set[str]:
    """Lista colunas existentes na tabela de responsáveis."""
    with connection.cursor() as cursor:
        descricao = connection.introspection.get_table_description(
            cursor,
            ResponsavelAluno._meta.db_table,
        )
    return {col.name for col in descricao}


def _alunos_indexados(
    codigos_alunos: Sequence[int],
) -> dict[int, dict[str, Any]]:
    """Indexa dados básicos dos alunos por código EOL.

    Args:
        codigos_alunos: Códigos EOL dos alunos consultados.

    Returns:
        Dicionário indexado por ``codigo_aluno``.
    """
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
            "cns",
            "data_atualizacao_contato",
            "possui_deficiencia",
        )
    }


def _matricula_turma_por_matricula(
    codigos_matricula: Sequence[int],
) -> dict[int, dict[str, Any]]:
    """Indexa vínculos de matrícula com turma.

    Args:
        codigos_matricula: Códigos de matrícula consultados.

    Returns:
        Dicionário indexado por ``codigo_matricula``.
    """
    if not codigos_matricula:
        return {}
    saida: dict[int, dict[str, Any]] = {}
    for mt in (
        MatriculaTurma.objects.filter(codigo_matricula__in=codigos_matricula)
        .values(
            "codigo_matricula",
            "codigo_turma",
            "numero_chamada",
            "data_situacao_aluno",
            "data_situacao_aluno_data_hora",
            "codigo_situacao_aluno",
            "codigo_tipo_turma",
            "data_atualizacao_tabela",
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


def _todas_turmas_por_matricula(
    codigos_matricula: Sequence[int],
) -> dict[int, list[dict[str, Any]]]:
    """Retorna todas as turmas de cada matrícula.

    Args:
        codigos_matricula: Códigos de matrícula consultados.

    Returns:
        Dicionário indexado por ``codigo_matricula`` com lista de turmas.
    """
    if not codigos_matricula:
        return {}
    saida: dict[int, list[dict[str, Any]]] = {}
    for mt in (
        MatriculaTurma.objects.filter(codigo_matricula__in=codigos_matricula)
        .values(
            "codigo_matricula",
            "codigo_turma",
            "numero_chamada",
            "data_situacao_aluno",
            "data_situacao_aluno_data_hora",
            "codigo_situacao_aluno",
            "codigo_tipo_turma",
            "data_atualizacao_tabela",
        )
        .order_by(
            "codigo_matricula",
            "-data_situacao_aluno_data_hora",
            "-data_situacao_aluno",
        )
    ):
        saida.setdefault(mt["codigo_matricula"], []).append(mt)
    return saida


def _responsaveis_do_aluno(codigo_aluno: int) -> list[dict[str, Any]]:
    """Lista responsáveis de um aluno.

    Args:
        codigo_aluno: Código EOL do aluno.

    Returns:
        Dados dos Responsáveis.
    """
    return list(
        ResponsavelAluno.objects.filter(aluno_id=codigo_aluno)
        .order_by("codigo_responsavel")
        .values(
            "codigo_responsavel",
            "tipo_responsavel",
            "nome",
            "cpf",
            "email",
            "ddd_celular",
            "numero_celular",
            "endereco_id",
            "numero_endereco",
            "complemento",
            "bairro",
            "logradouro",
            "cep",
            "nome_municipio",
            "sigla_uf",
            "tipo_logradouro",
            "data_atualizacao_tabela",
        )
    )


def _endereco_responsavel(
    responsavel: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Monta o bloco de endereço do responsável.

    Args:
        responsavel: Dados do responsável usado como origem do endereço.

    Returns:
        Endereço no formato canônico do domínio, ou ``None``.
    """
    if not responsavel or not responsavel.get("endereco_id"):
        return None
    return {
        "id": responsavel.get("endereco_id"),
        "nro": responsavel.get("numero_endereco"),
        "complemento": responsavel.get("complemento"),
        "bairro": responsavel.get("bairro"),
        "cep": responsavel.get("cep"),
        "nome_municipio": responsavel.get("nome_municipio"),
        "sigla_uf": responsavel.get("sigla_uf"),
        "tipo_logradouro": responsavel.get("tipo_logradouro"),
        "logradouro": responsavel.get("logradouro"),
    }


def _codigo_situacao_turma(
    matricula: dict[str, Any], matricula_turma: dict[str, Any]
) -> int:
    """Resolve o código de situação usado.

    Args:
        matricula: Dados da matrícula.
        matricula_turma: Dados do vínculo matrícula-turma.

    Returns:
        Situação da matrícula-turma, ou situação da matrícula como fallback.
    """
    return cast(
        int,
        matricula_turma.get("codigo_situacao_aluno")
        or matricula["codigo_situacao_matricula"],
    )


def _matriculas_por_codigos_turma(
    codigos_turma: Sequence[int],
) -> list[dict[str, Any]]:
    """Consulta matrículas vinculadas a turmas.

    Args:
        codigos_turma: Códigos de turma usados no filtro.

    Returns:
        Matrículas enriquecidas com dados de matrícula-turma.
    """
    if not codigos_turma:
        return []
    mts = list(
        MatriculaTurma.objects.filter(
            codigo_turma__in=codigos_turma,
            codigo_situacao_aluno__in=SITUACOES_MATRICULA_VALIDAS,
        ).values(
            "codigo_matricula",
            "codigo_turma",
            "numero_chamada",
            "data_situacao_aluno",
            "codigo_situacao_aluno",
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
    """Obtém o responsável vigente prioritário do aluno.

    Args:
        codigo_aluno: Código EOL do aluno.

    Returns:
        Dados do responsável prioritário, ou ``None``.
    """
    responsavel = (
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
            "endereco_id",
            "numero_endereco",
            "complemento",
            "bairro",
            "logradouro",
            "cep",
            "nome_municipio",
            "sigla_uf",
            "tipo_logradouro",
            "data_atualizacao_tabela",
        )
        .first()
    )
    return cast(dict[str, Any] | None, responsavel)


def _qs_matriculas(
    codigo_aluno: int,
    ano_letivo: int | None,
    historico: bool,
    filtrar_situacao: bool,
) -> Any:
    """Monta queryset base de matrículas do aluno.

    Args:
        codigo_aluno: Código EOL do aluno.
        ano_letivo: Ano letivo filtrado, ou ``None`` para todos.
        historico: Indica se deve manter anos anteriores.
        filtrar_situacao: Indica se deve aplicar situações válidas.

    Returns:
        QuerySet de matrículas com os filtros aplicados.
    """
    qs = Matricula.objects.filter(aluno_id=codigo_aluno)
    if ano_letivo is not None:
        qs = qs.filter(ano_letivo=ano_letivo)
    if filtrar_situacao:
        qs = qs.filter(
            codigo_situacao_matricula__in=SITUACOES_MATRICULA_VALIDAS
        )
    if historico:
        qs = qs.filter(origem_atual=False)
    else:
        qs = qs.filter(origem_atual=True)
        if ano_letivo is None:
            qs = qs.filter(ano_letivo=timezone.now().year)
    return qs


def _consultar_turmas_do_aluno(
    codigo_aluno: int,
    ano_letivo: int | None = None,
    historico: bool = False,
    filtrar_situacao: bool = True,
    tipo_turma: bool = True,
) -> list[TurmaDoAlunoDTO]:
    """Consulta turmas e matrículas do aluno.

    Args:
        codigo_aluno: Código do aluno no EOL.
        ano_letivo: Filtra pelo ano letivo; ``None`` não aplica filtro de ano.
        historico: Inclui anos anteriores ao corrente quando ``True``.
        filtrar_situacao: Restringe às situações de matrícula válidas
            quando ``True``.
        tipo_turma: Exclui turmas do tipo programa (tipo 3) quando ``True``.

    Returns:
        Turmas e matrículas do aluno no formato do domínio.
    """
    matriculas = list(
        _qs_matriculas(codigo_aluno, ano_letivo, historico, filtrar_situacao)
        .values(
            "codigo_matricula",
            "aluno_id",
            "codigo_ue",
            "ano_letivo",
            "codigo_situacao_matricula",
            "situacao_matricula",
            "data_situacao_matricula",
            "data_situacao_matricula_data_hora",
        )
        .order_by("-ano_letivo", "codigo_situacao_matricula")
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
    responsavel = (
        ResponsavelAluno.objects.filter(aluno_id=codigo_aluno)
        .order_by("tipo_responsavel")
        .values(
            "nome",
            "tipo_responsavel",
            "ddd_celular",
            "numero_celular",
            "data_atualizacao_tabela",
        )
        .first()
        or {}
    )
    responsaveis = _responsaveis_do_aluno(codigo_aluno) or [responsavel]
    mts = _matricula_turma_por_matricula(
        [m["codigo_matricula"] for m in matriculas]
    )
    filtrar_tipo_regular = tipo_turma and any(
        mt.get("codigo_tipo_turma") is not None for mt in mts.values()
    )

    saida: list[TurmaDoAlunoDTO] = []
    for m in matriculas:
        mt = mts.get(m["codigo_matricula"], {})
        if filtrar_tipo_regular and mt.get("codigo_tipo_turma") == 3:
            continue
        codigo_situacao = _codigo_situacao_turma(m, mt)
        for resp in responsaveis:
            saida.append(
                TurmaDoAlunoDTO(
                    codigo_aluno=m["aluno_id"],
                    ano_letivo=m["ano_letivo"],
                    nome_aluno=aluno.get("nome", ""),
                    nome_social_aluno=aluno.get("nome_social"),
                    codigo_situacao_matricula=codigo_situacao,
                    situacao_matricula=SituacaoMatricula.get_descricao(
                        codigo_situacao
                    ),
                    data_situacao=(
                        mt.get("data_situacao_aluno_data_hora")
                        or mt.get("data_situacao_aluno")
                        or m.get("data_situacao_matricula_data_hora")
                        or m["data_situacao_matricula"]
                    ),
                    data_nascimento=aluno.get("data_nascimento"),
                    documento_cpf=aluno.get("cpf"),
                    data_matricula=(
                        m.get("data_situacao_matricula_data_hora")
                        or m["data_situacao_matricula"]
                    ),
                    numero_aluno_chamada=mt.get("numero_chamada"),
                    codigo_turma=mt.get("codigo_turma") or 0,
                    data_atualizacao_contato=aluno.get(
                        "data_atualizacao_contato"
                    ),
                    nome_responsavel=resp.get("nome"),
                    tipo_responsavel=resp.get("tipo_responsavel"),
                    ddd_celular=resp.get("ddd_celular"),
                    numero_celular=resp.get("numero_celular"),
                    codigo_escola=m["codigo_ue"],
                    codigo_tipo_turma=mt.get("codigo_tipo_turma"),
                    data_atualizacao_tabela=(
                        mt.get("data_atualizacao_tabela")
                        or mt.get("data_situacao_aluno_data_hora")
                        or mt.get("data_situacao_aluno")
                        or m.get("data_situacao_matricula_data_hora")
                        or m["data_situacao_matricula"]
                    ),
                )
            )
    return saida


def buscar_turmas_do_aluno(
    codigo_aluno: int,
    tipo_turma: bool = True,
    filtrar_situacao: bool = True,
) -> list[TurmaDoAlunoDTO]:
    """Lista as turmas do aluno no ano corrente.

    Args:
        codigo_aluno: Código EOL do aluno.
        tipo_turma: Exclui turmas do tipo programa (tipo 3) quando verdadeiro.
        filtrar_situacao: Restringe às situações de matrícula válidas quando
            verdadeiro.

    Returns:
        Turmas do aluno no ano corrente.
    """
    return _consultar_turmas_do_aluno(
        codigo_aluno=codigo_aluno,
        tipo_turma=tipo_turma,
        filtrar_situacao=filtrar_situacao,
    )


def buscar_turmas_do_aluno_por_situacao_matricula(
    codigo_aluno: int,
    ano_letivo: int | None,
    filtrar_situacao_matricula: bool = True,
) -> list[TurmaDoAlunoDTO]:
    """Busca turmas filtradas por situação de matrícula.

    Args:
        codigo_aluno: Código EOL do aluno.
        ano_letivo: Ano letivo usado no filtro.
        filtrar_situacao_matricula: Indica se aplica filtro de situação.

    Returns:
        Turmas do aluno conforme os filtros aplicados.
    """
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
    """Lista alunos da UE no ano letivo.

    Args:
        codigo_ue: Código EOL da UE.
        ano_letivo: Ano letivo da consulta.
        nome_aluno: Filtro por substring (case-insensitive) do nome.
        codigo_eol: Filtro pelo código EOL exato; valor não numérico
            resulta em lista vazia.

    Returns:
        Alunos matriculados na UE com matrícula em situação válida.
    """
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
            "data_situacao_matricula_data_hora",
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
            documento_cpf=alunos_idx.get(m["aluno_id"], {}).get("cpf"),
            data_matricula=m["data_situacao_matricula"],
            numero_aluno_chamada=mts.get(m["codigo_matricula"], {}).get(
                "numero_chamada"
            ),
            codigo_turma=mts.get(m["codigo_matricula"], {}).get("codigo_turma")
            or 0,
            data_atualizacao_contato=alunos_idx.get(m["aluno_id"], {}).get(
                "data_atualizacao_contato"
            ),
            codigo_escola=m["codigo_ue"],
            codigo_tipo_turma=mts.get(m["codigo_matricula"], {}).get(
                "codigo_tipo_turma"
            ),
        )
        for m in matriculas
    ]


def _resolver_matriculas_e_mts_idx(
    matriculas: list[dict],
    codigo_turmas: Sequence[int] | None,
) -> tuple[list[dict], dict]:
    """Resolve matrículas e índice de matrícula-turma.

    Args:
        matriculas: Matrículas candidatas ao retorno.
        codigo_turmas: Códigos de turma usados como filtro opcional.

    Returns:
        Tupla com matrículas filtradas e índice por ``codigo_matricula``.
    """
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
    """Resolve autocomplete de alunos a partir de filtros opcionais.

    Args:
        codigo_ue: Código EOL da UE.
        ano_letivo: Ano letivo usado como filtro opcional.
        codigo_turmas: Turmas usadas como filtro opcional.
        nome_aluno: Substring de nome usada como filtro opcional.
        codigo_eol: Código EOL exato do aluno.
        somente_ativos: Indica se usa apenas situações ativas.
        limite: Máximo de itens retornados.

    Returns:
        Alunos compatíveis com os filtros de autocomplete.
    """
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
    """Busca alunos para autocomplete da UE/ano.

    Args:
        codigo_ue: Código EOL da UE.
        ano_letivo: Ano letivo da consulta.
        codigo_turmas: Restringe pelas turmas informadas.
        nome_aluno: Filtro por substring do nome (case-insensitive).
        codigo_eol: Filtro pelo código EOL exato.
        somente_ativos: Se ``True``, considera apenas situações ativas.
        eh_historico: Mantido por compatibilidade; sem efeito.
        limite: Máximo de resultados retornados.

    Returns:
        Alunos compatíveis com os filtros, limitados por ``limite``.
    """
    return _autocomplete_base(
        codigo_ue=codigo_ue,
        ano_letivo=ano_letivo,
        codigo_turmas=codigo_turmas,
        nome_aluno=nome_aluno,
        codigo_eol=codigo_eol,
        somente_ativos=somente_ativos,
        limite=limite,
    )


def _qs_matriculas_ativas_ue(
    ue_codigo: str,
    referencia: date | None,
    aluno_codigo: int,
    nome_l: str,
) -> Any:
    """Monta o queryset de matrículas ativas da UE para autocomplete.

    Args:
        ue_codigo: Código EOL da UE.
        referencia: Inclui situações alteradas após a data, quando informada.
        aluno_codigo: Código EOL do aluno, ou ``0`` para ignorar.
        nome_l: Substring do nome em minúsculas, ou vazia para ignorar.

    Returns:
        QuerySet de matrículas com os filtros aplicados, ordenado por nome.
    """
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
    """Indexa matrículas-turma ativas regulares por matrícula.

    Considera apenas situações ativas de matrícula-turma e exclui turmas
    de programa (tipo 3).

    Args:
        codigos_matricula: Códigos de matrícula consultados.

    Returns:
        Índice de matrícula-turma por ``codigo_matricula``.
    """
    mts = (
        MatriculaTurma.objects.filter(
            codigo_matricula__in=codigos_matricula,
            codigo_situacao_aluno__in=SITUACOES_MATRICULA_TURMA_ATIVAS,
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


def _montar_autocomplete_ativos(
    matriculas: list[dict[str, Any]],
    mts_idx: dict[int, dict[str, Any]],
    nome_l: str,
    limite: int,
) -> list[AlunoAutocompleteDTO]:
    """Monta os DTOs de autocomplete de alunos ativos.

    Args:
        matriculas: Matrículas elegíveis ao retorno.
        mts_idx: Índice de matrícula-turma por ``codigo_matricula``.
        nome_l: Substring do nome em minúsculas, ou vazia para ignorar.
        limite: Máximo de itens retornados.

    Returns:
        DTOs de autocomplete ordenados por nome.
    """
    alunos_idx = _alunos_indexados([m["aluno_id"] for m in matriculas])
    saida: list[AlunoAutocompleteDTO] = []
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
            AlunoAutocompleteDTO(
                codigo_aluno=m["aluno_id"],
                nome_aluno=nome,
                nome_social_aluno=a.get("nome_social"),
                codigo_turma=mt.get("codigo_turma") or 0,
                numero_aluno_chamada=mt.get("numero_chamada"),
                turma=mt.get("nome_turma"),
                modalidade=_modalidade_por_etapa(
                    mt.get("codigo_etapa_ensino")
                ),
            )
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
) -> list[AlunoAutocompleteDTO]:
    """Busca alunos ativos para autocomplete.

    Args:
        ue_codigo: Código EOL da UE.
        aluno_nome: Substring do nome do aluno.
        aluno_codigo: Código EOL do aluno, ou ``0`` para ignorar.
        data_referencia: Mantido por compatibilidade; sem efeito atual.
        limite: Máximo de resultados retornados.

    Returns:
        Alunos ativos compatíveis com os filtros.
    """
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

    return _montar_autocomplete_ativos(matriculas, mts_idx, nome_l, limite)


def obter_total_alunos_ativos_periodo(
    ano_letivo: int,
    data_inicio: datetime | date,
    data_fim: datetime | date,
    ue_id: str | None = None,
    ano_turma: str | None = None,  # NOSONAR
    dre_id: str | None = None,  # NOSONAR
    modalidades: list[int] | None = None,  # NOSONAR
) -> TotalAlunosAtivosPeriodoDTO:
    """Conta alunos distintos com matrícula ativa no intervalo.

    Args:
        ano_letivo: Ano letivo da consulta.
        data_inicio: Data inicial do intervalo (inclusiva).
        data_fim: Data final do intervalo (inclusiva).
        ue_id: Restringe à UE informada.
        ano_turma: Mantido por compatibilidade; sem efeito atual.
        dre_id: Mantido por compatibilidade; sem efeito atual.
        modalidades: Mantido por compatibilidade; sem efeito atual.

    Returns:
        DTO com a quantidade de alunos ativos distintos no período.
    """
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
    """Lista alunos da turma com filtro opcional por janela de datas.

    Args:
        codigo_turma: Código EOL da turma.
        data_referencia_inicio: Data inicial opcional da janela.
        data_referencia_fim: Data final opcional da janela.

    Returns:
        Alunos da turma compatíveis com o período informado.
    """
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
    """Retorna alunos ativos em uma turma por período.

    Args:
        codigo_turma: Código EOL da turma.
        data_referencia_fim: Data final da janela de referência.
        data_referencia_inicio: Data inicial da janela de referência.

    Returns:
        Alunos ativos encontrados para a turma e período.
    """
    return _consultar_alunos_ativos_turma(
        codigo_turma=codigo_turma,
        data_referencia_inicio=data_referencia_inicio,
        data_referencia_fim=data_referencia_fim,
    )


def obter_alunos_ativos_por_turma(
    codigo_turma: int,
) -> list[AlunoAtivoTurmaDTO]:
    """Retorna alunos ativos em uma turma.

    Args:
        codigo_turma: Código EOL da turma.

    Returns:
        Alunos ativos encontrados para a turma.
    """
    return _consultar_alunos_ativos_turma(codigo_turma=codigo_turma)


def _data_matricula_por_matricula(
    codigos_matricula: Sequence[int],
) -> dict[int, datetime | None]:
    """Indexa a menor data de situação na turma por matrícula.

    Args:
        codigos_matricula: Códigos de matrícula consultados.

    Returns:
        Menor ``data_situacao_aluno_data_hora`` por ``codigo_matricula``.
    """
    if not codigos_matricula:
        return {}
    return {
        m["codigo_matricula"]: m["menor_data"]
        for m in MatriculaTurma.objects.filter(
            codigo_matricula__in=codigos_matricula
        )
        .values("codigo_matricula")
        .annotate(menor_data=Min("data_situacao_aluno_data_hora"))
    }


def _responsavel_tem_celular(resp: dict[str, Any]) -> bool:
    """Indica se o responsável possui DDD ou número de celular."""
    return bool(resp.get("ddd_celular") or resp.get("numero_celular"))


def _responsaveis_por_aluno(
    codigos_alunos: Sequence[int],
) -> dict[int, dict[str, Any]]:
    """Indexa o responsável prioritário por aluno.

    Args:
        codigos_alunos: Códigos EOL dos alunos consultados.

    Returns:
        Dicionário indexado por ``codigo_aluno``.
    """
    if not codigos_alunos:
        return {}
    saida: dict[int, dict[str, Any]] = {}
    for resp in (
        ResponsavelAluno.objects.filter(
            aluno_id__in=codigos_alunos, data_fim_vinculo__isnull=True
        )
        .order_by("aluno_id", "tipo_responsavel", "codigo_responsavel")
        .values(
            "aluno_id",
            "nome",
            "tipo_responsavel",
            "ddd_celular",
            "numero_celular",
        )
    ):
        atual = saida.get(resp["aluno_id"])
        if atual is None or (
            not _responsavel_tem_celular(atual)
            and _responsavel_tem_celular(resp)
        ):
            saida[resp["aluno_id"]] = resp
    return saida


def _chave_dedup(row: dict[str, Any]) -> tuple[datetime, str]:
    """Chave de desempate da dedup legada (data de situação, chamada).

    Simula ``OrderByDescending(DataSituacao).ThenByDescending(
    NumeroAlunoChamada).First()`` do handler legado: vence a linha de
    maior ``data_situacao_aluno_data_hora`` e, no empate, maior
    ``numero_chamada`` (comparação de string, como no legado).
    """
    return (
        row["data_situacao_aluno_data_hora"] or datetime.min,
        row["numero_chamada"] or "",
    )


def _dedup_alunos_ativos_turma(
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Deduplica os registros da turma conforme o legado.

    Args:
        rows: Registros combinados de matrícula e matrícula-turma.

    Returns:
        Um registro por aluno distinto, na ordem do primeiro encontrado.
    """
    por_aluno: dict[int, dict[str, Any]] = {}
    for row in rows:
        atual = por_aluno.get(row["aluno_id"])
        if atual is None or _chave_dedup(row) > _chave_dedup(atual):
            por_aluno[row["aluno_id"]] = row
    return list(por_aluno.values())


def _montar_aluno_matricula_turma(
    row: dict[str, Any],
    alunos_idx: dict[int, dict[str, Any]],
    responsaveis_idx: dict[int, dict[str, Any]],
    data_matricula_idx: dict[int, datetime | None],
) -> AlunoAtivoDataAulaDTO:
    """Monta os dados do aluno a partir do registro deduplicado."""
    aluno = alunos_idx.get(row["aluno_id"], {})
    resp = responsaveis_idx.get(row["aluno_id"], {})
    celular = None
    if resp.get("ddd_celular") or resp.get("numero_celular"):
        celular = f"{resp.get('ddd_celular') or ''}" + (
            resp.get("numero_celular") or ""
        )
    codigo_situacao = row["codigo_situacao_aluno"]
    return AlunoAtivoDataAulaDTO(
        codigo_aluno=row["aluno_id"],
        nome_aluno=aluno.get("nome", ""),
        nome_social_aluno=aluno.get("nome_social"),
        data_nascimento=aluno.get("data_nascimento"),
        codigo_situacao_matricula=codigo_situacao,
        situacao_matricula=SituacaoMatricula.get_descricao(codigo_situacao),
        data_situacao=row["data_situacao_aluno_data_hora"],
        numero_aluno_chamada=row["numero_chamada"],
        possui_deficiencia=aluno.get("possui_deficiencia", False),
        codigo_matricula=row["codigo_matricula"],
        codigo_turma=row["codigo_turma"],
        codigo_escola=row["codigo_ue"],
        ano_letivo=row["ano_letivo"],
        data_matricula=data_matricula_idx.get(row["codigo_matricula"]),
        nome_responsavel=resp.get("nome"),
        tipo_responsavel=resp.get("tipo_responsavel"),
        celular_responsavel=celular,
        data_atualizacao_contato=aluno.get("data_atualizacao_contato"),
        sequencia=row["sequencia"],
        codigo_dre=row["codigo_dre"],
    )


def _atende_condicao_data_matricula(row: dict[str, Any], limite: date) -> bool:
    """Avalia a condição composta do legado por data de matrícula.

    Aplica a mesma condição do legado ``BuscaAlunosPorTurmaDataMatricula``
    onde se verifica se a data de situação da matrícula 
    for anterior ou igual ao limite.

    Args:
        row: Registro combinado de matrícula e matrícula-turma.
        limite: Data de matrícula derivada dos ticks .NET.
    """
    data_situacao = row["data_situacao_aluno_data_hora"]
    data_matricula = row["data_situacao_matricula_data_hora"]
    situacao_valida = (
        row["codigo_situacao_aluno"] in SITUACOES_MATRICULA_VALIDAS
    )
    por_situacao = (
        data_situacao is not None
        and data_situacao.date() <= limite
        and not situacao_valida
    )
    por_matricula = (
        data_matricula is not None and data_matricula.date() <= limite
    )
    return por_situacao or por_matricula


def obter_alunos_ativos_turma_por_data_aula(
    codigo_turma: int,
    data_aula: datetime | None,
    data_matricula: datetime | None = None,
    codigo_aluno: int | None = None,
    considerar_inativos: bool = False,
    sequencia: int | None = None,
) -> list[AlunoAtivoDataAulaDTO]:
    """Lista os alunos de uma turma conforme os filtros informados.

    Args:
        codigo_turma: Código EOL da turma.
        data_aula: Data de aula derivada dos ticks .NET; ``None`` (ticks
            iguais a zero) não filtra por data. Com ``data_aula`` e
            ``data_matricula`` nulas e ``sequencia`` igual a ``1``, ordena o
            resultado por ``numero_chamada`` crescente.
        data_matricula: Data de matrícula derivada dos ticks .NET; quando
            informada, aplica a condição composta do legado, descarta Vínculo
            Indevido e ordena o resultado por nome do aluno.
        codigo_aluno: Quando informado, restringe o resultado ao aluno
            correspondente.
        considerar_inativos: Quando ``False`` (padrão), restringe às situações
            ``(1, 2, 3, 5, 6, 10, 13)``. Quando ``True``, preserva o legado e
            não filtra por situação.
        sequencia: Quando informado, restringe matrícula-turma àquela
            ``sequencia``; ``None`` traz todas as sequências.

    Returns:
        Alunos distintos na turma conforme os filtros informados.
    """
    filtros: dict[str, Any] = {"codigo_turma": codigo_turma}
    if data_aula is not None:
        filtros["data_situacao_aluno_data_hora__lte"] = fim_do_dia(data_aula)
    if sequencia is not None:
        filtros["sequencia"] = sequencia

    mts = list(
        MatriculaTurma.objects.filter(**filtros).values(
            "codigo_matricula",
            "codigo_turma",
            "numero_chamada",
            "sequencia",
            "codigo_situacao_aluno",
            "data_situacao_aluno_data_hora",
        )
    )
    if not mts:
        return []

    matriculas_idx = {
        m["codigo_matricula"]: m
        for m in Matricula.objects.filter(
            codigo_matricula__in=[mt["codigo_matricula"] for mt in mts],
        ).values(
            "codigo_matricula",
            "aluno_id",
            "codigo_ue",
            "codigo_dre",
            "ano_letivo",
            "data_situacao_matricula_data_hora",
        )
    }
    rows = [
        {**matriculas_idx[mt["codigo_matricula"]], **mt}
        for mt in mts
        if mt["codigo_matricula"] in matriculas_idx
    ]
    if codigo_aluno is not None:
        rows = [r for r in rows if r["aluno_id"] == codigo_aluno]
    if data_matricula is not None:
        limite = data_matricula.date()
        rows = [r for r in rows if _atende_condicao_data_matricula(r, limite)]
    if not rows:
        return []

    finais = _dedup_alunos_ativos_turma(rows)
    if not considerar_inativos:
        finais = [
            r
            for r in finais
            if r["codigo_situacao_aluno"] in SITUACOES_MATRICULA_ATIVAS_TURMA
        ]
    if data_matricula is not None:
        finais = [
            r
            for r in finais
            if r["codigo_situacao_aluno"] != SituacaoMatricula.VINCULO_INDEVIDO
        ]
    codigos_alunos = [r["aluno_id"] for r in finais]
    alunos_idx = _alunos_indexados(codigos_alunos)
    responsaveis_idx = _responsaveis_por_aluno(codigos_alunos)
    data_matricula_idx = _data_matricula_por_matricula(
        [r["codigo_matricula"] for r in finais]
    )
    if data_matricula is not None:
        finais.sort(
            key=lambda r: alunos_idx.get(r["aluno_id"], {}).get("nome", "")
        )
    elif data_aula is None and sequencia == 1:
        finais.sort(
            key=lambda r: (
                numero_chamada_int(r["numero_chamada"]) is None,
                numero_chamada_int(r["numero_chamada"]) or 0,
            )
        )
    return [
        _montar_aluno_matricula_turma(
            r, alunos_idx, responsaveis_idx, data_matricula_idx
        )
        for r in finais
    ]


def obter_necessidades_especiais_por_aluno(
    codigo_aluno: int,
) -> list[NecessidadeEspecialDTO]:
    """Retorna necessidades especiais cadastradas para o aluno.

    Args:
        codigo_aluno: Código EOL do aluno.

    Returns:
        Necessidades especiais vinculadas ao aluno.
    """
    rows = list(
        NecessidadeEspecialAluno.objects.filter(aluno_id=codigo_aluno).values(
            "aluno_id",
            "necessidade_especial_id",
            "codigo_tipo_recurso",
            "descricao_tipo_recurso",
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
            tipo_recurso=r.get("codigo_tipo_recurso"),
            descricao_recurso=r.get("descricao_tipo_recurso"),
        )
        for r in rows
    ]


def obter_alunos_por_codigos_e_ano(
    codigos_aluno: Sequence[int], ano_letivo: int
) -> list[TurmaDoAlunoDTO]:
    """Lista turmas dos alunos informados por ano letivo.

    Args:
        codigos_aluno: Códigos EOL dos alunos.
        ano_letivo: Ano letivo usado no filtro.

    Returns:
        Turmas dos alunos restritas ao ano informado.
    """
    if not codigos_aluno:
        return []
    eh_historico = ano_letivo != timezone.now().year
    saida: list[TurmaDoAlunoDTO] = []
    for codigo in codigos_aluno:
        saida.extend(
            _consultar_turmas_do_aluno(
                codigo_aluno=codigo,
                ano_letivo=ano_letivo,
                historico=eh_historico,
                filtrar_situacao=True,
            )
        )
    return saida


def _turmas_atuais_por_aluno(codigo_aluno: int) -> list[TurmaDoAlunoDTO]:
    """Retorna turmas atuais do aluno.

    Args:
        codigo_aluno: Código EOL do aluno.

    Returns:
        Turmas baseadas nas matrículas com ``origem_atual=True``.
    """
    matriculas = list(
        Matricula.objects.filter(aluno_id=codigo_aluno, origem_atual=True)
        .values(
            "codigo_matricula",
            "aluno_id",
            "codigo_ue",
            "ano_letivo",
            "codigo_situacao_matricula",
            "situacao_matricula",
            "data_situacao_matricula",
            "data_situacao_matricula_data_hora",
        )
        .order_by(
            "ano_letivo",
            "data_situacao_matricula_data_hora",
            "data_situacao_matricula",
        )
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
    responsaveis = _responsaveis_do_aluno(codigo_aluno) or [{}]
    mts_all = _todas_turmas_por_matricula(
        [m["codigo_matricula"] for m in matriculas]
    )

    saida: list[TurmaDoAlunoDTO] = []
    for m in matriculas:
        turmas = mts_all.get(m["codigo_matricula"]) or [{}]
        codigo_situacao = _codigo_situacao_turma(m, turmas[0])
        for mt in turmas:
            for responsavel in responsaveis:
                data_situacao = (
                    mt.get("data_situacao_aluno_data_hora")
                    or mt.get("data_situacao_aluno")
                    or m.get("data_situacao_matricula_data_hora")
                    or m["data_situacao_matricula"]
                )
                saida.append(
                    TurmaDoAlunoDTO(
                        codigo_aluno=m["aluno_id"],
                        ano_letivo=m["ano_letivo"],
                        nome_aluno=aluno.get("nome", ""),
                        nome_social_aluno=aluno.get("nome_social"),
                        codigo_situacao_matricula=codigo_situacao,
                        situacao_matricula=SituacaoMatricula.get_descricao(
                            codigo_situacao
                        ),
                        data_situacao=data_situacao,
                        data_nascimento=aluno.get("data_nascimento"),
                        documento_cpf=aluno.get("cpf"),
                        data_matricula=(
                            m.get("data_situacao_matricula_data_hora")
                            or m["data_situacao_matricula"]
                        ),
                        numero_aluno_chamada=mt.get("numero_chamada"),
                        codigo_turma=mt.get("codigo_turma") or 0,
                        data_atualizacao_contato=aluno.get(
                            "data_atualizacao_contato"
                        ),
                        nome_responsavel=responsavel.get("nome"),
                        tipo_responsavel=responsavel.get("tipo_responsavel"),
                        ddd_celular=responsavel.get("ddd_celular"),
                        numero_celular=responsavel.get("numero_celular"),
                        codigo_escola=m["codigo_ue"],
                        codigo_tipo_turma=mt.get("codigo_tipo_turma"),
                        data_atualizacao_tabela=(
                            mt.get("data_atualizacao_tabela") or data_situacao
                        ),
                    )
                )
    return saida


def obter_alunos_por_codigos(
    codigos_aluno: Sequence[int],
) -> list[TurmaDoAlunoDTO]:
    """Lista turmas atuais dos alunos informados.

    Args:
        codigos_aluno: Códigos EOL dos alunos.

    Returns:
        Turmas atuais encontradas para os alunos.
    """
    if not codigos_aluno:
        return []
    saida: list[TurmaDoAlunoDTO] = []
    for codigo in codigos_aluno:
        saida.extend(_turmas_atuais_por_aluno(codigo))
    return saida


def obter_informacoes_aluno(
    codigo_aluno: int,
) -> InformacoesAlunoDTO | None:
    """Retorna informações cadastrais do aluno.

    Args:
        codigo_aluno: Código EOL do aluno.

    Returns:
        Informações cadastrais do aluno, ou ``None`` quando não existir.
    """
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
        cns=aluno.cns,
        endereco=_endereco_responsavel(_responsavel_principal(codigo_aluno)),
        data_nascimento=aluno.data_nascimento,
        possui_deficiencia=aluno.possui_deficiencia,
    )


def obter_informacoes_alunos_da_turma(
    codigo_turma: int,
) -> list[InformacoesAlunoTurmaDTO]:
    """Lista informações dos alunos de uma turma.

    Args:
        codigo_turma: Código EOL da turma.
    """
    rows = _matriculas_por_codigos_turma([codigo_turma])
    rows_validas = [
        r
        for r in rows
        if r["codigo_situacao_matricula"] in SITUACOES_MATRICULA_VALIDAS
    ]
    if not rows_validas:
        return []

    alunos_idx = _alunos_indexados([r["aluno_id"] for r in rows_validas])
    saida = [
        InformacoesAlunoTurmaDTO(
            numero_aluno_chamada=r["numero_chamada"],
            codigo_aluno=r["aluno_id"],
            nome_aluno=alunos_idx.get(r["aluno_id"], {}).get("nome", ""),
            nome_social_aluno=alunos_idx.get(r["aluno_id"], {}).get(
                "nome_social"
            ),
            sexo=alunos_idx.get(r["aluno_id"], {}).get("sexo"),
            raca_cor=alunos_idx.get(r["aluno_id"], {}).get("raca_cor"),
            numero_chamada=numero_chamada_int(r["numero_chamada"]),
            raca=alunos_idx.get(r["aluno_id"], {}).get("raca_cor"),
            codigo_raca=_codigo_raca(
                alunos_idx.get(r["aluno_id"], {}).get("raca_cor")
            ),
        )
        for r in rows_validas
    ]
    return sorted(saida, key=lambda item: item.nome_aluno)


def obter_quantidade_matriculados_por_ano_e_cc(
    ano_letivo: int,
    ue_id: str | None = None,
    componentes_curriculares: list[int] | None = None,  # NOSONAR
    dre_id: str | None = None,  # NOSONAR
) -> list[QuantidadeMatriculadosCCDTO]:
    """Agrupa matrículas por turma no ano letivo.

    Args:
        ano_letivo: Ano letivo usado no filtro.
        ue_id: Código EOL da UE usado como filtro opcional.
        componentes_curriculares: Mantido por compatibilidade; sem efeito.
        dre_id: Mantido por compatibilidade; sem efeito atual.

    Returns:
        Quantidades de matrículas agrupadas por turma.
    """
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
    """Lista quantidade de matriculados por UE e turma.

    Args:
        ano_letivo: Ano letivo usado no filtro.
        ue_codigo: Código EOL da UE usado como filtro opcional.
        dre_codigo: Mantido por compatibilidade; sem efeito atual.
        modalidade: Mantido por compatibilidade; sem efeito atual.
        ano: Mantido por compatibilidade; sem efeito atual.
        turma: Mantido por compatibilidade; sem efeito atual.

    Returns:
        Quantidades de matrículas agregadas por UE e turma.
    """
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
    """Lista dados de acompanhamento escolar.

    Args:
        codigo_ue: Código EOL da UE usado como filtro opcional.
        ano_letivo: Ano letivo usado como filtro opcional.
        turma_codigo: Código da turma usado como filtro opcional.
        codigo_aluno: Código EOL do aluno usado como filtro opcional.
        cpf_responsavel: CPF do responsável usado como filtro opcional.
        codigo_dre: Mantido por compatibilidade; sem efeito atual.
        modalidade: Mantido por compatibilidade; sem efeito atual.
        semestre: Mantido por compatibilidade; sem efeito atual.

    Returns:
        Dados de acompanhamento escolar compatíveis com os filtros.
    """
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
    """Lista responsáveis vigentes agrupados por UE e turma.

    Args:
        codigo_ue: Código EOL da UE usado como filtro opcional.
        ano_letivo: Ano letivo usado como filtro opcional.
        codigo_dre: Mantido por compatibilidade; sem efeito atual.

    Returns:
        Responsáveis vigentes por UE, turma e aluno.
    """
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
    """Lista os vínculos de um responsável a partir do CPF.

    Args:
        cpf_responsavel: CPF do responsável. Valor vazio retorna ``[]``.

    Returns:
        Vínculos encontrados para o CPF informado.
    """
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
    """Retorna dados resumidos do responsável.

    Args:
        cpf_responsavel: CPF do responsável.

    Returns:
        Dados resumidos do responsável, ou ``None`` se não encontrado.
    """
    cpf = (cpf_responsavel or "").strip()
    if not cpf:
        return None
    campos = [
        "codigo_responsavel",
        "aluno_id",
        "tipo_responsavel",
        "nome",
        "email",
        "cpf",
        "ddd_celular",
        "numero_celular",
        "data_atualizacao_tabela",
    ]
    colunas = _colunas_responsavel_aluno()
    if "data_nascimento" in colunas:
        campos.append("data_nascimento")
    if "nome_mae" in colunas:
        campos.append("nome_mae")
    v = (
        ResponsavelAluno.objects.filter(cpf=cpf, data_fim_vinculo__isnull=True)
        .order_by("-data_atualizacao_tabela")
        .values(*campos)
        .first()
    )
    if v is None:
        return None
    return DadosResponsavelResumidoDTO(
        id=v["codigo_responsavel"],
        cpf=v["cpf"],
        email=v["email"],
        nome=v["nome"],
        tipo_responsavel=v["tipo_responsavel"],
        data_nascimento=v.get("data_nascimento"),
        data_atualizacao=v["data_atualizacao_tabela"],
        nome_mae=v.get("nome_mae"),
        ddd_celular=v["ddd_celular"],
        numero_celular=v["numero_celular"],
        codigo_aluno=None,
    )


def atualizar_dados_responsavel_busca_ativa(
    codigo_aluno: int,
    cpf_responsavel: str,
    *,
    email: str | None = None,
    ddd_celular: str | None = None,
    numero_celular: str | None = None,
) -> DadosResponsavelResumidoDTO:
    """Atualiza contatos do responsável no fluxo de busca ativa.

    Args:
        codigo_aluno: Código EOL do aluno vinculado.
        cpf_responsavel: CPF do responsável a atualizar.
        email: Novo e-mail; ``None`` mantém o valor atual.
        ddd_celular: Novo DDD; ``None`` mantém o valor atual.
        numero_celular: Novo número; ``None`` mantém o valor atual.

    Returns:
        Dados resumidos do responsável após a atualização. Quando o
        vínculo não existir, devolve um DTO sintético com os dados
        recebidos e ``codigo_responsavel=0``.
    """
    resp = ResponsavelAluno.objects.filter(
        cpf=cpf_responsavel, aluno_id=codigo_aluno
    ).first()
    if resp is None:
        return DadosResponsavelResumidoDTO(
            id=0,
            cpf=cpf_responsavel,
            email=email,
            nome=None,
            tipo_responsavel=None,
            data_nascimento=None,
            data_atualizacao=None,
            nome_mae=None,
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
        id=resp.codigo_responsavel,
        cpf=resp.cpf,
        email=resp.email,
        nome=resp.nome,
        tipo_responsavel=resp.tipo_responsavel,
        data_nascimento=None,
        data_atualizacao=getattr(resp, "data_atualizacao_tabela", None),
        nome_mae=None,
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
    """Cria ou atualiza um vínculo responsável-aluno.

    Args:
        codigo_aluno: Código EOL do aluno vinculado.
        cpf_responsavel: CPF do responsável.
        nome: Nome do responsável.
        email: E-mail de contato.
        tipo_responsavel: Tipo do vínculo (mãe, pai, guardião, etc.).
        ddd_celular: DDD do celular.
        numero_celular: Número do celular.

    Returns:
        Dados resumidos do responsável após a operação.
    """
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
        id=resp.codigo_responsavel,
        cpf=resp.cpf,
        email=resp.email,
        nome=resp.nome,
        tipo_responsavel=resp.tipo_responsavel,
        data_nascimento=None,
        data_atualizacao=getattr(resp, "data_atualizacao_tabela", None),
        nome_mae=None,
        ddd_celular=resp.ddd_celular,
        numero_celular=resp.numero_celular,
        codigo_aluno=str(codigo_aluno),
    )


def obter_dados_responsavel_filiacao(
    codigo_aluno: int,
) -> InformacoesAlunoDTO | None:
    """Retorna dados de filiação do aluno.

    Args:
        codigo_aluno: Código EOL do aluno.

    Returns:
        Informações cadastrais do aluno, ou ``None`` quando não existir.
    """
    return obter_informacoes_aluno(codigo_aluno=codigo_aluno)


def _consolidacao_por_turma(
    ano_letivo: int, ue_codigo: str
) -> list[ConsolidacaoMatriculaDTO]:
    """Conta matrículas válidas por turma.

    Args:
        ano_letivo: Ano letivo usado no filtro.
        ue_codigo: Código EOL da UE.

    Returns:
        Consolidação de matrículas por turma.
    """
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
    """Consolida matrículas válidas do ano atual por turma.

    Args:
        ano_letivo: Ano letivo usado no filtro.
        ue_codigo: Código EOL da UE.

    Returns:
        Consolidação de matrículas por turma.
    """
    return _consolidacao_por_turma(ano_letivo=ano_letivo, ue_codigo=ue_codigo)


def obter_matriculas_anos_anteriores(
    ano_letivo: int, ue_codigo: str
) -> list[ConsolidacaoMatriculaDTO]:
    """Consolida matrículas válidas de ano anterior por turma.

    Args:
        ano_letivo: Ano letivo usado no filtro.
        ue_codigo: Código EOL da UE.

    Returns:
        Consolidação de matrículas por turma.
    """
    return _consolidacao_por_turma(ano_letivo=ano_letivo, ue_codigo=ue_codigo)


def obter_quantidade_alunos_por_turma_da_escola(
    codigo_escola: str,
) -> list[ConsolidacaoMatriculaDTO]:
    """Lista total de matrículas por turma da escola.

    Args:
        codigo_escola: Código EOL da escola.

    Returns:
        Consolidação de matrículas por turma no último ano disponível.
    """
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
    """Retorna total de matrículas por turno da UE.

    Args:
        ue_codigo: Código EOL da UE.
    """
    _ = ue_codigo
    return []


def obter_total_matriculas_por_turno_dre(dre_codigo: str) -> list[Any]:
    """Retorna total de matrículas por turno da DRE.

    Args:
        dre_codigo: Código EOL da DRE.
    """
    _ = dre_codigo
    return []


def obter_matriculas_aluno_na_escola(
    codigo_escola: str, codigo_aluno: int
) -> list[MatriculaEscolaAlunoDTO]:
    """Lista matrículas do aluno em uma escola.

    Args:
        codigo_escola: Código EOL da escola.
        codigo_aluno: Código EOL do aluno.

    Returns:
        Matrículas do aluno na escola informada.
    """
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
    """Transforma DTO em dicionário.

    Args:
        dto: DTO a ser convertido.

    Returns:
        Dicionário do DTO, ou dicionário vazio para valor ``None``.
    """
    return asdict(dto) if dto is not None else {}


def _exec_json_agg(sql: str, params: dict[str, Any]) -> bytes:
    """Executa consulta SQL com retorno JSON_AGG.

    Args:
        sql: Consulta SQL parametrizada.
        params: Parâmetros enviados para a consulta.

    Returns:
        Conteúdo JSON serializado em bytes.
    """
    with connection.cursor() as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
    if not row or row[0] is None:
        return b"[]"
    if isinstance(row[0], bytes):
        return row[0]
    return str(row[0]).encode("utf-8")


def _dump_json_camel(payload: list[dict[str, Any]]) -> bytes:
    """Codifica payload Python em bytes JSON.

    Args:
        payload: Lista de dicionários a serializar.

    Returns:
        JSON em bytes sem caracteres ASCII escapados.
    """
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
    """Lista quantidade de matriculados por ano e componente curricular.

    Args:
        ano_letivo: Ano letivo usado no filtro.
        ue_id: Código EOL da UE usado como filtro opcional.
        componentes_curriculares: Mantido por compatibilidade; sem efeito.
        dre_id: Mantido por compatibilidade; sem efeito atual.

    Returns:
        Payload JSON serializado em bytes.
    """
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
    """Lista quantidade de matriculados por turma e UE em JSON.

    Args:
        ano_letivo: Ano letivo usado no filtro.
        ue_codigo: Código EOL da UE usado como filtro opcional.
        dre_codigo: Mantido por compatibilidade; sem efeito atual.
        modalidade: Mantido por compatibilidade; sem efeito atual.
        ano: Mantido por compatibilidade; sem efeito atual.
        turma: Mantido por compatibilidade; sem efeito atual.

    Returns:
        Payload JSON serializado em bytes.
    """
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
    """Lista dados de acompanhamento escolar em JSON.

    Args:
        codigo_ue: Código EOL da UE usado como filtro opcional.
        ano_letivo: Ano letivo usado como filtro opcional.
        turma_codigo: Código da turma usado como filtro opcional.
        codigo_aluno: Código EOL do aluno usado como filtro opcional.
        cpf_responsavel: CPF do responsável usado como filtro opcional.
        codigo_dre: Mantido por compatibilidade; sem efeito atual.
        modalidade: Mantido por compatibilidade; sem efeito atual.
        semestre: Mantido por compatibilidade; sem efeito atual.

    Returns:
        Payload JSON serializado em bytes.
    """
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
    """Lista responsáveis vigentes agrupados por UE e turma em JSON.

    Args:
        codigo_ue: Código EOL da UE usado como filtro opcional.
        ano_letivo: Ano letivo usado como filtro opcional.
        codigo_dre: Mantido por compatibilidade; sem efeito atual.

    Returns:
        Payload JSON serializado em bytes.
    """
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
    "AlunoAtivoDataAulaDTO",
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
    "obter_alunos_ativos_turma_por_data_aula",
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
