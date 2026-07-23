"""Services de acompanhamento escolar."""
from typing import Any

from apps.alunos import repositories
from apps.alunos.models import DadosAlunoAcompanhamentoEscolar


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
