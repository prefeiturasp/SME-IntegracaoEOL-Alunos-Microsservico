"""Services de acompanhamento escolar."""
from collections.abc import Sequence
from typing import Any

from apps.alunos import repositories
from apps.alunos.models import (
    DadosAlunoAcompanhamentoEscolar,
    Matricula,
    MatriculaTurma,
    ResponsavelAluno,
)
from apps.alunos.services.alunos import _chave_dedup


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
    """Lista dados de acompanhamento escolar."""
    return repositories.dados_acompanhamento_escolar(
        codigo_ue=codigo_ue,
        ano_letivo=ano_letivo,
        turma_codigo=turma_codigo,
        codigo_aluno=codigo_aluno,
        cpf_responsavel=cpf_responsavel,
        codigo_dre=codigo_dre,
        modalidade=modalidade,
        semestre=semestre,
    )


def obter_dados_acompanhamento_escolar_contrato(
    codigo_aluno: int | None = None,
    codigo_dre: str | None = None,
    codigo_ue: str | None = None,
    cpf_responsavel: str | None = None,
) -> list[dict[str, Any]]:
    """Lista dados de acompanhamento escolar no contrato do legado."""
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

    return list(
        qs.values(
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
        )
    )


def _responsaveis_acompanhamento_por_aluno(
    codigos_alunos: Sequence[int],
) -> dict[int, dict[str, Any]]:
    """Indexa o responsável vigente por aluno para o acompanhamento escolar.

    Traz os campos de contato completos (CPF, DDD/telefone fixo) que o índice
    prioritário genérico não expõe. Quando o aluno tem mais de um responsável
    vigente, prevalece o de menor ``tipo_responsavel`` e menor código.

    Args:
        codigos_alunos: Códigos EOL dos alunos consultados.

    Returns:
        Dicionário indexado por ``aluno_id`` apenas com alunos que têm
        responsável vigente.
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
            "cpf",
            "tipo_responsavel",
            "ddd_celular",
            "numero_celular",
            "ddd_telefone_fixo",
            "nr_telefone_fixo",
        )
    ):
        saida.setdefault(resp["aluno_id"], resp)
    return saida


def _cpf_para_inteiro(cpf: str | None) -> int:
    """Transforma o CPF textual do responsável no inteiro do contrato.

    Args:
        cpf: CPF como armazenado, possivelmente ``None`` ou vazio.

    Returns:
        O CPF numérico, ou ``0`` quando ausente ou não numérico.
    """
    if not cpf:
        return 0
    try:
        return int(cpf)
    except ValueError:
        return 0


def _montar_acompanhamento_escolar(
    row: dict[str, Any],
    alunos_idx: dict[int, dict[str, Any]],
    responsaveis_idx: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    """Monta os dados de acompanhamento a partir do registro deduplicado."""
    aluno = alunos_idx.get(row["aluno_id"], {})
    resp = responsaveis_idx.get(row["aluno_id"], {})
    return {
        "numero_chamada": row["numero_chamada"] or None,
        "nome_aluno": aluno.get("nome", ""),
        "codigo_eol_aluno": row["aluno_id"],
        "cpf": _cpf_para_inteiro(resp.get("cpf")),
        "nome_responsavel": resp.get("nome"),
        "tipo_responsavel": resp.get("tipo_responsavel"),
        "ddd_celular": resp.get("ddd_celular"),
        "celular": resp.get("numero_celular"),
        "ddd_fixo": resp.get("ddd_telefone_fixo"),
        "telefone_fixo": resp.get("nr_telefone_fixo"),
        "situacao_aluno": row["codigo_situacao_aluno"],
        "data_situacao_aluno": row["data_situacao_aluno_data_hora"],
    }


def obter_acompanhamento_escolar_turma(
    codigo_turma: int,
) -> list[dict[str, Any]]:
    """Lista os alunos e responsáveis vigentes de uma turma de acompanhamento.

    Considera os vínculos vigentes e históricos da turma, restrita ao tipo de
    turma de acompanhamento (regular). Só entram alunos com responsável
    vigente; cada aluno rende uma linha, a de situação mais recente. Não há
    filtro por situação de matrícula.

    Args:
        codigo_turma: Código EOL da turma.

    Returns:
        Um registro por aluno com responsável vigente na turma.
    """
    mts = list(
        MatriculaTurma.objects.filter(
            codigo_turma=codigo_turma, codigo_tipo_turma=1
        ).values(
            "codigo_matricula",
            "numero_chamada",
            "codigo_situacao_aluno",
            "data_situacao_aluno_data_hora",
        )
    )
    if not mts:
        return []

    matriculas_idx = {
        m["codigo_matricula"]: m["aluno_id"]
        for m in Matricula.objects.filter(
            codigo_matricula__in=[mt["codigo_matricula"] for mt in mts],
        ).values("codigo_matricula", "aluno_id")
    }
    rows = [
        {**mt, "aluno_id": matriculas_idx[mt["codigo_matricula"]]}
        for mt in mts
        if mt["codigo_matricula"] in matriculas_idx
    ]
    if not rows:
        return []

    responsaveis_idx = _responsaveis_acompanhamento_por_aluno(
        list({r["aluno_id"] for r in rows})
    )
    # A junção com o responsável vigente é interna: aluno sem responsável
    # vigente não aparece.
    rows = [r for r in rows if r["aluno_id"] in responsaveis_idx]
    if not rows:
        return []

    por_aluno: dict[int, dict[str, Any]] = {}
    for row in rows:
        atual = por_aluno.get(row["aluno_id"])
        if atual is None or _chave_dedup(row) > _chave_dedup(atual):
            por_aluno[row["aluno_id"]] = row

    alunos_idx = repositories.alunos_indexados(list(por_aluno))
    return [
        _montar_acompanhamento_escolar(row, alunos_idx, responsaveis_idx)
        for row in por_aluno.values()
    ]
