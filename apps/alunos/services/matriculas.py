"""Services de matrículas e consolidações."""

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from django.db.models import Count, Min

from apps.alunos import repositories
from apps.alunos.enums import SITUACOES_MATRICULA_VALIDAS
from apps.alunos.models import (
    Aluno,
    Matricula,
    MatriculaAnoAnterior,
    MatriculaTurma,
)
from apps.core.utils import fim_do_dia

_TIPO_TURNO_DESCRICAO: dict[int, str] = {
    1: "Manhã",
    2: "Intermediário",
    3: "Tarde",
    4: "Vespertino",
    5: "Noite",
    6: "Integral",
}


def _consolidacao_por_turma(
    ano_letivo: int, ue_codigo: str
) -> list[dict[str, Any]]:
    """Conta matrículas válidas por turma.
    
    Args:
        ano_letivo: Ano letivo a filtrar.
        ue_codigo: Código da unidade escolar.
    
    Returns:
        Lista de dicionários com codigo_turma e quantidade.
    """
    qs = Matricula.objects.filter(
        ano_letivo=ano_letivo,
        codigo_ue=ue_codigo,
        codigo_situacao_matricula=1,  # Apenas matrículas ativas
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


def _codigo_escola_legado(codigo_ue: str) -> str:
    """Formata o código EOL da escola no padrão legado.

    Args:
        codigo_ue: Código da unidade escolar.

    Returns:
        Código com zero à esquerda até 6 dígitos quando numérico.
    """
    if codigo_ue.isdigit() and len(codigo_ue) < 6:
        return codigo_ue.zfill(6)
    return codigo_ue


def _codigo_ue_canonico(codigo_ue: Any) -> str:
    """Normaliza códigos de UE para comparação interna.

    Args:
        codigo_ue: Código da unidade escolar em formato variável.

    Returns:
        Código normalizado sem zeros à esquerda quando numérico.
    """
    valor = str(codigo_ue or "").strip()
    if not valor:
        return ""
    if valor.isdigit():
        return str(int(valor))
    return valor


def _ultimas_alocacoes_por_matricula(
    codigos_matricula: list[int],
) -> dict[int, dict[str, Any]]:
    """Retorna a última alocação válida por matrícula.

    Args:
        codigos_matricula: Códigos de matrícula elegíveis no recorte.

    Returns:
        Mapa ``codigo_matricula -> dados da última alocação``.
    """
    if not codigos_matricula:
        return {}

    rows = (
        MatriculaTurma.objects.filter(
            codigo_matricula__in=codigos_matricula,
            codigo_situacao_aluno__in=SITUACOES_MATRICULA_VALIDAS,
            tipo_turno__isnull=False,
        )
        .values(
            "id",
            "codigo_matricula",
            "tipo_turno",
            "codigo_ue_turma",
            "data_situacao_aluno_data_hora",
            "sequencia",
        )
        .order_by(
            "codigo_matricula",
            "-data_situacao_aluno_data_hora",
            "-sequencia",
            "-id",
        )
    )

    ultima_por_matricula: dict[int, dict[str, Any]] = {}
    for row in rows:
        codigo = int(row["codigo_matricula"])
        if codigo in ultima_por_matricula:
            continue
        ultima_por_matricula[codigo] = row
    return ultima_por_matricula


def _turnos_por_matriculas(
    codigos_matricula: list[int],
) -> list[dict[str, Any]]:
    """Agrupa matrículas por turno usando a última alocação válida.

    Args:
        codigos_matricula: Códigos de matrícula elegíveis no recorte.

    Returns:
        Lista de turnos no contrato legado.
    """
    ultima_por_matricula = _ultimas_alocacoes_por_matricula(codigos_matricula)
    if not ultima_por_matricula:
        return []

    contagem: dict[int, int] = {}
    for row in ultima_por_matricula.values():
        tipo_turno = int(row["tipo_turno"])
        contagem[tipo_turno] = contagem.get(tipo_turno, 0) + 1

    turnos = [
        {
            "turno": _TIPO_TURNO_DESCRICAO.get(tipo_turno, str(tipo_turno)),
            "tipoTurno": tipo_turno,
            "quantidade": quantidade,
        }
        for tipo_turno, quantidade in sorted(contagem.items())
    ]
    return turnos


def _matriculas_ativas_ultimo_ano_ue(ue_codigo: str) -> dict[str, Any]:
    """Retorna matrículas ativas da UE no último ano letivo disponível.

    Args:
        ue_codigo: Código da unidade educacional.

    Returns:
        Dicionário com:
        - codigos_matricula: lista de códigos de matrícula
        - matricula_para_aluno: mapa codigo_matricula -> codigo_aluno
    """
    ultimo_ano = (
        Matricula.objects.filter(codigo_ue=ue_codigo)
        .order_by("-ano_letivo")
        .values_list("ano_letivo", flat=True)
        .first()
    )
    if ultimo_ano is None:
        return {"codigos_matricula": [], "matricula_para_aluno": {}}
    
    rows = list(
        Matricula.objects.filter(
            codigo_ue=ue_codigo,
            ano_letivo=ultimo_ano,
            codigo_situacao_matricula=1,
        )
        .values("codigo_matricula", "aluno_id")
        .distinct()
    )
    
    codigos_matricula = [int(row["codigo_matricula"]) for row in rows]
    matricula_para_aluno = {
        int(row["codigo_matricula"]): int(row["aluno_id"]) for row in rows
    }
    
    return {
        "codigos_matricula": codigos_matricula,
        "matricula_para_aluno": matricula_para_aluno,
    }


def _matriculas_ativas_ultimo_ano_dre(dre_codigo: str) -> dict[str, Any]:
    """Retorna matrículas ativas da DRE no último ano letivo disponível.

    Args:
        dre_codigo: Código da DRE.

    Returns:
        Dicionário com:
        - rows: lista de dicionários com codigo_ue, codigo_matricula, aluno_id
        - matricula_para_aluno: mapa codigo_matricula -> codigo_aluno
    """
    ultimo_ano = (
        Matricula.objects.filter(codigo_dre=dre_codigo)
        .order_by("-ano_letivo")
        .values_list("ano_letivo", flat=True)
        .first()
    )
    if ultimo_ano is None:
        return {"rows": [], "matricula_para_aluno": {}}
    
    rows = list(
        Matricula.objects.filter(
            codigo_dre=dre_codigo,
            ano_letivo=ultimo_ano,
            codigo_situacao_matricula=1,
        )
        .values("codigo_ue", "codigo_matricula", "aluno_id")
    )
    
    matricula_para_aluno = {
        int(row["codigo_matricula"]): int(row["aluno_id"]) for row in rows
    }
    
    return {
        "rows": rows,
        "matricula_para_aluno": matricula_para_aluno,
    }


def obter_total_matriculas_por_turno_ue(ue_codigo: str) -> dict[str, Any]:
    """Retorna total de alunos únicos por turno da UE.

    Args:
        ue_codigo: Código da unidade educacional.

    Returns:
        Objeto do contrato legado M03 com total e turnos.
        Retorna dicionário vazio quando não houver dados.
    """
    dados = _matriculas_ativas_ultimo_ano_ue(ue_codigo)
    codigos_matricula = dados["codigos_matricula"]
    matricula_para_aluno = dados["matricula_para_aluno"]
    
    alocacoes = _ultimas_alocacoes_por_matricula(codigos_matricula)

    ue_canonico = _codigo_ue_canonico(ue_codigo)
    # Usar sets para contar alunos únicos por turno
    alunos_por_turno: dict[int, set[int]] = {}
    
    for codigo_matricula, row in alocacoes.items():
        ue_turma = _codigo_ue_canonico(row.get("codigo_ue_turma"))
        if ue_turma and ue_turma != ue_canonico:
            continue
        
        codigo_aluno = matricula_para_aluno.get(codigo_matricula)
        if not codigo_aluno:
            continue
        
        tipo_turno = int(row["tipo_turno"])
        if tipo_turno not in alunos_por_turno:
            alunos_por_turno[tipo_turno] = set()
        alunos_por_turno[tipo_turno].add(codigo_aluno)

    if not alunos_por_turno:
        return {}

    turnos = [
        {
            "turno": _TIPO_TURNO_DESCRICAO.get(tipo_turno, str(tipo_turno)),
            "tipoTurno": tipo_turno,
            "quantidade": len(alunos),  # Conta alunos únicos por turno
        }
        for tipo_turno, alunos in sorted(alunos_por_turno.items())
    ]
    if not turnos:
        return {}
    return {
        "totalMatricula": sum(item["quantidade"] for item in turnos),
        "turnos": turnos,
    }


def obter_total_matriculas_por_turno_dre(dre_codigo: str) -> list[dict[str, Any]]:
    """Retorna total de alunos únicos por turno da DRE.

    Args:
        dre_codigo: Código da DRE.

    Returns:
        Lista do contrato legado M04 com totais por escola e turno.
    """
    dados = _matriculas_ativas_ultimo_ano_dre(dre_codigo)
    rows = dados["rows"]
    matricula_para_aluno = dados["matricula_para_aluno"]
    
    if not rows:
        return []

    codigo_ue_por_matricula: dict[int, str] = {}
    codigos_matricula: list[int] = []
    for row in rows:
        codigo_matricula = int(row["codigo_matricula"])
        codigos_matricula.append(codigo_matricula)
        codigo_ue_por_matricula[codigo_matricula] = _codigo_ue_canonico(
            row["codigo_ue"]
        )

    alocacoes = _ultimas_alocacoes_por_matricula(codigos_matricula)
    # Usar sets para contar alunos únicos por escola e turno
    por_escola_turno: dict[str, dict[int, set[int]]] = {}
    
    for codigo_matricula, row in alocacoes.items():
        codigo_ue = _codigo_ue_canonico(row.get("codigo_ue_turma")) or codigo_ue_por_matricula.get(
            codigo_matricula,
            "",
        )
        if not codigo_ue:
            continue
        
        codigo_aluno = matricula_para_aluno.get(codigo_matricula)
        if not codigo_aluno:
            continue

        tipo_turno = int(row["tipo_turno"])
        por_turno = por_escola_turno.setdefault(codigo_ue, {})
        if tipo_turno not in por_turno:
            por_turno[tipo_turno] = set()
        por_turno[tipo_turno].add(codigo_aluno)

    resposta: list[dict[str, Any]] = []
    # Ordenar numericamente pelo código da escola (sem zeros à esquerda)
    for codigo_ue in sorted(por_escola_turno, key=lambda x: int(x) if x.isdigit() else 0):
        turnos = [
            {
                "turno": _TIPO_TURNO_DESCRICAO.get(tipo_turno, str(tipo_turno)),
                "tipoTurno": tipo_turno,
                "quantidade": len(alunos),  # Conta alunos únicos por turno
            }
            for tipo_turno, alunos in sorted(
                por_escola_turno[codigo_ue].items()
            )
        ]
        resposta.append(
            {
                "totalMatriculas": sum(item["quantidade"] for item in turnos),
                "codigoEolEscola": codigo_ue,
                "turnos": turnos,
            }
        )
    return resposta


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
            "data_situacao_matricula_data_hora",
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
    mts = repositories.matricula_turma_por_matricula(
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


def contar_matriculas_turmas_periodo(
    codigos_turmas: Sequence[int],
    data_fim: datetime,
) -> int:
    """Conta alocações válidas nas turmas cuja matrícula começou até a data.

    A contagem é a alocação (matrícula + sequência), não o aluno
    distinto: um aluno com várias alocações válidas conta várias vezes. Só
    entram as alocações em situação regular cuja matrícula tem a primeira
    alocação com data anterior ou igual a ``data_fim``.

    Args:
        codigos_turmas: Códigos EOL das turmas consideradas.
        data_fim: Limite superior para a data de início da matrícula.

    Returns:
        Quantidade de alocações que atendem aos critérios.
    """
    if not codigos_turmas:
        return 0
    alocacoes = list(
        MatriculaTurma.objects.filter(
            codigo_turma__in=codigos_turmas,
            codigo_situacao_aluno__in=SITUACOES_MATRICULA_VALIDAS,
        ).values_list("codigo_matricula", flat=True)
    )
    if not alocacoes:
        return 0
    no_periodo = set(
        MatriculaTurma.objects.filter(codigo_matricula__in=set(alocacoes))
        .values("codigo_matricula")
        .annotate(primeira=Min("data_situacao_aluno_data_hora"))
        .filter(primeira__lte=fim_do_dia(data_fim))
        .values_list("codigo_matricula", flat=True)
    )
    return sum(1 for matricula in alocacoes if matricula in no_periodo)
