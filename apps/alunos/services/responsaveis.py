"""Serviços e consultas do recorte Responsáveis."""

from typing import Any, cast

from django.db import connection
from django.db.models import Max

from apps.alunos import repositories
from apps.alunos.models import Aluno, ResponsavelAluno


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
) -> dict[str, Any]:
    """Atualiza contatos do responsável no fluxo de busca ativa."""
    resp = ResponsavelAluno.objects.filter(
        cpf=cpf_responsavel, aluno_id=codigo_aluno
    ).first()
    if resp is None:
        return {
            "responsavel": None,
            "codigo_aluno": codigo_aluno,
            "cpf": cpf_responsavel,
            "email": email,
            "ddd_celular": ddd_celular,
            "numero_celular": numero_celular,
        }

    if email is not None:
        resp.email = email
    if ddd_celular is not None:
        resp.ddd_celular = ddd_celular
    if numero_celular is not None:
        resp.numero_celular = numero_celular
    resp.save(update_fields=["email", "ddd_celular", "numero_celular"])

    return {"responsavel": resp, "codigo_aluno": codigo_aluno}


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
        resp = ResponsavelAluno(
            codigo_responsavel=max_pk + 1,
            aluno_id=codigo_aluno,
            cpf=cpf_responsavel,
            nome=nome,
            email=email,
            tipo_responsavel=tipo_responsavel,
            ddd_celular=ddd_celular,
            numero_celular=numero_celular,
        )
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

    return {"responsavel": resp, "codigo_aluno": codigo_aluno}


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
