"""Services do domínio Alunos."""
from datetime import UTC, date, datetime
from typing import Any

from django.db.models import Min

from apps.alunos.constants import codigo_raca
from apps.alunos.enums import (
    SITUACOES_MATRICULA_ATIVAS_TURMA,
    SITUACOES_MATRICULA_VALIDAS,
    SituacaoMatricula,
)
from apps.alunos.models import (
    Aluno,
    Matricula,
    MatriculaTurma,
    NecessidadeEspecialAluno,
    TipoNecessidadeEspecial,
)
from apps.alunos.repositories import (
    alunos_indexados,
    matriculas_por_codigos_turma,
)
from apps.alunos.services.responsaveis import (
    responsaveis_por_aluno,
    responsavel_principal,
)
from apps.core.utils import fim_do_dia, numero_chamada_int

SITUACOES_MATRICULA_TURMA_ATIVAS = (1, 6, 10, 13)



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


def _linha_serializavel_aluno_ativo_turma(
    linha: dict[str, Any],
    aluno: dict[str, Any],
) -> dict[str, Any]:
    """Agrupa dados crus de aluno ativo em turma."""
    return {"linha": linha, "aluno": aluno}


def _linhas_serializaveis_alunos_ativos_turma(
    linhas: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Agrupa alunos ativos em turma."""
    alunos_idx = alunos_indexados([linha["aluno_id"] for linha in linhas])
    return [
        _linha_serializavel_aluno_ativo_turma(
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
    return _linhas_serializaveis_alunos_ativos_turma(linhas)


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

    alunos_idx = alunos_indexados([r["aluno_id"] for r in rows])
    return [
        {"linha": r, "aluno": alunos_idx.get(r["aluno_id"], {})}
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
    """Retorna a data da primeira alocação de cada matrícula em turma.

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


def _linha_aluno_matricula_turma(
    row: dict[str, Any],
    alunos_idx: dict[int, dict[str, Any]],
    responsaveis_idx: dict[int, dict[str, Any]],
    primeiras_alocacoes: dict[int, datetime | None],
) -> dict[str, Any]:
    """Agrupa dados crus do registro deduplicado."""
    return {
        "linha": row,
        "aluno": alunos_idx.get(row["aluno_id"], {}),
        "responsavel": responsaveis_idx.get(row["aluno_id"], {}),
        "primeira_alocacao": primeiras_alocacoes.get(row["codigo_matricula"]),
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
    ano_letivo: int | None = None,
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
        ano_letivo: Quando informado, restringe às alocações cuja turma
            pertence a esse ano letivo.

    Returns:
        Alunos distintos na turma conforme os filtros informados.
    """
    filtros: dict[str, Any] = {"codigo_turma": codigo_turma}
    if data_aula is not None:
        filtros["data_situacao_aluno_data_hora__lte"] = fim_do_dia(data_aula)
    if sequencia is not None:
        filtros["sequencia"] = sequencia
    if ano_letivo is not None:
        filtros["ano_letivo_turma"] = ano_letivo

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
    alunos_idx = alunos_indexados(codigos_alunos)
    responsaveis_idx = responsaveis_por_aluno(codigos_alunos)
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
        _linha_aluno_matricula_turma(
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
            "necessidade": r,
            "descricao_necessidade_especial": descricoes.get(
                r["necessidade_especial_id"], ""
            ),
        }
        for r in rows
    ]


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
        "aluno": aluno,
        "responsavel": responsavel_principal(codigo_aluno),
    }


def obter_informacoes_alunos_da_turma(
    codigo_turma: int,
) -> list[dict[str, Any]]:
    """Lista informações dos alunos de uma turma.

    Args:
        codigo_turma: Código EOL da turma.
    """
    rows = matriculas_por_codigos_turma([codigo_turma])
    rows_validas = [
        r
        for r in rows
        if r["codigo_situacao_matricula"] in SITUACOES_MATRICULA_VALIDAS
    ]
    if not rows_validas:
        return []

    alunos_idx = alunos_indexados([r["aluno_id"] for r in rows_validas])
    saida = [
        {
            "row": r,
            "aluno": alunos_idx.get(r["aluno_id"], {}),
            "numero_chamada": numero_chamada_int(r["numero_chamada"]),
            "codigo_raca": codigo_raca(
                alunos_idx.get(r["aluno_id"], {}).get("raca_cor")
            ),
        }
        for r in rows_validas
    ]
    return sorted(saida, key=lambda item: item["aluno"].get("nome", ""))


def _chave_dedup_matricula(
    row: dict[str, Any],
    primeiras_alocacoes: dict[int, datetime | None],
) -> tuple[datetime, datetime, str]:
    """Ordena as alocações de uma matrícula da mais recente para a mais antiga.

    Args:
        row: Registro combinado de matrícula e matrícula-turma.
        primeiras_alocacoes: Código da matrícula -> data da alocação mais
            antiga.

    Returns:
        Chave de ordenação por data de matrícula, data de situação e
        número de chamada.
    """
    minimo = datetime.min.replace(tzinfo=UTC)
    return (
        primeiras_alocacoes.get(row["codigo_matricula"]) or minimo,
        row["data_situacao_aluno_data_hora"] or minimo,
        row["numero_chamada"] or "",
    )


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


def obter_todos_alunos_turma(
    codigo_turma: int,
    codigo_aluno: int | None = None,
) -> list[dict[str, Any]]:
    """Lista o histórico de vínculos dos alunos com a turma.

    Cada matrícula rende uma linha por período de permanência na turma: um
    remanejamento de saída encerra a linha corrente e a alocação seguinte
    da mesma matrícula abre uma linha nova, de modo que a matrícula aparece
    antes e depois do remanejamento. Sem remanejamento, as alocações
    seguintes atualizam a linha existente. A data de matrícula de cada
    linha é a da alocação que a abriu.

    Args:
        codigo_turma: Código EOL da turma.
        codigo_aluno: Quando informado, restringe o resultado ao aluno
            correspondente.

    Returns:
        Vínculos dos alunos com a turma, sem filtro de situação.
    """
    mts = list(
        MatriculaTurma.objects.filter(codigo_turma=codigo_turma).values(
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
        )
    }
    rows = [
        {**matriculas_idx[mt["codigo_matricula"]], **mt}
        for mt in mts
        if mt["codigo_matricula"] in matriculas_idx
    ]
    if codigo_aluno is not None:
        rows = [r for r in rows if r["aluno_id"] == codigo_aluno]
    if not rows:
        return []

    # Alocações da mesma matrícula podem empatar na data de situação (troca
    # de turma registrada no mesmo instante). A sequência desempata para que
    # a ordem de percurso — e portanto o colapso — seja determinística.
    minimo = datetime.min.replace(tzinfo=UTC)
    rows.sort(
        key=lambda r: (
            r["aluno_id"],
            r["data_situacao_aluno_data_hora"] or minimo,
            r["sequencia"],
        )
    )

    entradas: list[dict[str, Any]] = []
    corrente_por_matricula: dict[int, dict[str, Any]] = {}
    for row in rows:
        corrente = corrente_por_matricula.get(row["codigo_matricula"])
        encerrada = (
            corrente is not None
            and corrente["codigo_situacao_aluno"]
            == SituacaoMatricula.REMANEJADO_SAIDA
        )
        if corrente is not None and not encerrada:
            corrente["numero_chamada"] = row["numero_chamada"]
            corrente["codigo_situacao_aluno"] = row["codigo_situacao_aluno"]
            corrente["data_situacao_aluno_data_hora"] = row[
                "data_situacao_aluno_data_hora"
            ]
        else:
            nova = dict(row)
            nova["data_matricula"] = row["data_situacao_aluno_data_hora"]
            entradas.append(nova)
            corrente_por_matricula[row["codigo_matricula"]] = nova

    codigos_alunos = [e["aluno_id"] for e in entradas]
    alunos_idx = alunos_indexados(codigos_alunos)
    responsaveis_idx = responsaveis_por_aluno(codigos_alunos)
    return [
        _montar_aluno_matricula_turma(
            entrada,
            alunos_idx,
            responsaveis_idx,
            {entrada["codigo_matricula"]: entrada["data_matricula"]},
        )
        for entrada in entradas
    ]


def obter_matriculas_turmas_aluno(
    codigo_aluno: int,
    data_aula: datetime | None = None,
    ano_letivo: int | None = None,
) -> list[dict[str, Any]]:
    """Lista as matrículas-turma do aluno em todas as turmas e anos.

    Cada matrícula do aluno rende uma única linha, a da alocação mais
    recente; um aluno com matrículas em anos ou turmas distintas rende uma
    linha por matrícula.

    Args:
        codigo_aluno: Código EOL do aluno.
        data_aula: Quando informada, restringe às alocações cuja situação é
            anterior ou igual a essa data.
        ano_letivo: Quando informado, restringe às alocações cuja turma
            pertence a esse ano letivo.

    Returns:
        Uma linha por matrícula do aluno conforme os filtros informados.
    """
    matriculas_idx = {
        m["codigo_matricula"]: m
        for m in Matricula.objects.filter(aluno_id=codigo_aluno).values(
            "codigo_matricula",
            "aluno_id",
            "codigo_ue",
            "codigo_dre",
            "ano_letivo",
            "data_situacao_matricula_data_hora",
        )
    }
    if not matriculas_idx:
        return []

    filtros: dict[str, Any] = {"codigo_matricula__in": list(matriculas_idx)}
    if data_aula is not None:
        filtros["data_situacao_aluno_data_hora__lte"] = fim_do_dia(data_aula)
    if ano_letivo is not None:
        filtros["ano_letivo_turma"] = ano_letivo

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

    rows = [{**matriculas_idx[mt["codigo_matricula"]], **mt} for mt in mts]
    primeiras_alocacoes = _primeira_alocacao_por_matricula(
        [r["codigo_matricula"] for r in rows]
    )

    por_matricula: dict[int, dict[str, Any]] = {}
    for row in rows:
        atual = por_matricula.get(row["codigo_matricula"])
        if atual is None or _chave_dedup_matricula(
            row, primeiras_alocacoes
        ) > _chave_dedup_matricula(atual, primeiras_alocacoes):
            por_matricula[row["codigo_matricula"]] = row

    finais = list(por_matricula.values())
    codigos_alunos = [r["aluno_id"] for r in finais]
    alunos_idx = alunos_indexados(codigos_alunos)
    responsaveis_idx = responsaveis_por_aluno(codigos_alunos)
    return [
        _montar_aluno_matricula_turma(
            r, alunos_idx, responsaveis_idx, primeiras_alocacoes
        )
        for r in finais
    ]
