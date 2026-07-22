"""Services do domínio Alunos."""

import json
from collections.abc import Iterator, Sequence
from datetime import date, datetime
from typing import Any, cast

from django.db import connection
from django.db.models import Count, F, Max, Min, Q
from django.utils import timezone

from apps.alunos.enums import (
    SITUACOES_MATRICULA_ATIVAS_TURMA,
    SITUACOES_MATRICULA_VALIDAS,
    SituacaoMatricula,
)
from apps.alunos.models import (
    Aluno,
    DadosAlunoAcompanhamentoEscolar,
    Matricula,
    MatriculaAnoAnterior,
    MatriculaAnoLetivo,
    MatriculaComponenteCurricularAnoLetivo,
    MatriculaTurma,
    NecessidadeEspecialAluno,
    ResponsavelAluno,
    ResponsavelAlunoTurma,
    TipoNecessidadeEspecial,
)
from apps.alunos.queries import (
    SQL_A15_QUANTIDADE_POR_ANO_E_CC,
    SQL_A16_QUANTIDADE,
    SQL_A18_ACOMPANHAMENTO,
    SQL_A19_RESPONSAVEIS,
)
from apps.core.utils import fim_do_dia, numero_chamada_int

SITUACOES_MATRICULA_TURMA_ATIVAS = (1, 6, 10, 13)

# Data de referência usada quando a fonte histórica não projeta o campo.
_DATA_DEFAULT_LEGADO = datetime(1, 1, 1)
_DATA_PADRAO_LEGADO = "0001-01-01T00:00:00"
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


_MODALIDADE_POR_ETAPA = {
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
            "tipo_turno",
            "data_atualizacao_tabela",
            "nome_turma",
            "codigo_etapa_ensino",
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


def _turmas_mais_recentes_por_matricula(
    codigos_matricula: Sequence[int],
    historico: bool = False,
) -> dict[int, list[dict[str, Any]]]:
    """Agrupa os vínculos de turma por matrícula.

    No ramo corrente mantém apenas o estado mais recente de cada turma;
    no histórico devolve todos os vínculos (a jornada completa), como a
    consulta histórica do legado.

    Args:
        codigos_matricula: Códigos de matrícula consultados.
        historico: Usa os vínculos históricos quando ``True``; caso contrário,
            apenas os vínculos correntes.

    Returns:
        Vínculos de turma agrupados por código de matrícula.
    """
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


def _dados_acompanhamento_por_aluno_turma(
    pares_aluno_turma: Sequence[tuple[int, int]],
) -> dict[tuple[int, int], dict[str, Any]]:
    """Indexa os dados de acompanhamento por aluno e turma.

    Args:
        pares_aluno_turma: Pares de aluno e turma usados na consulta.

    Returns:
        Dados de acompanhamento indexados por aluno e turma.
    """
    chaves = set(pares_aluno_turma)
    if not chaves:
        return {}
    codigos_alunos = {codigo_aluno for codigo_aluno, _ in chaves}
    saida: dict[tuple[int, int], dict[str, Any]] = {}
    for dado in (
        DadosAlunoAcompanhamentoEscolar.objects.filter(
            codigo_aluno__in=codigos_alunos
        )
        .values(
            "codigo_aluno",
            "codigo_turma",
            "codigo_ciclo_ensino",
            "descricao_etapa_ensino",
            "descricao_ciclo_ensino",
        )
        .order_by("codigo_aluno", "codigo_turma", "tipo_responsavel")
    ):
        chave = (dado["codigo_aluno"], dado["codigo_turma"])
        if chave in chaves:
            saida.setdefault(chave, dado)
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
) -> Any:
    """Monta queryset base de matrículas do aluno.

    No ramo histórico o filtro usa ``origem_historica`` (presença na view
    histórica do EOL), pois uma matrícula pode existir nas duas fontes e
    ``origem_atual`` guarda apenas a origem vencedora.

    Args:
        codigo_aluno: Código EOL do aluno.
        ano_letivo: Ano letivo filtrado, ou ``None`` para todos.
        historico: Indica se a consulta é do ramo histórico.

    Returns:
        QuerySet de matrículas com os filtros aplicados.
    """
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


def _montar_turma_do_aluno(
    matricula: dict[str, Any],
    matricula_turma: dict[str, Any],
    aluno: dict[str, Any],
    responsavel: dict[str, Any],
    codigo_situacao: int,
    historico: bool = False,
) -> dict[str, Any]:
    """Monta dados de turma do aluno.

    No ramo histórico replica os campos que a consulta histórica do legado
    não projeta: CPF nulo, ``dataAtualizacaoTabela`` no default do C#
    (0001-01-01) e a data de matrícula vinda da fonte histórica.
    """
    data_situacao = (
        matricula_turma.get("data_situacao_aluno_data_hora")
        or matricula_turma.get("data_situacao_aluno")
        or matricula.get("data_situacao_matricula_data_hora")
        or matricula["data_situacao_matricula"]
    )
    return {
        "codigo_aluno": matricula["aluno_id"],
        "ano_letivo": matricula["ano_letivo"],
        "nome_aluno": aluno.get("nome", ""),
        "nome_social_aluno": aluno.get("nome_social"),
        "codigo_situacao_matricula": codigo_situacao,
        "situacao_matricula": SituacaoMatricula.get_descricao(codigo_situacao),
        "data_situacao": data_situacao,
        "data_nascimento": aluno.get("data_nascimento"),
        "documento_cpf": None if historico else aluno.get("cpf"),
        "data_matricula": (
            (
                matricula.get("data_situacao_matricula_historica")
                or matricula.get("data_situacao_matricula_data_hora")
                or matricula["data_situacao_matricula"]
            )
            if historico
            else (
                matricula.get("data_situacao_matricula_data_hora")
                or matricula["data_situacao_matricula"]
            )
        ),
        "numero_aluno_chamada": matricula_turma.get("numero_chamada"),
        "codigo_turma": matricula_turma.get("codigo_turma") or 0,
        "data_atualizacao_contato": responsavel.get("data_atualizacao_tabela"),
        "nome_responsavel": responsavel.get("nome"),
        "tipo_responsavel": responsavel.get("tipo_responsavel"),
        "ddd_celular": responsavel.get("ddd_celular"),
        "numero_celular": responsavel.get("numero_celular"),
        "codigo_escola": matricula["codigo_ue"],
        "codigo_tipo_turma": matricula_turma.get("codigo_tipo_turma"),
        "data_atualizacao_tabela": (
            _DATA_DEFAULT_LEGADO
            if historico
            else (
                matricula_turma.get("data_atualizacao_tabela") or data_situacao
            )
        ),
    }


def _montar_turmas_do_aluno(
    matriculas: list[dict[str, Any]],
    turmas_por_matricula: dict[int, list[dict[str, Any]]],
    aluno: dict[str, Any],
    responsaveis: list[dict[str, Any]],
    filtrar_situacao: bool,
    tipo_turma: bool,
    historico: bool = False,
) -> list[dict[str, Any]]:
    """Monta as turmas do aluno conforme os filtros informados."""
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
                    _montar_turma_do_aluno(
                        matricula,
                        matricula_turma,
                        aluno,
                        responsavel,
                        codigo_situacao,
                        historico,
                    )
                )
    return saida


def _consultar_turmas_do_aluno(
    codigo_aluno: int,
    ano_letivo: int | None = None,
    historico: bool = False,
    filtrar_situacao: bool = True,
    tipo_turma: bool = True,
) -> list[dict[str, Any]]:
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
    matriculas = _matriculas_do_aluno(codigo_aluno, ano_letivo, historico)
    if not matriculas:
        return []

    aluno = _aluno_basico(codigo_aluno)
    responsavel = _responsavel_prioritario_do_aluno(codigo_aluno)
    responsaveis = _responsaveis_do_aluno(codigo_aluno) or [responsavel]
    turmas_por_matricula = _turmas_mais_recentes_por_matricula(
        [m["codigo_matricula"] for m in matriculas],
        historico=historico,
    )
    return _montar_turmas_do_aluno(
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
    tipo_turma: bool = False,
) -> list[dict[str, Any]]:
    """Busca turmas filtradas por situação de matrícula.

    Args:
        codigo_aluno: Código EOL do aluno.
        ano_letivo: Ano letivo usado no filtro.
        filtrar_situacao_matricula: Indica se aplica filtro de situação.
        tipo_turma: Exclui turmas do tipo programa quando verdadeiro.

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
        tipo_turma=tipo_turma,
    )


def _situacao_ativa_na_data(
    codigo_situacao: int,
    data_situacao: date | None,
    limite: date,
) -> bool:
    """Aplica o filtro ativa/inativa vs. data de referência.

    Uma situação "ativa" (em ``SITUACOES_MATRICULA_VALIDAS``) só vale se a
    data da situação for anterior ou igual ao limite; uma situação
    "inativa" (fora do conjunto) só vale se a data for posterior ao
    limite — ou seja, o aluno ainda estava vinculado na data de referência.

    Args:
        codigo_situacao: Código da situação resolvida do vínculo.
        data_situacao: Data da situação do aluno na turma.
        limite: Data de referência (``dataReferencia`` ou hoje).

    Returns:
        ``True`` quando o vínculo deve ser considerado na data informada.
    """
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
    """Resolve as turmas válidas do aluno para um ramo (corrente/histórico).

    Agrupa por ``(codigo_matricula, codigo_turma)``, mantém a situação mais
    recente, exclui Vínculo Indevido e aplica o filtro ativa/inativa vs.
    data.

    Args:
        matriculas_idx: Matrículas do aluno indexadas por código, já
            filtradas pelo ramo (``origem_atual``) e ano letivo.
        ano_letivo: Ano letivo consultado (filtra a turma).
        historico: Usa os vínculos históricos quando ``True``.
        limite: Data de referência do filtro de situação.

    Returns:
        Linhas ``{codigo_matricula, codigo_turma, data_situacao}`` do ramo.
    """
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
        # Usa a situação do próprio vínculo turma, sem cair para a situação
        # da matrícula — não usar _codigo_situacao_turma.
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
    """Lista códigos de turma do aluno no ano letivo (recorte de matrícula).

    Resolve a parte do domínio Alunos: apura a
    última situação por matrícula+turma nos vínculos correntes e
    históricos, exclui Vínculo Indevido, aplica o filtro ativa/inativa vs.
    data de referência e ordena por data da situação (mais recente
    primeiro). **Não** filtra por tipo de turma / UE / semestre — esse
    recorte pertence ao domínio Pedagógico, e a interseção é feita no
    gateway.

    Args:
        codigo_aluno: Código EOL do aluno.
        ano_letivo: Ano letivo consultado.
        data_referencia: Data de referência do filtro de situação; usa a
            data de hoje quando ``None``.

    Returns:
        Códigos de turma, sem duplicidade, ordenados por data da situação
        decrescente.
    """
    limite = data_referencia or timezone.now().date()
    linhas: list[dict[str, Any]] = []
    for historico in (False, True):
        if historico:
            # Vínculos históricos só contam para matrículas presentes na
            # fonte histórica — inclusive as que também existem na fonte
            # atual e, por isso, têm origem_atual=True.
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
    """Busca turmas do aluno com a origem histórica explícita.

    Como no legado, o chamador escolhe a fonte (corrente ou histórica) e,
    quando a corrente não retorna turmas, a busca é repetida na histórica.

    Args:
        codigo_aluno: Código EOL do aluno.
        ano_letivo: Ano letivo usado no filtro; ``None`` não filtra.
        historico: Consulta os vínculos históricos quando ``True``.
        filtrar_situacao: Restringe às situações de matrícula válidas.
        tipo_turma: Exclui turmas do tipo programa (tipo 3) quando ``True``.

    Returns:
        Turmas do aluno conforme a origem e os filtros informados.
    """
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


def _montar_aluno_da_ue(
    matricula: dict[str, Any],
    matricula_turma: dict[str, Any],
    aluno: dict[str, Any],
    ano_letivo: int,
) -> dict[str, Any]:
    """Monta dados de aluno vinculado a uma UE."""
    codigo_situacao = matricula_turma.get("codigo_situacao_aluno")
    return {
        "codigo_aluno": matricula["aluno_id"],
        "tipo_turno": matricula_turma.get("tipo_turno"),
        "ano_letivo": matricula_turma.get("ano_letivo_turma") or ano_letivo,
        "nome_aluno": aluno.get("nome", ""),
        "nome_social_aluno": aluno.get("nome_social"),
        "codigo_situacao_matricula": codigo_situacao or 0,
        "situacao_matricula": SituacaoMatricula.get_descricao(codigo_situacao),
        "data_situacao": (
            matricula_turma.get("data_situacao_aluno_data_hora")
            or matricula_turma.get("data_situacao_aluno")
        ),
        "data_nascimento": aluno.get("data_nascimento"),
        "numero_aluno_chamada": matricula_turma.get("numero_chamada") or "0",
        "codigo_turma": matricula_turma["codigo_turma"],
        "data_atualizacao_contato": _DATA_PADRAO_LEGADO,
        "codigo_tipo_turma": matricula_turma.get("codigo_tipo_turma"),
        "turma_nome": matricula_turma.get("nome_turma"),
        "etapa_ensino": matricula_turma.get("codigo_etapa_ensino"),
        "ciclo_ensino": matricula_turma.get("codigo_ciclo_ensino"),
        "desc_etapa_ensino": matricula_turma.get("descricao_etapa_ensino"),
        "desc_ciclo_ensino": matricula_turma.get("descricao_ciclo_ensino"),
        "data_atualizacao_tabela": _DATA_PADRAO_LEGADO,
    }


def _montar_alunos_da_ue(
    matriculas_turma: list[dict[str, Any]],
    matriculas_idx: dict[int, dict[str, Any]],
    alunos_idx: dict[int, dict[str, Any]],
    ano_letivo: int,
) -> list[dict[str, Any]]:
    """Monta alunos vinculados à UE."""
    saida: list[dict[str, Any]] = []
    for matricula_turma in matriculas_turma:
        matricula = matriculas_idx.get(matricula_turma["codigo_matricula"])
        if matricula is None:
            continue
        aluno = alunos_idx.get(matricula["aluno_id"], {})
        saida.append(
            _montar_aluno_da_ue(matricula, matricula_turma, aluno, ano_letivo)
        )
    return saida


def buscar_alunos_da_ue(
    codigo_ue: str,
    ano_letivo: int,
    nome_aluno: str | None = None,
    codigo_eol: str | None = None,
) -> list[dict[str, Any]]:
    """Lista alunos vinculados a turmas da UE no ano letivo.

    Args:
        codigo_ue: Código EOL da UE.
        ano_letivo: Ano letivo da consulta.
        nome_aluno: Filtro por substring (case-insensitive) do nome.
        codigo_eol: Filtro por substring do código EOL do aluno.

    Returns:
        Alunos com vínculo de turma atual na UE e no ano letivo.
    """
    codigo_eol_filtro = codigo_eol.strip() if codigo_eol else ""
    nome_filtro = nome_aluno.strip().lower() if nome_aluno else ""

    matriculas_turma = _matriculas_turma_da_ue(codigo_ue, ano_letivo)
    if not matriculas_turma:
        return []

    matriculas_idx = _matriculas_idx_da_ue(matriculas_turma, codigo_eol_filtro)
    if not matriculas_idx:
        return []
    codigos_alunos = {m["aluno_id"] for m in matriculas_idx.values()}
    alunos_idx = _alunos_indexados(list(codigos_alunos))

    matriculas_idx = _filtrar_matriculas_idx_por_nome(
        matriculas_idx, alunos_idx, nome_filtro
    )
    if not matriculas_idx:
        return []
    return _montar_alunos_da_ue(
        matriculas_turma, matriculas_idx, alunos_idx, ano_letivo
    )


def _mts_autocomplete_ue(
    codigo_ue: str,
    ano_letivo: int,
    historico: bool,
) -> list[dict[str, Any]]:
    """Lista vínculos de turma regular da UE para o autocomplete.

    Args:
        codigo_ue: Código EOL da UE.
        ano_letivo: Ano letivo, ou ``0`` para não filtrar por ano.
        historico: Usa os vínculos históricos quando ``True``.

    Returns:
        Vínculos de matrícula-turma do ramo consultado.
    """
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
    """Identifica alunos com vínculo corrente de turma-programa nas turmas.

    Args:
        codigo_turmas: Códigos de turma consultados.

    Returns:
        Códigos dos alunos vinculados às turmas em turma não regular.
    """
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
    """Indexa matrículas do autocomplete com dados do aluno.

    Args:
        codigos_matricula: Códigos de matrícula candidatos.
        historico: Usa matrículas históricas quando ``True``.
        nome_aluno: Substring do nome usada como filtro opcional.
        codigo_eol: Código EOL exato usado como filtro opcional.

    Returns:
        Índice por ``codigo_matricula`` com aluno, nome e nome social.
    """
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
    """Aplica o filtro de turmas do autocomplete (turma direta ou programa)."""
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
    """Gera pares turma-matrícula aceitos pelos filtros do autocomplete.

    Args:
        mts: Vínculos de matrícula-turma da UE.
        matriculas_idx: Matrículas indexadas por código.
        codigo_turmas: Restringe pelas turmas informadas.
        alunos_programa: Alunos com turma-programa nas turmas filtradas.

    Yields:
        Par ``(mt, matricula)`` que passou nos filtros de turma.
    """
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
    """Busca alunos para autocomplete da UE/ano.

    Replica o autocomplete do legado: turmas regulares da UE na fonte
    corrente ou histórica, com filtros de nome, código EOL e turmas.
    ``somente_ativos`` é aceito por compatibilidade e ignorado, como no
    legado.

    Args:
        codigo_ue: Código EOL da UE.
        ano_letivo: Ano letivo da consulta; ``0`` não filtra por ano.
        codigo_turmas: Restringe pelas turmas informadas.
        nome_aluno: Filtro por substring do nome (case-insensitive).
        codigo_eol: Filtro pelo código EOL exato.
        somente_ativos: Aceito por compatibilidade; sem efeito no legado.
        eh_historico: Consulta os vínculos históricos quando ``True``.
        limite: Máximo de resultados retornados.

    Returns:
        Alunos compatíveis com os filtros, limitados por ``limite``.
    """
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
                    "codigo_aluno": matricula["aluno_id"],
                    "nome_aluno": matricula["aluno__nome"] or "",
                    "nome_social_aluno": matricula["aluno__nome_social"],
                    "codigo_turma": mt["codigo_turma"],
                    "numero_aluno_chamada": _numero_chamada_autocomplete(
                        mt["numero_chamada"]
                    ),
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
) -> list[dict[str, Any]]:
    """Monta os registros de autocomplete de alunos ativos.

    Args:
        matriculas: Matrículas elegíveis ao retorno.
        mts_idx: Índice de matrícula-turma por ``codigo_matricula``.
        nome_l: Substring do nome em minúsculas, ou vazia para ignorar.
        limite: Máximo de itens retornados.

    Returns:
        Registros de autocomplete ordenados por nome.
    """
    alunos_idx = _alunos_indexados([m["aluno_id"] for m in matriculas])
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
                "codigo_aluno": m["aluno_id"],
                "nome_aluno": nome,
                "nome_social_aluno": a.get("nome_social"),
                "codigo_turma": mt.get("codigo_turma") or 0,
                "numero_aluno_chamada": mt.get("numero_chamada"),
                "turma": mt.get("nome_turma"),
                "modalidade": _MODALIDADE_POR_ETAPA.get(
                    mt.get("codigo_etapa_ensino")
                ),
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


def _chamada_valida(numero_chamada: str | None) -> bool:
    """Indica se o número de chamada do aluno é válido (não nulo nem zero)."""
    return numero_chamada is not None and numero_chamada != "0"


def _ativo_no_periodo_total(
    codigo_situacao: int | None,
    data_matricula: date | None,
    data_situacao: date | None,
    inicio: date | None,
    fim: date | None,
) -> bool:
    """Replica a condição de período do total de ativos do legado.

    Args:
        codigo_situacao: Situação do aluno na matrícula-turma.
        data_matricula: Data de situação da matrícula (DataMatricula).
        data_situacao: Data de situação na matrícula-turma.
        inicio: Início opcional da janela.
        fim: Fim da janela.

    Returns:
        ``True`` se o aluno entra na contagem do período.
    """
    if codigo_situacao == 10:
        return True
    if codigo_situacao in (1, 6, 13, 5):
        return (
            data_matricula is not None
            and fim is not None
            and data_matricula < fim
        )
    if fim is None or data_matricula is None or data_matricula > fim:
        return False
    if data_situacao is None:
        return False
    if inicio is None:
        return data_situacao >= fim
    return data_situacao > fim or (inicio < data_situacao <= fim)


def _ramo_historico_total(
    mt: dict[str, Any],
    matricula: dict[str, Any],
    atuais: set[tuple[int, int]],
) -> bool:
    """Indica se a matrícula-turma histórica entra na contagem."""
    return (
        not mt["origem_atual"]
        and not matricula["origem_atual"]
        and mt["codigo_situacao_aluno"] in (5, 10)
        and _chamada_valida(mt["numero_chamada"])
        and (mt["codigo_matricula"], mt["codigo_turma"]) not in atuais
    )


def _aluno_no_total(
    mt: dict[str, Any],
    matricula: dict[str, Any],
    atuais: set[tuple[int, int]],
    inicio: date | None,
    fim: date | None,
    dre_id: str | None,
) -> int | None:
    """Retorna o aluno se ele entra na contagem do total no período.

    O legado pareia as fontes: o ramo corrente exige matrícula e
    matrícula-turma correntes; o histórico exige ambos históricos.

    Args:
        mt: Vínculo de matrícula-turma.
        matricula: Matrícula correspondente ao vínculo.
        atuais: Pares (matrícula, turma) presentes no ramo corrente.
        inicio: Início opcional da janela.
        fim: Fim da janela.
        dre_id: Restringe à DRE informada.

    Returns:
        Código do aluno a contabilizar, ou ``None``.
    """
    if dre_id and matricula["codigo_dre"] != dre_id:
        return None
    if mt["origem_atual"] and matricula["origem_atual"]:
        ativo = _ativo_no_periodo_total(
            mt["codigo_situacao_aluno"],
            matricula["data_situacao_matricula"],
            _data_simples(mt["data_situacao_aluno"]),
            inicio,
            fim,
        )
        return matricula["aluno_id"] if ativo else None
    if _ramo_historico_total(mt, matricula, atuais):
        return matricula["aluno_id"]
    return None


def obter_total_alunos_ativos_periodo(
    ano_letivo: int,
    data_inicio: datetime | date,
    data_fim: datetime | date,
    ue_id: str | None = None,
    ano_turma: str | None = None,
    dre_id: str | None = None,
    modalidades: list[int] | None = None,
) -> dict[str, Any]:
    """Conta alunos ativos distintos na série e modalidade no período.

    Replica ``ObterTotalAlunosAtivosPorPeriodo`` do legado, filtrando por ano
    letivo, turma regular, série, modalidades, DRE e UE.

    Args:
        ano_letivo: Ano letivo da consulta.
        data_inicio: Início do intervalo de referência.
        data_fim: Fim do intervalo de referência.
        ue_id: Restringe à UE (escola) informada.
        ano_turma: Série resumida (ex.: ``"5"``), equivalente a ``@turmaAno``.
        dre_id: Restringe à DRE informada.
        modalidades: Etapas de ensino aceitas (``cd_etapa_ensino``).

    Returns:
        Registro com a quantidade de alunos ativos distintos.
    """
    fim = _data_simples(data_fim)
    inicio = _data_simples(data_inicio)
    modalidades = modalidades or []

    base = MatriculaTurma.objects.filter(
        ano_letivo_turma=ano_letivo,
        codigo_tipo_turma=1,
        serie_resumida=ano_turma,
        codigo_etapa_ensino__in=modalidades,
    )
    if ue_id:
        base = base.filter(codigo_ue_turma=ue_id)

    mts = list(
        base.values(
            "codigo_matricula",
            "codigo_turma",
            "codigo_situacao_aluno",
            "data_situacao_aluno",
            "numero_chamada",
            "origem_atual",
        )
    )
    if not mts:
        return {"quantidade": 0}

    matriculas_idx = {
        m["codigo_matricula"]: m
        for m in Matricula.objects.filter(
            codigo_matricula__in=[mt["codigo_matricula"] for mt in mts],
        ).values(
            "codigo_matricula",
            "aluno_id",
            "data_situacao_matricula",
            "codigo_dre",
            "origem_atual",
        )
    }
    # Matrícula-turma presentes no ramo corrente (para o NOT EXISTS histórico).
    atuais = {
        (mt["codigo_matricula"], mt["codigo_turma"])
        for mt in mts
        if mt["origem_atual"]
    }

    alunos: set[int] = set()
    for mt in mts:
        matricula = matriculas_idx.get(mt["codigo_matricula"])
        if matricula is None:
            continue
        aluno = _aluno_no_total(mt, matricula, atuais, inicio, fim, dre_id)
        if aluno is not None:
            alunos.add(aluno)

    return {"quantidade": len(alunos)}


def _matriculas_turma_da_turma(
    codigo_turma: int,
) -> list[dict[str, Any]]:
    """Lista vínculos de matrícula da turma."""
    return list(
        MatriculaTurma.objects.filter(codigo_turma=codigo_turma).values(
            "codigo_matricula",
            "codigo_turma",
            "numero_chamada",
            "data_situacao_aluno_data_hora",
            "codigo_situacao_aluno",
            "sequencia",
        )
    )


def _matriculas_idx_por_matriculas_turma(
    matriculas_turma: list[dict[str, Any]],
) -> dict[int, dict[str, Any]]:
    """Indexa matrículas por código a partir dos vínculos de turma."""
    return {
        matricula["codigo_matricula"]: matricula
        for matricula in Matricula.objects.filter(
            codigo_matricula__in=[
                mt["codigo_matricula"] for mt in matriculas_turma
            ]
        ).values(
            "codigo_matricula",
            "aluno_id",
            "codigo_ue",
            "ano_letivo",
            "data_situacao_matricula",
            "codigo_situacao_matricula",
        )
    }


def _numero_chamada_preenchido(numero_chamada: str | None) -> bool:
    """Verifica se o número de chamada possui valor útil."""
    return (numero_chamada or "").strip().lstrip("0") != ""


def _data_matricula_na_janela(
    data_matricula: datetime | date | None,
    data_referencia_inicio: datetime | date | None,
    data_referencia_fim: datetime | date | None,
) -> bool:
    """Verifica se a data da matrícula está na janela informada."""
    data = _data_simples(data_matricula)
    inicio = _data_simples(data_referencia_inicio)
    fim = _data_simples(data_referencia_fim)
    if data is None:
        return True
    if inicio is not None and data < inicio:
        return False
    return fim is None or data <= fim


def _matricula_ativa_turma_valida(
    matricula: dict[str, Any],
    matricula_turma: dict[str, Any],
    data_referencia_inicio: datetime | date | None,
    data_referencia_fim: datetime | date | None,
) -> bool:
    """Verifica se a matrícula da turma pode compor a listagem."""
    if (
        matricula["codigo_situacao_matricula"]
        not in SITUACOES_MATRICULA_VALIDAS
    ):
        return False
    if not _numero_chamada_preenchido(matricula_turma["numero_chamada"]):
        return False
    return _data_matricula_na_janela(
        matricula["data_situacao_matricula"],
        data_referencia_inicio,
        data_referencia_fim,
    )


def _linha_aluno_ativo_turma(
    matricula_turma: dict[str, Any],
    matriculas_idx: dict[int, dict[str, Any]],
    data_referencia_inicio: datetime | date | None,
    data_referencia_fim: datetime | date | None,
) -> dict[str, Any] | None:
    """Monta uma linha candidata de aluno ativo da turma."""
    matricula = matriculas_idx.get(matricula_turma["codigo_matricula"])
    if matricula is None:
        return None
    if not _matricula_ativa_turma_valida(
        matricula,
        matricula_turma,
        data_referencia_inicio,
        data_referencia_fim,
    ):
        return None
    return {**matricula, **matricula_turma}


def _linhas_alunos_ativos_turma(
    matriculas_turma: list[dict[str, Any]],
    matriculas_idx: dict[int, dict[str, Any]],
    data_referencia_inicio: datetime | date | None,
    data_referencia_fim: datetime | date | None,
) -> list[dict[str, Any]]:
    """Lista linhas candidatas de alunos ativos da turma."""
    linhas: list[dict[str, Any]] = []
    for matricula_turma in matriculas_turma:
        linha = _linha_aluno_ativo_turma(
            matricula_turma,
            matriculas_idx,
            data_referencia_inicio,
            data_referencia_fim,
        )
        if linha is not None:
            linhas.append(linha)
    return linhas


def _linhas_mais_recentes_por_aluno(
    linhas: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Mantém a linha mais recente de cada aluno."""
    recentes: dict[int, tuple[Any, dict[str, Any]]] = {}
    for linha in linhas:
        chave = (
            linha["data_situacao_aluno_data_hora"] is not None,
            linha["data_situacao_aluno_data_hora"],
            linha["sequencia"] or 0,
        )
        atual = recentes.get(linha["aluno_id"])
        if atual is None or chave > atual[0]:
            recentes[linha["aluno_id"]] = (chave, linha)
    return [valor[1] for valor in recentes.values()]


def _montar_aluno_ativo_turma(
    linha: dict[str, Any],
    aluno: dict[str, Any],
) -> dict[str, Any]:
    """Monta dados de aluno ativo em turma."""
    return {
        "codigo_aluno": linha["aluno_id"],
        "nome_aluno": aluno.get("nome", ""),
        "nome_social_aluno": aluno.get("nome_social"),
        "data_nascimento": aluno.get("data_nascimento"),
        "codigo_situacao_matricula": linha["codigo_situacao_aluno"],
        "situacao_matricula": SituacaoMatricula.get_descricao(
            linha["codigo_situacao_aluno"]
        ),
        "data_situacao": linha["data_situacao_aluno_data_hora"],
        "numero_aluno_chamada": linha["numero_chamada"],
        "possui_deficiencia": aluno.get("possui_deficiencia", False),
        "codigo_matricula": linha["codigo_matricula"],
        "codigo_turma": linha["codigo_turma"],
        "codigo_escola": linha["codigo_ue"],
        "ano_letivo": linha["ano_letivo"],
    }


def _montar_alunos_ativos_turma(
    linhas: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Monta alunos ativos em turma."""
    alunos_idx = _alunos_indexados([linha["aluno_id"] for linha in linhas])
    return [
        _montar_aluno_ativo_turma(
            linha,
            alunos_idx.get(linha["aluno_id"], {}),
        )
        for linha in linhas
    ]


def _consultar_alunos_ativos_turma(
    codigo_turma: int,
    data_referencia_inicio: datetime | date | None = None,
    data_referencia_fim: datetime | date | None = None,
) -> list[dict[str, Any]]:
    """Lista alunos da turma com filtro opcional por janela de datas.

    Args:
        codigo_turma: Código EOL da turma.
        data_referencia_inicio: Data inicial opcional da janela.
        data_referencia_fim: Data final opcional da janela.

    Returns:
        Alunos da turma compatíveis com o período informado.
    """
    matriculas_turma = _matriculas_turma_da_turma(codigo_turma)
    if not matriculas_turma:
        return []

    matriculas_idx = _matriculas_idx_por_matriculas_turma(matriculas_turma)
    linhas = _linhas_alunos_ativos_turma(
        matriculas_turma,
        matriculas_idx,
        data_referencia_inicio,
        data_referencia_fim,
    )
    if not linhas:
        return []
    linhas = _linhas_mais_recentes_por_aluno(linhas)
    return _montar_alunos_ativos_turma(linhas)


def _data_simples(valor: datetime | date | None) -> date | None:
    """Reduz datetime/date a date (espelha CAST(... AS DATE) do legado)."""
    if valor is None:
        return None
    return valor.date() if isinstance(valor, datetime) else valor


def _aluno_ativo_no_periodo(
    codigo_situacao_aluno: int | None,
    data_matricula: date | None,
    data_situacao_aluno: date | None,
    data_referencia_inicio: date | None,
    data_referencia_fim: date | None,
) -> bool:
    """Replica o WHERE do legado ObterAlunosAtivosPorPeriodoETurma.

    Args:
        codigo_situacao_aluno: Situação do aluno na matrícula-turma.
        data_matricula: Data de situação da matrícula (DataMatricula).
        data_situacao_aluno: Data de situação na matrícula-turma.
        data_referencia_inicio: Início opcional da janela.
        data_referencia_fim: Fim da janela.

    Returns:
        ``True`` se o aluno deve aparecer no período informado.
    """
    if codigo_situacao_aluno == 10:
        return True
    if data_referencia_fim is None:
        return False
    if data_matricula is None or data_matricula >= data_referencia_fim:
        return False
    if codigo_situacao_aluno in (1, 6, 13, 5):
        return True
    if data_situacao_aluno is None:
        return False
    if data_referencia_inicio is None:
        return data_situacao_aluno > data_referencia_fim
    return data_situacao_aluno > data_referencia_fim or (
        data_referencia_inicio < data_situacao_aluno <= data_referencia_fim
    )


def _consultar_alunos_ativos_periodo_turma(
    codigo_turma: int,
    data_referencia_fim: datetime | date,
    data_referencia_inicio: datetime | date | None = None,
) -> list[dict[str, Any]]:
    """Lista alunos ativos na turma no período (espelha o legado EP4).

    Replica ``ObterAlunosAtivosPorPeriodoETurma``: matrícula-turma corrente
    (``origem_atual``), com o ano letivo escopado pela própria turma (e não
    pelo ano atual), filtrada pela janela de datas sobre a situação do aluno e
    a data da matrícula.

    Args:
        codigo_turma: Código EOL da turma.
        data_referencia_fim: Fim da janela de referência.
        data_referencia_inicio: Início opcional da janela.

    Returns:
        Alunos ativos na turma no período informado.
    """
    fim = _data_simples(data_referencia_fim)
    inicio = _data_simples(data_referencia_inicio)

    mts = list(
        MatriculaTurma.objects.filter(
            codigo_turma=codigo_turma, origem_atual=True
        ).values(
            "codigo_matricula",
            "codigo_turma",
            "codigo_situacao_aluno",
            "data_situacao_aluno",
            "data_situacao_aluno_data_hora",
            "numero_chamada",
            "sequencia",
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
            "ano_letivo",
            "data_situacao_matricula",
        )
    }
    rows: list[dict[str, Any]] = []
    for mt in mts:
        m = matriculas_idx.get(mt["codigo_matricula"])
        if not m:
            continue
        if _aluno_ativo_no_periodo(
            mt["codigo_situacao_aluno"],
            m["data_situacao_matricula"],
            _data_simples(mt["data_situacao_aluno"]),
            inicio,
            fim,
        ):
            rows.append({**m, **mt})

    if not rows:
        return []

    # Um registro por aluno, mantendo a matrícula-turma mais recente.
    recentes: dict[int, tuple[Any, dict[str, Any]]] = {}
    for r in rows:
        chave = (
            r["data_situacao_aluno_data_hora"] is not None,
            r["data_situacao_aluno_data_hora"],
            r["sequencia"] or 0,
        )
        atual = recentes.get(r["aluno_id"])
        if atual is None or chave > atual[0]:
            recentes[r["aluno_id"]] = (chave, r)
    rows = [valor[1] for valor in recentes.values()]

    alunos_idx = _alunos_indexados([r["aluno_id"] for r in rows])
    return [
        {
            "codigo_aluno": r["aluno_id"],
            "nome_aluno": alunos_idx.get(r["aluno_id"], {}).get("nome", ""),
            "nome_social_aluno": alunos_idx.get(r["aluno_id"], {}).get(
                "nome_social"
            ),
            "data_nascimento": alunos_idx.get(r["aluno_id"], {}).get(
                "data_nascimento"
            ),
            "codigo_situacao_matricula": r["codigo_situacao_aluno"],
            "situacao_matricula": SituacaoMatricula.get_descricao(
                r["codigo_situacao_aluno"]
            ),
            "data_situacao": r["data_situacao_aluno_data_hora"],
            "numero_aluno_chamada": r["numero_chamada"],
            "possui_deficiencia": alunos_idx.get(r["aluno_id"], {}).get(
                "possui_deficiencia", False
            ),
            "codigo_matricula": r["codigo_matricula"],
            "codigo_turma": r["codigo_turma"],
            "codigo_escola": r["codigo_ue"],
            "ano_letivo": r["ano_letivo"],
        }
        for r in rows
    ]


def obter_alunos_ativos_por_periodo_e_turma(
    codigo_turma: int,
    data_referencia_fim: datetime | date,
    data_referencia_inicio: datetime | date | None = None,
) -> list[dict[str, Any]]:
    """Retorna alunos ativos em uma turma por período.

    Args:
        codigo_turma: Código EOL da turma.
        data_referencia_fim: Data final da janela de referência.
        data_referencia_inicio: Data inicial da janela de referência.

    Returns:
        Alunos ativos encontrados para a turma e período.
    """
    return _consultar_alunos_ativos_periodo_turma(
        codigo_turma=codigo_turma,
        data_referencia_fim=data_referencia_fim,
        data_referencia_inicio=data_referencia_inicio,
    )


def obter_alunos_ativos_por_turma(
    codigo_turma: int,
) -> list[dict[str, Any]]:
    """Retorna alunos ativos em uma turma.

    Args:
        codigo_turma: Código EOL da turma.

    Returns:
        Alunos ativos encontrados para a turma.
    """
    return _consultar_alunos_ativos_turma(codigo_turma=codigo_turma)


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
        saida.setdefault(resp["aluno_id"], resp)
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


def _primeira_alocacao_por_matricula(
    codigos_matricula: list[int],
) -> dict[int, datetime | None]:
    """Data da primeira alocação de cada matrícula em turma.

    A matrícula pode ter passado por várias turmas (ou por várias situações
    na mesma turma); a data de matrícula do aluno é a da alocação mais
    antiga, incluindo as que já não são a vigente.

    Args:
        codigos_matricula: Códigos de matrícula a consultar.

    Returns:
        Código da matrícula -> data da alocação mais antiga.
    """
    if not codigos_matricula:
        return {}
    return {
        linha["codigo_matricula"]: linha["primeira"]
        for linha in MatriculaTurma.objects.filter(
            codigo_matricula__in=codigos_matricula,
        )
        .values("codigo_matricula")
        .annotate(primeira=Min("data_situacao_aluno_data_hora"))
    }


def _montar_aluno_matricula_turma(
    row: dict[str, Any],
    alunos_idx: dict[int, dict[str, Any]],
    responsaveis_idx: dict[int, dict[str, Any]],
    primeiras_alocacoes: dict[int, datetime | None],
) -> dict[str, Any]:
    """Monta os dados do aluno a partir do registro deduplicado."""
    aluno = alunos_idx.get(row["aluno_id"], {})
    resp = responsaveis_idx.get(row["aluno_id"], {})
    celular = None
    if resp.get("ddd_celular") or resp.get("numero_celular"):
        celular = f"{resp.get('ddd_celular') or ''}" + (
            resp.get("numero_celular") or ""
        )
    codigo_situacao = row["codigo_situacao_aluno"]
    return {
        "codigo_aluno": row["aluno_id"],
        "nome_aluno": aluno.get("nome", ""),
        "nome_social_aluno": aluno.get("nome_social"),
        "data_nascimento": aluno.get("data_nascimento"),
        "codigo_situacao_matricula": codigo_situacao,
        "situacao_matricula": SituacaoMatricula.get_descricao(codigo_situacao),
        "data_situacao": row["data_situacao_aluno_data_hora"],
        "numero_aluno_chamada": row["numero_chamada"],
        "possui_deficiencia": aluno.get("possui_deficiencia", False),
        "codigo_matricula": row["codigo_matricula"],
        "codigo_turma": row["codigo_turma"],
        "codigo_escola": row["codigo_ue"],
        "ano_letivo": row["ano_letivo"],
        "data_matricula": primeiras_alocacoes.get(row["codigo_matricula"]),
        "nome_responsavel": resp.get("nome"),
        "tipo_responsavel": resp.get("tipo_responsavel"),
        "celular_responsavel": celular,
        "data_atualizacao_contato": aluno.get("data_atualizacao_contato"),
        "sequencia": row["sequencia"],
        "codigo_dre": row["codigo_dre"],
    }


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


def obter_alunos_turma(
    codigo_turma: int,
    data_aula: datetime | None,
    data_matricula: datetime | None = None,
    codigo_aluno: int | None = None,
    considerar_inativos: bool = False,
    sequencia: int | None = None,
) -> list[dict[str, Any]]:
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
    primeiras_alocacoes = _primeira_alocacao_por_matricula(
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
            r, alunos_idx, responsaveis_idx, primeiras_alocacoes
        )
        for r in finais
    ]


def obter_necessidades_especiais_por_aluno(
    codigo_aluno: int,
) -> list[dict[str, Any]]:
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
        {
            "codigo_aluno": r["aluno_id"],
            "tipo_necessidade_especial": r["necessidade_especial_id"],
            "descricao_necessidade_especial": descricoes.get(
                r["necessidade_especial_id"], ""
            ),
            "tipo_recurso": r.get("codigo_tipo_recurso"),
            "descricao_recurso": r.get("descricao_tipo_recurso"),
        }
        for r in rows
    ]


def obter_alunos_por_codigos_e_ano(
    codigos_aluno: Sequence[int], ano_letivo: int
) -> list[dict[str, Any]]:
    """Lista turmas dos alunos informados por ano letivo.

    Como no legado, usa os vínculos históricos apenas para anos anteriores
    ao corrente e não filtra situação de matrícula nem tipo de turma.

    Args:
        codigos_aluno: Códigos EOL dos alunos.
        ano_letivo: Ano letivo usado no filtro.

    Returns:
        Turmas dos alunos restritas ao ano informado.
    """
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

    saida: list[dict[str, Any]] = []
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
                    {
                        "codigo_aluno": m["aluno_id"],
                        "ano_letivo": m["ano_letivo"],
                        "nome_aluno": aluno.get("nome", ""),
                        "nome_social_aluno": aluno.get("nome_social"),
                        "codigo_situacao_matricula": codigo_situacao,
                        "situacao_matricula": SituacaoMatricula.get_descricao(
                            codigo_situacao
                        ),
                        "data_situacao": data_situacao,
                        "data_nascimento": aluno.get("data_nascimento"),
                        "documento_cpf": aluno.get("cpf"),
                        "data_matricula": (
                            m.get("data_situacao_matricula_data_hora")
                            or m["data_situacao_matricula"]
                        ),
                        "numero_aluno_chamada": mt.get("numero_chamada"),
                        "codigo_turma": mt.get("codigo_turma") or 0,
                        "data_atualizacao_contato": aluno.get(
                            "data_atualizacao_contato"
                        ),
                        "nome_responsavel": responsavel.get("nome"),
                        "tipo_responsavel": responsavel.get(
                            "tipo_responsavel"
                        ),
                        "ddd_celular": responsavel.get("ddd_celular"),
                        "numero_celular": responsavel.get("numero_celular"),
                        "codigo_escola": m["codigo_ue"],
                        "codigo_tipo_turma": mt.get("codigo_tipo_turma"),
                        "data_atualizacao_tabela": (
                            mt.get("data_atualizacao_tabela") or data_situacao
                        ),
                    }
                )
    return saida


def obter_alunos_por_codigos(
    codigos_aluno: Sequence[int],
) -> list[dict[str, Any]]:
    """Lista turmas atuais dos alunos informados.

    Args:
        codigos_aluno: Códigos EOL dos alunos.

    Returns:
        Turmas atuais encontradas para os alunos.
    """
    if not codigos_aluno:
        return []
    saida: list[dict[str, Any]] = []
    for codigo in codigos_aluno:
        saida.extend(_turmas_atuais_por_aluno(codigo))
    return saida


def obter_informacoes_aluno(
    codigo_aluno: int,
) -> dict[str, Any] | None:
    """Retorna informações cadastrais do aluno.

    Args:
        codigo_aluno: Código EOL do aluno.

    Returns:
        Informações cadastrais do aluno, ou ``None`` quando não existir.
    """
    aluno = Aluno.objects.filter(codigo_aluno=codigo_aluno).first()
    if aluno is None:
        return None
    return {
        "codigo_aluno": aluno.codigo_aluno,
        "nome_aluno": aluno.nome,
        "nome_social_aluno": aluno.nome_social,
        "nome_mae": aluno.nome_mae,
        "sexo": aluno.sexo,
        "nacionalidade": aluno.nacionalidade,
        "raca_cor": aluno.raca_cor,
        "nis": aluno.nis,
        "cpf": aluno.cpf,
        "cns": aluno.cns,
        "endereco": _endereco_responsavel(
            _responsavel_principal(codigo_aluno)
        ),
        "data_nascimento": aluno.data_nascimento,
        "possui_deficiencia": aluno.possui_deficiencia,
    }


def obter_informacoes_alunos_da_turma(
    codigo_turma: int,
) -> list[dict[str, Any]]:
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
        {
            "numero_aluno_chamada": r["numero_chamada"],
            "codigo_aluno": r["aluno_id"],
            "nome_aluno": alunos_idx.get(r["aluno_id"], {}).get("nome", ""),
            "nome_social_aluno": alunos_idx.get(r["aluno_id"], {}).get(
                "nome_social"
            ),
            "sexo": alunos_idx.get(r["aluno_id"], {}).get("sexo"),
            "raca_cor": alunos_idx.get(r["aluno_id"], {}).get("raca_cor"),
            "numero_chamada": numero_chamada_int(r["numero_chamada"]),
            "raca": alunos_idx.get(r["aluno_id"], {}).get("raca_cor"),
            "codigo_raca": _codigo_raca(
                alunos_idx.get(r["aluno_id"], {}).get("raca_cor")
            ),
        }
        for r in rows_validas
    ]
    return sorted(saida, key=lambda item: item["nome_aluno"])


def obter_quantidade_matriculados_por_ano_e_cc(
    ano_letivo: int,
    ue_id: str | None = None,
    componentes_curriculares: list[int] | None = None,  # NOSONAR
    dre_id: str | None = None,  # NOSONAR
) -> list[dict[str, Any]]:
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
        {
            "codigo_turma": r["codigo_turma"],
            "quantidade": r["quantidade"],
            "ordem": ordem,
        }
        for ordem, r in enumerate(agrupado, start=1)
    ]


def obter_quantidade_matriculados(
    ano_letivo: int,
    ue_codigo: str = "",
    dre_codigo: str = "",  # NOSONAR
    modalidade: list[int] | None = None,  # NOSONAR
    ano: list[int] | None = None,  # NOSONAR
    turma: list[str] | None = None,  # NOSONAR
) -> list[dict[str, Any]]:
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

    saida: list[dict[str, Any]] = []
    for ordem, ((ue, codigo_turma), qtd) in enumerate(
        sorted(grupos.items()), start=1
    ):
        saida.append(
            {
                "quantidade": qtd,
                "ordem": ordem,
                "codigo_turma": codigo_turma,
                "ue_codigo": ue,
            }
        )
    return saida


def obter_quantidade_matriculados_cc_contrato(
    ano_letivo: int,
    componentes_curriculares: Sequence[int],
    dre_id: str | None = None,
    ue_id: str | None = None,
) -> list[dict[str, Any]]:
    """Lista matriculados por componente curricular no contrato do legado.

    Agregado de matrículas em turma-programa de alunos que também possuem
    turma regular, filtrado por componentes curriculares, DRE e UE. A ordem
    sem modalidade é retornada como zero, como no legado.

    Args:
        ano_letivo: Ano letivo da consulta.
        componentes_curriculares: Códigos dos componentes curriculares.
        dre_id: Código da DRE usado como filtro opcional.
        ue_id: Código da UE usado como filtro opcional.

    Returns:
        Registros agregados no formato do contrato interno.
    """
    qs = MatriculaComponenteCurricularAnoLetivo.objects.filter(
        ano_letivo=ano_letivo,
        componente_curricular_id__in=list(componentes_curriculares),
    )
    if dre_id:
        qs = qs.filter(codigo_dre=dre_id)
    if ue_id:
        qs = qs.filter(codigo_ue=ue_id)
    # Aproxima a ordem de agrupamento do legado (etapa, componente, série,
    # turma); a etapa não é materializada, então a ordem da modalidade entra
    # no lugar, com nulos primeiro.
    qs = qs.order_by(
        F("ordem").asc(nulls_first=True),
        "componente_curricular_id",
        "ano",
        "turma",
    )
    return [
        {
            "componente_curricular_id": r["componente_curricular_id"],
            "quantidade": r["quantidade"],
            "ordem": r["ordem"] or 0,
            "modalidade": r["modalidade"],
            "ano": r["ano"],
            "turma": r["turma"],
        }
        for r in qs.values(
            "componente_curricular_id",
            "quantidade",
            "ordem",
            "modalidade",
            "ano",
            "turma",
        )
    ]


# Tipos de escola aceitos pela modalidade Educação Infantil no legado.
_TIPOS_ESCOLA_INFANTIL = (2, 17, 28, 31)

# Etapas agregadas por modalidade no read-model (código da modalidade SGP).
_MODALIDADES_CONTRATO = {1, 3, 5, 6}


def _pares_ue_turma_por_codigos(
    codigos_turma: Sequence[int],
) -> set[tuple[str, str]]:
    """Resolve códigos de turma em pares (UE, nome da turma).

    Args:
        codigos_turma: Códigos EOL das turmas consultadas.

    Returns:
        Pares de código da UE e nome da turma correspondentes.
    """
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
    """Lista a quantidade de matriculados no contrato do legado.

    Agregado por DRE, UE, modalidade, série e turma, como no legado. A
    modalidade infantil também restringe o tipo de escola.

    Args:
        ano_letivo: Ano letivo da consulta.
        dre_codigo: Código da DRE usado como filtro opcional.
        ue_codigo: Código da UE usado como filtro opcional.
        modalidade: Códigos de modalidade SGP usados como filtro.
        ano: Séries usadas como filtro; ``-99`` desativa o filtro.
        turma: Códigos de turma usados como filtro opcional.

    Returns:
        Registros agregados no formato do contrato interno.
    """
    qs = MatriculaAnoLetivo.objects.filter(ano_letivo=ano_letivo)
    if dre_codigo:
        qs = qs.filter(codigo_dre=dre_codigo)
    if ue_codigo:
        qs = qs.filter(codigo_ue=ue_codigo)
    if ano and -99 not in ano:
        qs = qs.filter(ano__in=[str(a) for a in ano])
    for codigo_modalidade in modalidade or []:
        if codigo_modalidade not in _MODALIDADES_CONTRATO:
            continue
        qs = qs.filter(codigo_modalidade=codigo_modalidade)
        if codigo_modalidade == 1:
            qs = qs.filter(tipo_escola__in=_TIPOS_ESCOLA_INFANTIL)

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
        saida.append(
            {
                "quantidade": r["quantidade"],
                "ordem": r["ordem"],
                "modalidade": r["modalidade"],
                "ano": r["ano"],
                "turma": r["turma"],
                "dre_codigo": r["codigo_dre"],
                "ue_codigo": r["codigo_ue"],
            }
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
) -> list[dict[str, Any]]:
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


def obter_responsaveis_dre_ue_turma(
    codigo_ue: str | None = None,
    ano_letivo: int | None = None,
    codigo_dre: str | None = None,
) -> list[dict[str, Any]]:
    """Lista responsáveis vigentes agrupados por UE e turma.

    Args:
        codigo_ue: Código EOL da UE usado como filtro opcional.
        ano_letivo: Ano letivo usado como filtro opcional.
        codigo_dre: Código EOL da DRE usado como filtro opcional.

    Returns:
        Responsáveis vigentes por UE, turma e aluno.
    """
    ano = (
        ano_letivo
        if ano_letivo and ano_letivo > 0
        else timezone.localdate().year
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
    # O domínio não acompanha instalação do aplicativo; sempre falso.
    return [{**row, "tem_app_instalado": False} for row in rows]


def obter_dados_responsavel(
    cpf_responsavel: str,
) -> list[dict[str, Any]]:
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
        {
            "codigo_responsavel": v["codigo_responsavel"],
            "cpf": v["cpf"],
            "email": v["email"],
            "nome": v["nome"],
            "tipo_responsavel": v["tipo_responsavel"],
            "nome_aluno": alunos_idx.get(v["aluno_id"], {}).get("nome", ""),
            "nome_social_aluno": alunos_idx.get(v["aluno_id"], {}).get(
                "nome_social"
            ),
            "data_nascimento_aluno": alunos_idx.get(v["aluno_id"], {}).get(
                "data_nascimento"
            ),
            "codigo_aluno": str(v["aluno_id"]),
            "ddd_celular": v["ddd_celular"],
            "numero_celular": v["numero_celular"],
            "autoriza_sms": v["autoriza_sms"],
            "logradouro": v["logradouro"],
            "cep": v["cep"],
            "data_fim_vinculo": v["data_fim_vinculo"],
        }
        for v in vinculos
    ]


def obter_dados_responsavel_resumido(
    cpf_responsavel: str,
) -> dict[str, Any] | None:
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
    return {
        "id": v["codigo_responsavel"],
        "cpf": v["cpf"],
        "email": v["email"],
        "nome": v["nome"],
        "tipo_responsavel": v["tipo_responsavel"],
        "data_nascimento": v.get("data_nascimento"),
        "data_atualizacao": v["data_atualizacao_tabela"],
        "nome_mae": v.get("nome_mae"),
        "ddd_celular": v["ddd_celular"],
        "numero_celular": v["numero_celular"],
        "codigo_aluno": None,
    }


def atualizar_dados_responsavel_busca_ativa(
    codigo_aluno: int,
    cpf_responsavel: str,
    *,
    email: str | None = None,
    ddd_celular: str | None = None,
    numero_celular: str | None = None,
) -> dict[str, Any]:
    """Atualiza contatos do responsável no fluxo de busca ativa.

    Args:
        codigo_aluno: Código EOL do aluno vinculado.
        cpf_responsavel: CPF do responsável a atualizar.
        email: Novo e-mail; ``None`` mantém o valor atual.
        ddd_celular: Novo DDD; ``None`` mantém o valor atual.
        numero_celular: Novo número; ``None`` mantém o valor atual.

    Returns:
        Dados resumidos do responsável após a atualização. Quando o
        vínculo não existir, devolve um registro sintético com os dados
        recebidos e ``codigo_responsavel=0``.
    """
    resp = ResponsavelAluno.objects.filter(
        cpf=cpf_responsavel, aluno_id=codigo_aluno
    ).first()
    if resp is None:
        return {
            "id": 0,
            "cpf": cpf_responsavel,
            "email": email,
            "nome": None,
            "tipo_responsavel": None,
            "data_nascimento": None,
            "data_atualizacao": None,
            "nome_mae": None,
            "ddd_celular": ddd_celular,
            "numero_celular": numero_celular,
            "codigo_aluno": str(codigo_aluno),
        }

    if email is not None:
        resp.email = email
    if ddd_celular is not None:
        resp.ddd_celular = ddd_celular
    if numero_celular is not None:
        resp.numero_celular = numero_celular
    resp.save(update_fields=["email", "ddd_celular", "numero_celular"])

    return {
        "id": resp.codigo_responsavel,
        "cpf": resp.cpf,
        "email": resp.email,
        "nome": resp.nome,
        "tipo_responsavel": resp.tipo_responsavel,
        "data_nascimento": None,
        "data_atualizacao": getattr(resp, "data_atualizacao_tabela", None),
        "nome_mae": None,
        "ddd_celular": resp.ddd_celular,
        "numero_celular": resp.numero_celular,
        "codigo_aluno": str(codigo_aluno),
    }


def cadastrar_dados_responsavel(
    codigo_aluno: int,
    cpf_responsavel: str,
    *,
    nome: str = "",
    email: str = "",
    tipo_responsavel: int | None = None,
    ddd_celular: str = "",
    numero_celular: str = "",
) -> dict[str, Any]:
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

    return {
        "id": resp.codigo_responsavel,
        "cpf": resp.cpf,
        "email": resp.email,
        "nome": resp.nome,
        "tipo_responsavel": resp.tipo_responsavel,
        "data_nascimento": None,
        "data_atualizacao": getattr(resp, "data_atualizacao_tabela", None),
        "nome_mae": None,
        "ddd_celular": resp.ddd_celular,
        "numero_celular": resp.numero_celular,
        "codigo_aluno": str(codigo_aluno),
    }


def obter_dados_responsavel_filiacao(
    codigo_aluno: int,
) -> list[dict[str, Any]]:
    """Lista dados de filiação do aluno.

    Args:
        codigo_aluno: Código EOL do aluno.

    Returns:
        Responsáveis de filiação encontrados para o aluno.
    """
    responsaveis = (
        ResponsavelAluno.objects.filter(
            aluno_id=codigo_aluno,
            tipo_responsavel__in=(1, 2),
            endereco_id__isnull=False,
        )
        .values(
            "nome",
            "cpf",
            "email",
            "ddd_celular",
            "numero_celular",
            "ddd_telefone_fixo",
            "nr_telefone_fixo",
            "ddd_telefone_comercial",
            "nr_telefone_comercial",
            "tipo_responsavel",
            "endereco_id",
            "numero_endereco",
            "complemento",
            "bairro",
            "cep",
            "nome_municipio",
            "sigla_uf",
            "tipo_logradouro",
            "logradouro",
        )
        .order_by("tipo_responsavel")
    )
    return [
        {
            "nome_responsavel": responsavel["nome"],
            "cpf": responsavel["cpf"],
            "email": responsavel["email"],
            "ddd_celular": responsavel["ddd_celular"],
            "numero_celular": responsavel["numero_celular"],
            "ddd_residencial": responsavel["ddd_telefone_fixo"],
            "numero_residencial": responsavel["nr_telefone_fixo"],
            "ddd_comercial": responsavel["ddd_telefone_comercial"],
            "numero_comercial": responsavel["nr_telefone_comercial"],
            "tipo_responsavel": responsavel["tipo_responsavel"],
            "endereco": {
                "id": responsavel["endereco_id"],
                "nro": responsavel["numero_endereco"],
                "complemento": responsavel["complemento"],
                "bairro": responsavel["bairro"],
                "cep": responsavel["cep"],
                "nome_municipio": responsavel["nome_municipio"],
                "sigla_uf": responsavel["sigla_uf"],
                "tipo_logradouro": responsavel["tipo_logradouro"],
                "logradouro": responsavel["logradouro"],
            },
        }
        for responsavel in responsaveis
    ]


def _consolidacao_por_turma(
    ano_letivo: int, ue_codigo: str
) -> list[dict[str, Any]]:
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
        {
            "turma_codigo": str(r["codigo_turma"]),
            "quantidade": r["quantidade"],
        }
        for r in agrupado
    ]


def obter_matriculas_ano_atual(
    ano_letivo: int, ue_codigo: str
) -> list[dict[str, Any]]:
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
) -> list[dict[str, Any]]:
    """Consolida matrículas válidas de ano anterior por turma.

    Args:
        ano_letivo: Ano letivo usado no filtro.
        ue_codigo: Código EOL da UE.

    Returns:
        Consolidação de matrículas por turma.
    """
    rows = (
        MatriculaAnoAnterior.objects.filter(
            ano_letivo=ano_letivo,
            codigo_ue=ue_codigo,
        )
        .values("codigo_turma", "quantidade")
        .order_by("codigo_turma")
    )
    return [
        {
            "turma_codigo": str(row["codigo_turma"]),
            "quantidade": row["quantidade"],
        }
        for row in rows
    ]


def obter_quantidade_alunos_por_turma_da_escola(
    codigo_escola: str,
) -> list[dict[str, Any]]:
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
) -> list[dict[str, Any]]:
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
        {
            "codigo_aluno": m["aluno_id"],
            "nome_aluno": aluno.get("nome", ""),
            "nome_social_aluno": aluno.get("nome_social"),
            "codigo_situacao_matricula": m["codigo_situacao_matricula"],
            "situacao_matricula": m["situacao_matricula"],
            "data_situacao": m["data_situacao_matricula"],
            "codigo_turma": mts.get(m["codigo_matricula"], {}).get(
                "codigo_turma"
            )
            or 0,
            "codigo_matricula": m["codigo_matricula"],
            "ano_letivo": m["ano_letivo"],
        }
        for m in matriculas
    ]


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
            SQL_A15_QUANTIDADE_POR_ANO_E_CC,
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
                "codigo_turma": r["codigo_turma"],
                "quantidade": r["quantidade"],
                "ordem": r["ordem"],
            }
            for r in rows
        ]
    )


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
            SQL_A16_QUANTIDADE,
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
                "quantidade": r["quantidade"],
                "ordem": r["ordem"],
                "codigo_turma": r["codigo_turma"],
                "ueCodigo": r["ue_codigo"],
            }
            for r in rows
        ]
    )


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
                "codigo_eol": r["codigo_eol"],
                "nome_responsavel": r["nome_responsavel"],
                "cpf_responsavel": r["cpf_responsavel"],
                "nome": r["nome"],
                "nome_social": r["nome_social"],
                "codigo_escola": r["codigo_escola"],
                "tipo_responsavel": r["tipo_responsavel"],
                "codigo_turma": r["codigo_turma"],
                "situacao_matricula": r["situacao_matricula"],
                "data_nascimento": (
                    r["data_nascimento"].isoformat()
                    if r["data_nascimento"]
                    else None
                ),
                "data_situacao_matricula": (
                    r["data_situacao_matricula"].isoformat()
                    if r["data_situacao_matricula"]
                    else None
                ),
                "ano_letivo": r["ano_letivo"],
            }
            for r in rows
        ]
    )


def obter_dados_acompanhamento_escolar_contrato(
    codigo_aluno: int | None = None,
    codigo_dre: str | None = None,
    codigo_ue: str | None = None,
    cpf_responsavel: str | None = None,
) -> list[dict[str, Any]]:
    """Lista dados de acompanhamento escolar no contrato do legado.

    Considera apenas responsável vigente com CPF e aluno sem sigilo, como o
    legado, com filtros opcionais de aluno, DRE, UE e CPF do responsável.

    Args:
        codigo_aluno: Código EOL do aluno usado como filtro opcional.
        codigo_dre: Código da DRE usado como filtro opcional.
        codigo_ue: Código da UE usado como filtro opcional.
        cpf_responsavel: CPF do responsável usado como filtro opcional.

    Returns:
        Registros de acompanhamento no formato do contrato interno.
    """
    qs = DadosAlunoAcompanhamentoEscolar.objects.filter(
        cpf_responsavel__isnull=False,
        data_fim_vinculo_responsavel__isnull=True,
        tipo_sigilo__isnull=True,
    )
    if codigo_aluno:
        qs = qs.filter(codigo_aluno=codigo_aluno)
    if codigo_dre:
        qs = qs.filter(codigo_dre=codigo_dre)
    if codigo_ue:
        qs = qs.filter(codigo_ue=codigo_ue)
    if cpf_responsavel:
        qs = qs.filter(cpf_responsavel=cpf_responsavel)

    saida: list[dict[str, Any]] = []
    for r in qs.values(
        "codigo_aluno",
        "nome_responsavel",
        "cpf_responsavel",
        "nome",
        "nome_social",
        "codigo_ue",
        "codigo_dre",
        "unidade_educacional",
        "tipo_responsavel",
        "codigo_tipo_escola",
        "descricao_tipo_escola",
        "sigla_dre",
        "codigo_turma",
        "turma",
        "situacao_matricula",
        "data_nascimento",
        "data_situacao_matricula",
        "data_situacao_matricula_data_hora",
        "codigo_ciclo_ensino",
        "codigo_etapa_ensino",
        "serie_resumida",
    ):
        data_situacao = r["data_situacao_matricula_data_hora"]
        if data_situacao is None and r["data_situacao_matricula"]:
            data_situacao = datetime.combine(
                r["data_situacao_matricula"], datetime.min.time()
            )
        saida.append(
            {
                "codigo_eol": r["codigo_aluno"],
                "nome_responsavel": r["nome_responsavel"],
                "cpf_responsavel": r["cpf_responsavel"],
                "nome": r["nome"],
                "nome_social": r["nome_social"],
                "codigo_escola": r["codigo_ue"],
                "codigo_dre": r["codigo_dre"],
                "escola": r["unidade_educacional"],
                "tipo_responsavel": r["tipo_responsavel"],
                "codigo_tipo_escola": r["codigo_tipo_escola"],
                "descricao_tipo_escola": r["descricao_tipo_escola"],
                "sigla_dre": r["sigla_dre"],
                "codigo_turma": r["codigo_turma"],
                "turma": r["turma"],
                "situacao_matricula": r["situacao_matricula"],
                "data_nascimento": r["data_nascimento"],
                "data_situacao_matricula": data_situacao,
                "codigo_ciclo_ensino": r["codigo_ciclo_ensino"],
                "codigo_etapa_ensino": r["codigo_etapa_ensino"],
                "serie_resumida": r["serie_resumida"],
            }
        )
    return saida


def obter_responsaveis_dre_ue_turma_json(
    codigo_ue: str | None = None,
    ano_letivo: int | None = None,
    codigo_dre: str | None = None,
) -> bytes:
    """Lista responsáveis vigentes agrupados por UE e turma em JSON.

    Args:
        codigo_ue: Código EOL da UE usado como filtro opcional.
        ano_letivo: Ano letivo usado como filtro opcional.
        codigo_dre: Código EOL da DRE usado como filtro opcional.

    Returns:
        Payload JSON serializado em bytes.
    """
    ano = (
        ano_letivo
        if ano_letivo and ano_letivo > 0
        else timezone.localdate().year
    )
    if connection.vendor == "postgresql":
        return _exec_json_agg(
            SQL_A19_RESPONSAVEIS,
            {
                "codigo_dre": codigo_dre or None,
                "codigo_ue": codigo_ue or None,
                "ano_letivo": ano,
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
                "codigo_dre": r["codigo_dre"],
                "dre": r["dre"],
                "codigo_ue": r["codigo_ue"],
                "ue": r["ue"],
                "codigo_turma": r["codigo_turma"],
                "turma": r["turma"],
                "cpf_responsavel": r["cpf_responsavel"],
                "codigo_aluno": r["codigo_aluno"],
                "codigo_tipo_escola": r["codigo_tipo_escola"],
                "codigo_etapa_ensino": r["codigo_etapa_ensino"],
                "codigo_ciclo_ensino": r["codigo_ciclo_ensino"],
                "serie_resumida": r["serie_resumida"],
                "codigo_modalidade_turma": r["codigo_modalidade_turma"],
                "tem_app_instalado": r["tem_app_instalado"],
            }
            for r in rows
        ]
    )


__all__ = [
    "atualizar_dados_responsavel_busca_ativa",
    "buscar_alunos_autocomplete",
    "buscar_alunos_ativos_autocomplete",
    "buscar_alunos_da_ue",
    "buscar_turmas_do_aluno",
    "buscar_turmas_do_aluno_por_situacao_matricula",
    "cadastrar_dados_responsavel",
    "obter_alunos_ativos_por_periodo_e_turma",
    "obter_alunos_ativos_por_turma",
    "obter_alunos_turma",
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
