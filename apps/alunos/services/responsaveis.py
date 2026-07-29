"""Serviços e consultas do recorte Responsáveis."""

from collections import Counter
from datetime import date, datetime
from typing import Any, cast

from django.db import connection
from django.db.models import Q
from django.utils import timezone

from apps.alunos import repositories
from apps.alunos.models import (
    Aluno,
    Matricula,
    MatriculaTurma,
    ResponsavelAluno,
)


def alunos_indexados(codigos_alunos: list[int]) -> dict[int, dict[str, Any]]:
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
        )
    }


def colunas_responsavel_aluno() -> set[str]:
    """Lista colunas existentes na tabela de responsáveis."""
    with connection.cursor() as cursor:
        descricao = connection.introspection.get_table_description(
            cursor,
            ResponsavelAluno._meta.db_table,
        )
    return {col.name for col in descricao}


def responsaveis_do_aluno(codigo_aluno: int) -> list[dict[str, Any]]:
    """Lista responsáveis de um aluno."""
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


def responsavel_principal(codigo_aluno: int) -> dict[str, Any] | None:
    """Obtém o responsável vigente prioritário do aluno."""
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


def responsaveis_por_aluno(
    codigos_alunos: list[int],
) -> dict[int, dict[str, Any]]:
    """Indexa o responsável prioritário por aluno."""
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


def obter_dados_responsavel(cpf_responsavel: str) -> list[dict[str, Any]]:
    """Lista os vínculos de um responsável a partir do CPF."""
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

    alunos_idx = alunos_indexados([v["aluno_id"] for v in vinculos])
    return [
        {
            "responsavel": v,
            "aluno": alunos_idx.get(v["aluno_id"], {}),
        }
        for v in vinculos
    ]


def obter_dados_responsavel_contrato(
    cpf_responsavel: str,
) -> list[dict[str, Any]]:
    """Lista os dados do responsável e dos alunos vinculados.

    Args:
        cpf_responsavel: CPF do responsável consultado.

    Returns:
        Dados dos vínculos vigentes com alunos matriculados no ano corrente.
    """
    cpf = (cpf_responsavel or "").strip()
    if not cpf:
        return []

    ano_atual = timezone.localtime(timezone.now()).year
    matriculas_elegiveis = list(
        Matricula.objects.filter(
            origem_atual=True,
            codigo_situacao_matricula=1,
            ano_letivo=ano_atual,
        )
        .filter(
            Q(codigo_serie_ensino__isnull=False)
            | Q(codigo_tipo_escola__in=(22, 23))
        )
        .values("codigo_matricula", "aluno_id")
    )
    alunos_por_matricula = {
        item["codigo_matricula"]: item["aluno_id"]
        for item in matriculas_elegiveis
    }
    matriculas_turma = MatriculaTurma.objects.filter(
        codigo_matricula__in=alunos_por_matricula,
        origem_atual=True,
        codigo_situacao_aluno__in=(1, 6, 10, 13),
    ).values_list("codigo_matricula", flat=True)
    quantidade_linhas_por_aluno = Counter(
        alunos_por_matricula[codigo_matricula]
        for codigo_matricula in matriculas_turma
    )
    vinculos = (
        ResponsavelAluno.objects.filter(
            cpf=cpf,
            aluno_id__in=quantidade_linhas_por_aluno,
            data_fim_vinculo__isnull=True,
        )
        .select_related("aluno")
        .order_by("codigo_responsavel")
    )

    return [
        {
            "id": vinculo.codigo_responsavel,
            "cpf": vinculo.cpf,
            "email": vinculo.email,
            "nome": vinculo.nome,
            "tipo_responsavel": vinculo.tipo_responsavel or 0,
            "nome_social_aluno": vinculo.aluno.nome_social,
            "data_nascimento_aluno": vinculo.aluno.data_nascimento,
            "data_nascimento": vinculo.data_nascimento,
            "data_atualizacao": vinculo.data_atualizacao_tabela,
            "nome_mae": vinculo.nome_mae,
            "tipo_sigilo": vinculo.aluno.tipo_sigilo or 0,
            "ddd_celular": vinculo.ddd_celular,
            "numero_celular": vinculo.numero_celular,
            "nome_aluno": vinculo.aluno.nome,
            "codigo_aluno": str(vinculo.aluno_id),
            "numero_rg": vinculo.numero_rg,
            "digito_rg": vinculo.digito_rg,
            "uf_rg": vinculo.uf_rg,
            "cpf_confere": vinculo.cpf_confere,
            "tipo_turno_celular": vinculo.tipo_turno_celular,
            "ddd_telefone_fixo": vinculo.ddd_telefone_fixo or "",
            "numero_telefone_fixo": vinculo.nr_telefone_fixo or "",
            "tipo_turno_telefone_fixo": vinculo.tipo_turno_fixo,
            "ddd_telefone_comercial": (
                vinculo.ddd_telefone_comercial or ""
            ),
            "numero_telefone_comercial": (
                vinculo.nr_telefone_comercial or ""
            ),
            "tipo_turno_telefone_comercial": (
                vinculo.tipo_turno_comercial
            ),
            "autoriza_envio_sms": vinculo.autoriza_sms,
        }
        for vinculo in vinculos
        for _ in range(quantidade_linhas_por_aluno[vinculo.aluno_id])
    ]


def obter_responsaveis_dre_ue_turma(
    codigo_ue: str | None = None,
    ano_letivo: int | None = None,
    codigo_dre: str | None = None,
) -> list[dict[str, Any]]:
    """Lista responsáveis vigentes agrupados por UE e turma."""
    return repositories.responsaveis_dre_ue_turma(
        codigo_ue=codigo_ue,
        ano_letivo=ano_letivo,
        codigo_dre=codigo_dre,
    )


def obter_dados_responsavel_resumido(
    cpf_responsavel: str,
) -> dict[str, Any] | None:
    """Retorna dados resumidos do responsável."""
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
    colunas = colunas_responsavel_aluno()
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
    return {"responsavel": v, "codigo_aluno": None}


def atualizar_dados_responsavel_busca_ativa(
    codigo_aluno: int,
    cpf_responsavel: str,
    *,
    email: str | None = None,
    ddd_celular: str | None = None,
    numero_celular: str | None = None,
    ddd_residencial: str | None = None,
    numero_residencial: str | None = None,
    ddd_comercial: str | None = None,
    numero_comercial: str | None = None,
) -> bool:
    """Atualiza os contatos do responsável no fluxo de busca ativa.

    Args:
        codigo_aluno: Código EOL do aluno.
        cpf_responsavel: CPF do responsável atualizado.
        email: Endereço eletrônico do responsável.
        ddd_celular: DDD do telefone celular.
        numero_celular: Número do telefone celular.
        ddd_residencial: DDD do telefone residencial.
        numero_residencial: Número do telefone residencial.
        ddd_comercial: DDD do telefone comercial.
        numero_comercial: Número do telefone comercial.

    Returns:
        ``True`` quando o vínculo for atualizado.
    """
    atualizados = ResponsavelAluno.objects.filter(
        cpf=cpf_responsavel, aluno_id=codigo_aluno
    ).update(
        email=email,
        ddd_celular=ddd_celular,
        numero_celular=numero_celular,
        ddd_telefone_fixo=ddd_residencial,
        nr_telefone_fixo=numero_residencial,
        ddd_telefone_comercial=ddd_comercial,
        nr_telefone_comercial=numero_comercial,
        data_atualizacao_tabela=timezone.now(),
    )
    return atualizados > 0


def atualizar_dados_responsavel(
    codigo_aluno: int,
    cpf_responsavel: str,
    *,
    email: str | None = None,
    data_nascimento: date | datetime | None = None,
    nome_mae: str | None = None,
    ddd_celular: str | None = None,
    numero_celular: str | None = None,
) -> bool:
    """Atualiza os dados cadastrais do responsável.

    Args:
        codigo_aluno: Código EOL do aluno.
        cpf_responsavel: CPF do responsável atualizado.
        email: Endereço eletrônico do responsável.
        data_nascimento: Data de nascimento informada para o responsável.
        nome_mae: Nome da mãe do responsável.
        ddd_celular: DDD do telefone celular.
        numero_celular: Número do telefone celular.

    Returns:
        ``True`` quando o vínculo for atualizado.
    """
    if isinstance(data_nascimento, datetime):
        data_nascimento = data_nascimento.date()

    atualizados = ResponsavelAluno.objects.filter(
        cpf=cpf_responsavel, aluno_id=codigo_aluno
    ).update(
        email=email,
        data_nascimento=data_nascimento,
        nome_mae=nome_mae,
        ddd_celular=ddd_celular,
        numero_celular=numero_celular,
        cpf_confere="S",
        autoriza_sms="S",
        tipo_turno_celular=1,
        data_atualizacao_tabela=timezone.now(),
    )
    return atualizados > 0


def obter_dados_responsavel_filiacao(
    codigo_aluno: int,
) -> list[dict[str, Any]]:
    """Lista dados de filiação do aluno."""
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
        {"responsavel": responsavel}
        for responsavel in responsaveis
    ]
