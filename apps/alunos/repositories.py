"""Acesso a dados otimizado do domínio Alunos."""

from collections.abc import Sequence
from typing import Any

from django.db import connection
from django.db.models import Count, F
from django.utils import timezone

from apps.alunos.enums import SITUACOES_MATRICULA_VALIDAS
from apps.alunos.models import (
    Aluno,
    Matricula,
    MatriculaTurma,
    ResponsavelAluno,
    ResponsavelAlunoTurma,
)
from apps.alunos.queries import (
    SQL_A15_QUANTIDADE_POR_ANO_E_CC,
    SQL_A16_QUANTIDADE,
    SQL_A18_ACOMPANHAMENTO,
    SQL_A19_RESPONSAVEIS,
)


def _exec_query_rows(sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    """Executa consulta SQL e devolve cada linha como dicionário."""
    with connection.cursor() as cur:
        cur.execute(sql, params)
        columns = [col[0] for col in cur.description]
        return [dict(zip(columns, row, strict=True)) for row in cur.fetchall()]


def _usa_sql_postgresql() -> bool:
    """Indica se a conexão atual aceita as queries otimizadas de Postgres."""
    return connection.vendor == "postgresql"


def alunos_indexados(
    codigos_alunos: Sequence[int],
) -> dict[int, dict[str, Any]]:
    """Indexa dados básicos dos alunos por código EOL."""
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


def matriculas_por_codigos_turma(
    codigos_turma: Sequence[int],
) -> list[dict[str, Any]]:
    """Consulta matrículas vinculadas a turmas."""
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


def quantidade_matriculados_por_ano_e_cc(
    ano_letivo: int,
    ue_id: str | None = None,
    componentes_curriculares: list[int] | None = None,  # NOSONAR
    dre_id: str | None = None,  # NOSONAR
) -> list[dict[str, Any]]:
    """Lista quantidade de matriculados por ano e componente."""
    if _usa_sql_postgresql():
        return _exec_query_rows(
            SQL_A15_QUANTIDADE_POR_ANO_E_CC,
            {
                "ano": ano_letivo,
                "situacoes": list(SITUACOES_MATRICULA_VALIDAS),
                "ue": ue_id or None,
            },
        )

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
        {
            "codigo_turma": r["codigo_turma"],
            "quantidade": r["quantidade"],
            "ordem": ordem,
        }
        for ordem, r in enumerate(agrupado, start=1)
    ]


def quantidade_matriculados(
    ano_letivo: int,
    ue_codigo: str = "",
    dre_codigo: str = "",  # NOSONAR
    modalidade: list[int] | None = None,  # NOSONAR
    ano: list[int] | None = None,  # NOSONAR
    turma: list[str] | None = None,  # NOSONAR
) -> list[dict[str, Any]]:
    """Lista quantidade de matriculados por turma e UE."""
    if _usa_sql_postgresql():
        return _exec_query_rows(
            SQL_A16_QUANTIDADE,
            {
                "ano": ano_letivo,
                "situacoes": list(SITUACOES_MATRICULA_VALIDAS),
                "ue": ue_codigo or None,
            },
        )

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

    return [
        {
            "quantidade": qtd,
            "ordem": ordem,
            "codigo_turma": codigo_turma,
            "ue_codigo": ue,
        }
        for ordem, ((ue, codigo_turma), qtd) in enumerate(
            sorted(grupos.items()), start=1
        )
    ]


def dados_acompanhamento_escolar(
    codigo_ue: str | None = None,
    ano_letivo: int | None = None,
    turma_codigo: str | None = None,
    codigo_aluno: int | None = None,
    cpf_responsavel: str | None = None,
    codigo_dre: str | None = None,  # NOSONAR
    modalidade: int | None = None,  # NOSONAR
    semestre: int | None = None,  # NOSONAR
) -> list[dict[str, Any]]:
    """Lista dados de acompanhamento escolar."""
    if _usa_sql_postgresql():
        try:
            turma_int = int(turma_codigo) if turma_codigo else None
        except (TypeError, ValueError):
            return []
        return _exec_query_rows(
            SQL_A18_ACOMPANHAMENTO,
            {
                "situacoes": list(SITUACOES_MATRICULA_VALIDAS),
                "codigo_aluno": codigo_aluno,
                "codigo_ue": codigo_ue or None,
                "ano_letivo": ano_letivo,
                "turma_codigo": turma_int,
                "cpf": cpf_responsavel or None,
            },
        )

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
    alunos_idx = alunos_indexados(codigos_alunos)
    responsaveis = {
        r["aluno_id"]: r
        for r in ResponsavelAluno.objects.filter(
            aluno_id__in=codigos_alunos,
            data_fim_vinculo__isnull=True,
        )
        .order_by("aluno_id", "tipo_responsavel")
        .values("aluno_id", "nome", "cpf", "tipo_responsavel")
    }

    saida: list[dict[str, Any]] = []
    for m in matriculas:
        a = alunos_idx.get(m["aluno_id"], {})
        resp = responsaveis.get(m["aluno_id"], {})
        mt = mts.get(m["codigo_matricula"], {})
        saida.append(
            {
                "codigo_eol": m["aluno_id"],
                "nome_responsavel": resp.get("nome"),
                "cpf_responsavel": resp.get("cpf"),
                "nome": a.get("nome", ""),
                "nome_social": a.get("nome_social"),
                "codigo_escola": m["codigo_ue"],
                "tipo_responsavel": resp.get("tipo_responsavel"),
                "codigo_turma": mt.get("codigo_turma") or 0,
                "situacao_matricula": m["situacao_matricula"],
                "data_nascimento": a.get("data_nascimento"),
                "data_situacao_matricula": m["data_situacao_matricula"],
                "ano_letivo": m["ano_letivo"],
            }
        )
    return saida


def responsaveis_dre_ue_turma(
    codigo_ue: str | None = None,
    ano_letivo: int | None = None,
    codigo_dre: str | None = None,
) -> list[dict[str, Any]]:
    """Lista responsáveis vigentes agrupados por UE e turma."""
    ano = (
        ano_letivo
        if ano_letivo and ano_letivo > 0
        else timezone.localdate().year
    )
    if _usa_sql_postgresql():
        return _exec_query_rows(
            SQL_A19_RESPONSAVEIS,
            {
                "codigo_dre": codigo_dre or None,
                "codigo_ue": codigo_ue or None,
                "ano_letivo": ano,
            },
        )

    responsaveis_qs = ResponsavelAlunoTurma.objects.filter(ano_letivo=ano)
    if codigo_dre:
        responsaveis_qs = responsaveis_qs.filter(codigo_dre=codigo_dre)
    if codigo_ue:
        responsaveis_qs = responsaveis_qs.filter(codigo_ue=codigo_ue)

    campos = (
        "codigo_dre",
        "dre",
        "codigo_ue",
        "ue",
        "codigo_turma",
        "turma",
        "cpf_responsavel",
        "codigo_aluno",
        "codigo_tipo_escola",
        "codigo_etapa_ensino",
        "codigo_ciclo_ensino",
        "serie_resumida",
        "codigo_modalidade_turma",
    )
    rows = responsaveis_qs.values(*campos).distinct().order_by(*campos)
    return [{**row, "tem_app_instalado": False} for row in rows]
