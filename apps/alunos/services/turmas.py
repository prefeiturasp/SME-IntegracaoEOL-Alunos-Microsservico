"""Services de turmas e vínculos de alunos."""

from collections.abc import Sequence
from datetime import date
from typing import Any, cast

from django.db.models import F
from django.utils import timezone

from apps.alunos.enums import (
    SITUACOES_MATRICULA_VALIDAS,
    SituacaoMatricula,
)
from apps.alunos.models import (
    Aluno,
    Matricula,
    MatriculaTurma,
    ResponsavelAluno,
)
from apps.alunos.repositories import (
    alunos_indexados,
)
from apps.alunos.services.responsaveis import responsaveis_do_aluno


def _turmas_mais_recentes_por_matricula(
    codigos_matricula: Sequence[int],
    historico: bool = False,
) -> dict[int, list[dict[str, Any]]]:
    """Agrupa os vínculos de turma por matrícula."""
    if not codigos_matricula:
        return {}

    saida: dict[int, list[dict[str, Any]]] = {}
    turmas_processadas: set[tuple[int, int]] = set()
    for mt in (
        MatriculaTurma.objects.filter(
            codigo_matricula__in=codigos_matricula,
            origem_atual=not historico,
        )
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
            "-data_atualizacao_tabela",
            "-data_situacao_aluno_data_hora",
            "-data_situacao_aluno",
            "-sequencia",
        )
    ):
        if not historico:
            chave_turma = (mt["codigo_matricula"], mt["codigo_turma"])
            if chave_turma in turmas_processadas:
                continue
            turmas_processadas.add(chave_turma)
        saida.setdefault(mt["codigo_matricula"], []).append(mt)
    return saida


def _todas_turmas_por_matricula(
    codigos_matricula: Sequence[int],
) -> dict[int, list[dict[str, Any]]]:
    """Retorna todas as turmas de cada matrícula."""
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


def _codigo_situacao_turma(
    matricula: dict[str, Any], matricula_turma: dict[str, Any]
) -> int:
    """Resolve o código de situação usado."""
    return cast(
        int,
        matricula_turma.get("codigo_situacao_aluno")
        or matricula["codigo_situacao_matricula"],
    )


def _qs_matriculas(
    codigo_aluno: int,
    ano_letivo: int | None,
    historico: bool,
) -> Any:
    """Monta queryset base de matrículas do aluno."""
    qs = Matricula.objects.filter(aluno_id=codigo_aluno)
    if ano_letivo is not None:
        qs = qs.filter(ano_letivo=ano_letivo)
    if historico:
        qs = qs.filter(origem_historica=True)
    else:
        qs = qs.filter(origem_atual=True)
        if ano_letivo is None:
            qs = qs.filter(ano_letivo=timezone.now().year)
    return qs


def _matriculas_do_aluno(
    codigo_aluno: int,
    ano_letivo: int | None,
    historico: bool,
) -> list[dict[str, Any]]:
    """Lista matrículas do aluno conforme os filtros informados."""
    return list(
        _qs_matriculas(codigo_aluno, ano_letivo, historico)
        .values(
            "codigo_matricula",
            "aluno_id",
            "codigo_ue",
            "ano_letivo",
            "codigo_situacao_matricula",
            "situacao_matricula",
            "data_situacao_matricula",
            "data_situacao_matricula_data_hora",
            "data_situacao_matricula_historica",
        )
        .order_by("-ano_letivo", "codigo_situacao_matricula")
    )


def _aluno_basico(codigo_aluno: int) -> dict[str, Any]:
    """Retorna dados básicos do aluno."""
    return (
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


def _responsavel_prioritario_do_aluno(codigo_aluno: int) -> dict[str, Any]:
    """Retorna o responsável prioritário do aluno."""
    return (
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


def _turma_do_aluno_deve_ser_incluida(
    codigo_situacao: int,
    matricula_turma: dict[str, Any],
    filtrar_situacao: bool,
    tipo_turma: bool,
) -> bool:
    """Verifica se a turma atende aos filtros informados."""
    if filtrar_situacao and codigo_situacao not in SITUACOES_MATRICULA_VALIDAS:
        return False
    return not (tipo_turma and matricula_turma.get("codigo_tipo_turma") == 3)


def _linhas_turmas_do_aluno(
    matriculas: list[dict[str, Any]],
    turmas_por_matricula: dict[int, list[dict[str, Any]]],
    aluno: dict[str, Any],
    responsaveis: list[dict[str, Any]],
    filtrar_situacao: bool,
    tipo_turma: bool,
    historico: bool = False,
) -> list[dict[str, Any]]:
    """Agrupa as linhas de turma do aluno conforme os filtros informados."""
    saida: list[dict[str, Any]] = []
    for matricula in matriculas:
        turmas = turmas_por_matricula.get(matricula["codigo_matricula"], [])
        for matricula_turma in turmas:
            codigo_situacao = _codigo_situacao_turma(
                matricula, matricula_turma
            )
            if not _turma_do_aluno_deve_ser_incluida(
                codigo_situacao,
                matricula_turma,
                filtrar_situacao,
                tipo_turma,
            ):
                continue
            for responsavel in responsaveis:
                saida.append(
                    {
                        "matricula": matricula,
                        "matricula_turma": matricula_turma,
                        "aluno": aluno,
                        "responsavel": responsavel,
                        "codigo_situacao": codigo_situacao,
                        "historico": historico,
                    }
                )
    return saida


def _consultar_turmas_do_aluno(
    codigo_aluno: int,
    ano_letivo: int | None = None,
    historico: bool = False,
    filtrar_situacao: bool = True,
    tipo_turma: bool = True,
) -> list[dict[str, Any]]:
    """Consulta turmas e matrículas do aluno."""
    matriculas = _matriculas_do_aluno(codigo_aluno, ano_letivo, historico)
    if not matriculas:
        return []

    aluno = _aluno_basico(codigo_aluno)
    responsavel = _responsavel_prioritario_do_aluno(codigo_aluno)
    responsaveis = responsaveis_do_aluno(codigo_aluno) or [responsavel]
    turmas_por_matricula = _turmas_mais_recentes_por_matricula(
        [m["codigo_matricula"] for m in matriculas],
        historico=historico,
    )
    return _linhas_turmas_do_aluno(
        matriculas,
        turmas_por_matricula,
        aluno,
        responsaveis,
        filtrar_situacao,
        tipo_turma,
        historico,
    )


def buscar_turmas_do_aluno(
    codigo_aluno: int,
    tipo_turma: bool = True,
    filtrar_situacao: bool = True,
) -> list[dict[str, Any]]:
    """Lista as turmas do aluno no ano corrente."""
    return _consultar_turmas_do_aluno(
        codigo_aluno=codigo_aluno,
        tipo_turma=tipo_turma,
        filtrar_situacao=filtrar_situacao,
    )


def buscar_turmas_do_aluno_por_situacao_matricula(
    codigo_aluno: int,
    ano_letivo: int | None,
    filtrar_situacao_matricula: bool = True,
    tipo_turma: bool = False,
) -> list[dict[str, Any]]:
    """Busca turmas filtradas por situação de matrícula."""
    eh_historico = bool(
        ano_letivo and ano_letivo > 0 and ano_letivo != timezone.now().year
    )
    return _consultar_turmas_do_aluno(
        codigo_aluno=codigo_aluno,
        ano_letivo=ano_letivo,
        historico=eh_historico,
        filtrar_situacao=filtrar_situacao_matricula,
        tipo_turma=tipo_turma,
    )


def _situacao_ativa_na_data(
    codigo_situacao: int,
    data_situacao: date | None,
    limite: date,
) -> bool:
    """Aplica o filtro ativa/inativa vs. data de referência."""
    if data_situacao is None:
        return False
    ativa = codigo_situacao in SITUACOES_MATRICULA_VALIDAS
    if ativa:
        return data_situacao <= limite
    return data_situacao > limite


def _codigos_turmas_regulares_por_origem(
    matriculas_idx: dict[int, dict[str, Any]],
    ano_letivo: int,
    historico: bool,
    limite: date,
) -> list[dict[str, Any]]:
    """Resolve as turmas válidas do aluno para um ramo."""
    if not matriculas_idx:
        return []

    linhas: list[dict[str, Any]] = []
    processadas: set[tuple[int, int]] = set()
    for mt in (
        MatriculaTurma.objects.filter(
            codigo_matricula__in=list(matriculas_idx),
            ano_letivo_turma=ano_letivo,
            origem_atual=not historico,
        )
        .values(
            "codigo_matricula",
            "codigo_turma",
            "data_situacao_aluno",
            "data_situacao_aluno_data_hora",
            "codigo_situacao_aluno",
        )
        .order_by(
            "codigo_matricula",
            "codigo_turma",
            F("data_situacao_aluno").desc(nulls_last=True),
            F("data_situacao_aluno_data_hora").desc(nulls_last=True),
            "-sequencia",
        )
    ):
        chave = (mt["codigo_matricula"], mt["codigo_turma"])
        if chave in processadas:
            continue
        processadas.add(chave)
        codigo_situacao = mt.get("codigo_situacao_aluno")
        if codigo_situacao is None:
            continue
        if codigo_situacao == SituacaoMatricula.VINCULO_INDEVIDO:
            continue
        data_situacao = mt.get("data_situacao_aluno")
        if not _situacao_ativa_na_data(codigo_situacao, data_situacao, limite):
            continue
        linhas.append(
            {
                "codigo_matricula": mt["codigo_matricula"],
                "codigo_turma": mt["codigo_turma"],
                "data_situacao": data_situacao,
            }
        )
    return linhas


def obter_codigos_turmas_regulares_aluno(
    codigo_aluno: int,
    ano_letivo: int,
    data_referencia: date | None = None,
) -> list[int]:
    """Lista códigos de turma do aluno no ano letivo."""
    limite = data_referencia or timezone.now().date()
    linhas: list[dict[str, Any]] = []
    for historico in (False, True):
        if historico:
            matriculas_idx: dict[int, dict[str, Any]] = {
                codigo: {"codigo_matricula": codigo}
                for codigo in Matricula.objects.filter(
                    aluno_id=codigo_aluno,
                    ano_letivo=ano_letivo,
                    origem_historica=True,
                ).values_list("codigo_matricula", flat=True)
            }
        else:
            matriculas_idx = {
                m["codigo_matricula"]: m
                for m in _matriculas_do_aluno(
                    codigo_aluno, ano_letivo, historico
                )
            }
        if not matriculas_idx:
            continue
        linhas.extend(
            _codigos_turmas_regulares_por_origem(
                matriculas_idx, ano_letivo, historico, limite
            )
        )

    linhas.sort(key=lambda linha: linha["data_situacao"], reverse=True)
    saida: list[int] = []
    vistos: set[int] = set()
    for linha in linhas:
        codigo_turma = linha["codigo_turma"]
        if codigo_turma in vistos:
            continue
        vistos.add(codigo_turma)
        saida.append(codigo_turma)
    return saida


def buscar_turmas_do_aluno_com_historico(
    codigo_aluno: int,
    ano_letivo: int | None,
    historico: bool,
    filtrar_situacao: bool = True,
    tipo_turma: bool = True,
) -> list[dict[str, Any]]:
    """Busca turmas do aluno com a origem histórica explícita."""
    dados = _consultar_turmas_do_aluno(
        codigo_aluno=codigo_aluno,
        ano_letivo=ano_letivo,
        historico=historico,
        filtrar_situacao=filtrar_situacao,
        tipo_turma=tipo_turma,
    )
    if not dados and not historico:
        dados = _consultar_turmas_do_aluno(
            codigo_aluno=codigo_aluno,
            ano_letivo=ano_letivo,
            historico=True,
            filtrar_situacao=filtrar_situacao,
            tipo_turma=tipo_turma,
        )
    return dados


def _matriculas_turma_da_ue(
    codigo_ue: str,
    ano_letivo: int,
) -> list[dict[str, Any]]:
    """Lista vínculos de matrícula-turma da UE."""
    return list(
        MatriculaTurma.objects.filter(
            codigo_ue_turma=codigo_ue,
            ano_letivo_turma=ano_letivo,
            origem_atual=True,
        )
        .values(
            "codigo_matricula",
            "codigo_turma",
            "numero_chamada",
            "data_situacao_aluno",
            "data_situacao_aluno_data_hora",
            "codigo_situacao_aluno",
            "codigo_tipo_turma",
            "tipo_turno",
            "nome_turma",
            "codigo_etapa_ensino",
            "codigo_ciclo_ensino",
            "descricao_etapa_ensino",
            "descricao_ciclo_ensino",
            "ano_letivo_turma",
        )
        .order_by("codigo_turma", "codigo_matricula", "sequencia")
    )


def _matriculas_idx_da_ue(
    matriculas_turma: list[dict[str, Any]],
    codigo_eol_filtro: str,
) -> dict[int, dict[str, Any]]:
    """Indexa matrículas da UE pelo código da matrícula."""
    matriculas = list(
        Matricula.objects.filter(
            codigo_matricula__in=[
                mt["codigo_matricula"] for mt in matriculas_turma
            ],
            origem_atual=True,
        ).values("codigo_matricula", "aluno_id")
    )
    if codigo_eol_filtro:
        matriculas = [
            m for m in matriculas if codigo_eol_filtro in str(m["aluno_id"])
        ]
    return {m["codigo_matricula"]: m for m in matriculas}


def _filtrar_matriculas_idx_por_nome(
    matriculas_idx: dict[int, dict[str, Any]],
    alunos_idx: dict[int, dict[str, Any]],
    nome_filtro: str,
) -> dict[int, dict[str, Any]]:
    """Filtra matrículas pelos nomes dos alunos."""
    if not nome_filtro:
        return matriculas_idx
    codigos_alunos = {
        codigo_aluno
        for codigo_aluno, aluno in alunos_idx.items()
        if nome_filtro in (aluno.get("nome") or "").lower()
    }
    return {
        codigo_matricula: matricula
        for codigo_matricula, matricula in matriculas_idx.items()
        if matricula["aluno_id"] in codigos_alunos
    }


def _linhas_alunos_da_ue(
    matriculas_turma: list[dict[str, Any]],
    matriculas_idx: dict[int, dict[str, Any]],
    alunos_idx: dict[int, dict[str, Any]],
    ano_letivo: int,
) -> list[dict[str, Any]]:
    """Agrupa alunos vinculados à UE."""
    saida: list[dict[str, Any]] = []
    for matricula_turma in matriculas_turma:
        matricula = matriculas_idx.get(matricula_turma["codigo_matricula"])
        if matricula is None:
            continue
        aluno = alunos_idx.get(matricula["aluno_id"], {})
        saida.append(
            {
                "matricula": matricula,
                "matricula_turma": matricula_turma,
                "aluno": aluno,
                "ano_letivo": ano_letivo,
            }
        )
    return saida


def buscar_alunos_da_ue(
    codigo_ue: str,
    ano_letivo: int,
    nome_aluno: str | None = None,
    codigo_eol: str | None = None,
) -> list[dict[str, Any]]:
    """Lista alunos vinculados a turmas da UE no ano letivo."""
    codigo_eol_filtro = codigo_eol.strip() if codigo_eol else ""
    nome_filtro = nome_aluno.strip().lower() if nome_aluno else ""

    matriculas_turma = _matriculas_turma_da_ue(codigo_ue, ano_letivo)
    if not matriculas_turma:
        return []

    matriculas_idx = _matriculas_idx_da_ue(matriculas_turma, codigo_eol_filtro)
    if not matriculas_idx:
        return []
    codigos_alunos = {m["aluno_id"] for m in matriculas_idx.values()}
    alunos_idx = alunos_indexados(list(codigos_alunos))

    matriculas_idx = _filtrar_matriculas_idx_por_nome(
        matriculas_idx, alunos_idx, nome_filtro
    )
    if not matriculas_idx:
        return []
    return _linhas_alunos_da_ue(
        matriculas_turma, matriculas_idx, alunos_idx, ano_letivo
    )


def obter_alunos_por_codigos_e_ano(
    codigos_aluno: Sequence[int], ano_letivo: int
) -> list[dict[str, Any]]:
    """Lista turmas dos alunos informados por ano letivo."""
    if not codigos_aluno:
        return []
    eh_historico = ano_letivo < timezone.now().year
    saida: list[dict[str, Any]] = []
    for codigo in codigos_aluno:
        saida.extend(
            _consultar_turmas_do_aluno(
                codigo_aluno=codigo,
                ano_letivo=ano_letivo,
                historico=eh_historico,
                filtrar_situacao=False,
                tipo_turma=False,
            )
        )
    return saida


def _turmas_atuais_por_aluno(codigo_aluno: int) -> list[dict[str, Any]]:
    """Retorna turmas atuais do aluno."""
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

    aluno = _aluno_basico(codigo_aluno)
    responsaveis = responsaveis_do_aluno(codigo_aluno) or [{}]
    mts_all = _todas_turmas_por_matricula(
        [m["codigo_matricula"] for m in matriculas]
    )

    saida: list[dict[str, Any]] = []
    for m in matriculas:
        turmas = mts_all.get(m["codigo_matricula"]) or [{}]
        for mt in turmas:
            codigo_situacao = _codigo_situacao_turma(m, mt)
            for responsavel in responsaveis:
                saida.append(
                    {
                        "matricula": m,
                        "matricula_turma": mt,
                        "aluno": aluno,
                        "responsavel": responsavel,
                        "codigo_situacao": codigo_situacao,
                        "historico": False,
                    }
                )
    return saida


def obter_alunos_por_codigos(
    codigos_aluno: Sequence[int],
) -> list[dict[str, Any]]:
    """Lista turmas atuais dos alunos informados."""
    if not codigos_aluno:
        return []
    saida: list[dict[str, Any]] = []
    for codigo in codigos_aluno:
        saida.extend(_turmas_atuais_por_aluno(codigo))
    return saida
