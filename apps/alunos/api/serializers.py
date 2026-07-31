"""Serializers do domínio Alunos."""

from datetime import datetime
from typing import Any, cast

from rest_framework import serializers

from apps.alunos.constants import DATA_DEFAULT_LEGADO, MODALIDADE_POR_ETAPA
from apps.alunos.enums import SituacaoMatricula


def _valor(obj: Any, campo: str, padrao: Any = None) -> Any:
    """Obtém um campo de dict ou objeto."""
    if isinstance(obj, dict):
        return obj.get(campo, padrao)
    return getattr(obj, campo, padrao)


def _turma_do_aluno_representation(instance: dict[str, Any]) -> dict[str, Any]:
    """Representa uma linha composta de turma do aluno."""
    matricula = instance["matricula"]
    matricula_turma = instance["matricula_turma"]
    aluno = instance["aluno"]
    responsavel = instance["responsavel"]
    codigo_situacao = instance["codigo_situacao"]
    historico = instance.get("historico", False)
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
        "situacao_matricula": SituacaoMatricula.get_descricao(
            codigo_situacao
        ),
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
        "data_atualizacao_contato": responsavel.get(
            "data_atualizacao_tabela"
        ),
        "nome_responsavel": responsavel.get("nome"),
        "tipo_responsavel": responsavel.get("tipo_responsavel"),
        "ddd_celular": responsavel.get("ddd_celular"),
        "numero_celular": responsavel.get("numero_celular"),
        "codigo_escola": matricula["codigo_ue"],
        "codigo_tipo_turma": matricula_turma.get("codigo_tipo_turma"),
        "data_atualizacao_tabela": DATA_DEFAULT_LEGADO
        if historico
        else matricula_turma.get("data_atualizacao_tabela") or data_situacao,
    }


def _aluno_da_ue_representation(instance: dict[str, Any]) -> dict[str, Any]:
    """Representa uma linha composta de aluno da UE."""
    matricula = instance["matricula"]
    matricula_turma = instance["matricula_turma"]
    aluno = instance["aluno"]
    ano_letivo = instance["ano_letivo"]
    codigo_situacao = matricula_turma.get("codigo_situacao_aluno")
    return {
        "codigo_aluno": matricula["aluno_id"],
        "tipo_turno": matricula_turma.get("tipo_turno"),
        "ano_letivo": matricula_turma.get("ano_letivo_turma") or ano_letivo,
        "nome_aluno": aluno.get("nome", ""),
        "nome_social_aluno": aluno.get("nome_social"),
        "codigo_situacao_matricula": codigo_situacao or 0,
        "situacao_matricula": SituacaoMatricula.get_descricao(
            codigo_situacao
        ),
        "data_situacao": (
            matricula_turma.get("data_situacao_aluno_data_hora")
            or matricula_turma.get("data_situacao_aluno")
        ),
        "data_nascimento": aluno.get("data_nascimento"),
        "numero_aluno_chamada": matricula_turma.get("numero_chamada") or "0",
        "codigo_turma": matricula_turma["codigo_turma"],
        "data_atualizacao_contato": DATA_DEFAULT_LEGADO,
        "codigo_tipo_turma": matricula_turma.get("codigo_tipo_turma"),
        "turma_nome": matricula_turma.get("nome_turma"),
        "etapa_ensino": matricula_turma.get("codigo_etapa_ensino"),
        "ciclo_ensino": matricula_turma.get("codigo_ciclo_ensino"),
        "desc_etapa_ensino": matricula_turma.get("descricao_etapa_ensino"),
        "desc_ciclo_ensino": matricula_turma.get("descricao_ciclo_ensino"),
        "data_atualizacao_tabela": DATA_DEFAULT_LEGADO,
    }


def _autocomplete_representation(instance: dict[str, Any]) -> dict[str, Any]:
    """Representa uma linha composta de autocomplete."""
    matricula = instance["matricula"]
    matricula_turma = instance["matricula_turma"]
    aluno = instance.get("aluno") or {}
    nome = aluno.get("nome") or matricula.get("aluno__nome") or ""
    return {
        "codigo_aluno": matricula["aluno_id"],
        "nome_aluno": nome,
        "nome_social_aluno": (
            aluno.get("nome_social")
            if aluno
            else matricula.get("aluno__nome_social")
        ),
        "codigo_turma": matricula_turma.get("codigo_turma") or 0,
        "numero_aluno_chamada": matricula_turma.get("numero_chamada"),
        "turma": matricula_turma.get("nome_turma"),
        "modalidade": MODALIDADE_POR_ETAPA.get(
            matricula_turma.get("codigo_etapa_ensino")
        ),
    }


def _aluno_ativo_turma_representation(
    instance: dict[str, Any],
) -> dict[str, Any]:
    """Representa uma linha composta de aluno ativo da turma."""
    linha = instance["linha"]
    aluno = instance["aluno"]
    codigo_situacao = linha["codigo_situacao_aluno"]
    return {
        "codigo_aluno": linha["aluno_id"],
        "nome_aluno": aluno.get("nome", ""),
        "nome_social_aluno": aluno.get("nome_social"),
        "data_nascimento": aluno.get("data_nascimento"),
        "codigo_situacao_matricula": codigo_situacao,
        "situacao_matricula": SituacaoMatricula.get_descricao(
            codigo_situacao
        ),
        "data_situacao": linha["data_situacao_aluno_data_hora"],
        "numero_aluno_chamada": linha["numero_chamada"],
        "possui_deficiencia": aluno.get("possui_deficiencia", False),
        "codigo_matricula": linha["codigo_matricula"],
        "codigo_turma": linha["codigo_turma"],
        "codigo_escola": linha["codigo_ue"],
        "ano_letivo": linha["ano_letivo"],
    }


def _aluno_ativo_data_aula_representation(
    instance: dict[str, Any],
) -> dict[str, Any]:
    """Representa uma linha composta de aluno ativo por data de aula."""
    linha = instance["linha"]
    aluno = instance["aluno"]
    responsavel = instance.get("responsavel") or {}
    celular = None
    if responsavel.get("ddd_celular") or responsavel.get("numero_celular"):
        celular = f"{responsavel.get('ddd_celular') or ''}" + (
            responsavel.get("numero_celular") or ""
        )
    saida = _aluno_ativo_turma_representation(instance)
    saida.update(
        {
            "data_matricula": instance.get("primeira_alocacao"),
            "nome_responsavel": responsavel.get("nome"),
            "tipo_responsavel": responsavel.get("tipo_responsavel"),
            "celular_responsavel": celular,
            "data_atualizacao_contato": aluno.get("data_atualizacao_contato"),
            "sequencia": linha["sequencia"],
            "codigo_dre": linha["codigo_dre"],
        }
    )
    return saida


def _necessidade_especial_representation(
    instance: dict[str, Any],
) -> dict[str, Any]:
    """Representa uma necessidade especial de aluno."""
    necessidade = instance["necessidade"]
    return {
        "codigo_aluno": necessidade["aluno_id"],
        "tipo_necessidade_especial": necessidade["necessidade_especial_id"],
        "descricao_necessidade_especial": instance.get(
            "descricao_necessidade_especial", ""
        ),
        "tipo_recurso": necessidade.get("codigo_tipo_recurso"),
        "descricao_recurso": necessidade.get("descricao_tipo_recurso"),
    }


def _informacoes_aluno_representation(
    instance: dict[str, Any],
) -> dict[str, Any]:
    """Representa informações cadastrais de aluno."""
    aluno = instance["aluno"]
    responsavel = instance.get("responsavel")
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
        "endereco": _endereco_responsavel_representation(responsavel),
        "data_nascimento": aluno.data_nascimento,
        "possui_deficiencia": aluno.possui_deficiencia,
    }


def _informacoes_aluno_turma_representation(
    instance: dict[str, Any],
) -> dict[str, Any]:
    """Representa resumo de aluno em turma."""
    row = instance["row"]
    aluno = instance["aluno"]
    raca = aluno.get("raca_cor")
    return {
        "numero_aluno_chamada": row["numero_chamada"],
        "numero_chamada": instance.get("numero_chamada"),
        "codigo_aluno": row["aluno_id"],
        "nome_aluno": aluno.get("nome", ""),
        "nome_social_aluno": aluno.get("nome_social"),
        "sexo": aluno.get("sexo"),
        "raca_cor": raca,
        "raca": raca,
        "codigo_raca": instance.get("codigo_raca"),
    }


def _dados_responsavel_representation(
    instance: dict[str, Any],
) -> dict[str, Any]:
    """Representa dados completos do responsável."""
    responsavel = instance["responsavel"]
    aluno = instance["aluno"]
    return {
        "codigo_responsavel": responsavel["codigo_responsavel"],
        "cpf": responsavel["cpf"],
        "email": responsavel["email"],
        "nome": responsavel["nome"],
        "tipo_responsavel": responsavel["tipo_responsavel"],
        "nome_aluno": aluno.get("nome", ""),
        "nome_social_aluno": aluno.get("nome_social"),
        "data_nascimento_aluno": aluno.get("data_nascimento"),
        "codigo_aluno": str(responsavel["aluno_id"]),
        "ddd_celular": responsavel["ddd_celular"],
        "numero_celular": responsavel["numero_celular"],
        "autoriza_sms": responsavel["autoriza_sms"],
        "logradouro": responsavel["logradouro"],
        "cep": responsavel["cep"],
        "data_fim_vinculo": responsavel["data_fim_vinculo"],
    }


def _endereco_responsavel_representation(
    responsavel: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Representa o endereço do responsável."""
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


def _dados_responsavel_resumido_representation(
    instance: dict[str, Any],
) -> dict[str, Any]:
    """Representa dados resumidos do responsável."""
    responsavel = instance.get("responsavel")
    if responsavel is None:
        return {
            "id": 0,
            "cpf": instance.get("cpf"),
            "email": instance.get("email"),
            "nome": None,
            "tipo_responsavel": None,
            "data_nascimento": None,
            "data_atualizacao": None,
            "nome_mae": None,
            "ddd_celular": instance.get("ddd_celular"),
            "numero_celular": instance.get("numero_celular"),
            "codigo_aluno": str(instance.get("codigo_aluno")),
        }
    return {
        "id": _valor(responsavel, "codigo_responsavel"),
        "cpf": _valor(responsavel, "cpf"),
        "email": _valor(responsavel, "email"),
        "nome": _valor(responsavel, "nome"),
        "tipo_responsavel": _valor(responsavel, "tipo_responsavel"),
        "data_nascimento": _valor(responsavel, "data_nascimento"),
        "data_atualizacao": _valor(responsavel, "data_atualizacao_tabela"),
        "nome_mae": _valor(responsavel, "nome_mae"),
        "ddd_celular": _valor(responsavel, "ddd_celular"),
        "numero_celular": _valor(responsavel, "numero_celular"),
        "codigo_aluno": (
            str(instance["codigo_aluno"])
            if instance.get("codigo_aluno") is not None
            else None
        ),
    }


def _dados_responsavel_filiacao_representation(
    instance: dict[str, Any],
) -> dict[str, Any]:
    """Representa dados de filiação do responsável."""
    responsavel = instance["responsavel"]
    return {
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


def _quantidade_cc_contrato_representation(
    instance: dict[str, Any],
) -> dict[str, Any]:
    """Representa quantidade por componente no contrato legado."""
    return {
        "componente_curricular_id": instance["componente_curricular_id"],
        "quantidade": instance["quantidade"],
        "ordem": instance["ordem"] or 0,
        "modalidade": instance["modalidade"],
        "ano": instance["ano"],
        "turma": instance["turma"],
    }


def _quantidade_contrato_representation(
    instance: dict[str, Any],
) -> dict[str, Any]:
    """Representa quantidade de matriculados no contrato legado."""
    return {
        "quantidade": instance["quantidade"],
        "ordem": instance["ordem"],
        "modalidade": instance["modalidade"],
        "ano": instance["ano"],
        "turma": instance["turma"],
        "dre_codigo": instance["codigo_dre"],
        "ue_codigo": instance["codigo_ue"],
    }


def _consolidacao_matricula_representation(
    instance: dict[str, Any],
) -> dict[str, Any]:
    """Representa consolidação de matrícula por turma."""
    return {
        "turma_codigo": str(instance["codigo_turma"]),
        "quantidade": instance["quantidade"],
    }


def _matricula_escola_aluno_representation(
    instance: dict[str, Any],
) -> dict[str, Any]:
    """Representa matrícula do aluno em uma escola."""
    matricula = instance["matricula"]
    aluno = instance["aluno"]
    matricula_turma = instance["matricula_turma"]
    data_situacao = (
        matricula.get("data_situacao_matricula_data_hora")
        or matricula["data_situacao_matricula"]
    )
    return {
        "codigo_aluno": matricula["aluno_id"],
        "nome_aluno": aluno.get("nome", ""),
        "nome_social_aluno": aluno.get("nome_social"),
        "codigo_situacao_matricula": matricula["codigo_situacao_matricula"],
        "situacao_matricula": matricula["situacao_matricula"],
        "data_situacao": data_situacao,
        "codigo_turma": matricula_turma.get("codigo_turma") or 0,
        "codigo_matricula": matricula["codigo_matricula"],
        "ano_letivo": matricula["ano_letivo"],
    }


def _acompanhamento_contrato_representation(
    instance: dict[str, Any],
) -> dict[str, Any]:
    """Representa dados de acompanhamento no contrato legado."""
    data_situacao = instance["data_situacao_matricula_data_hora"]
    if data_situacao is None and instance["data_situacao_matricula"]:
        data_situacao = datetime.combine(
            instance["data_situacao_matricula"], datetime.min.time()
        )
    return {
        "codigo_eol": instance["codigo_aluno"],
        "nome_responsavel": instance["nome_responsavel"],
        "cpf_responsavel": instance["cpf_responsavel"],
        "nome": instance["nome"],
        "nome_social": instance["nome_social"],
        "codigo_escola": instance["codigo_ue"],
        "codigo_dre": instance["codigo_dre"],
        "escola": instance["unidade_educacional"],
        "tipo_responsavel": instance["tipo_responsavel"],
        "codigo_tipo_escola": instance["codigo_tipo_escola"],
        "descricao_tipo_escola": instance["descricao_tipo_escola"],
        "sigla_dre": instance["sigla_dre"],
        "codigo_turma": instance["codigo_turma"],
        "turma": instance["turma"],
        "situacao_matricula": instance["situacao_matricula"],
        "data_nascimento": instance["data_nascimento"],
        "data_situacao_matricula": data_situacao,
        "codigo_ciclo_ensino": instance["codigo_ciclo_ensino"],
        "codigo_etapa_ensino": instance["codigo_etapa_ensino"],
        "serie_resumida": instance["serie_resumida"],
    }


class TurmaDoAlunoSerializer(serializers.Serializer):
    """Serializa turmas do aluno."""

    codigo_aluno = serializers.IntegerField()
    ano_letivo = serializers.IntegerField()
    nome_aluno = serializers.CharField()
    nome_social_aluno = serializers.CharField(allow_null=True)
    codigo_situacao_matricula = serializers.IntegerField()
    situacao_matricula = serializers.CharField()
    data_situacao = serializers.CharField(allow_null=True)
    data_nascimento = serializers.DateField(allow_null=True)
    documento_cpf = serializers.CharField(allow_null=True)
    data_matricula = serializers.CharField(allow_null=True)
    numero_aluno_chamada = serializers.CharField(allow_null=True)
    codigo_turma = serializers.IntegerField()
    data_atualizacao_contato = serializers.SerializerMethodField()

    def to_representation(self, instance: Any) -> dict[str, Any]:
        """Serializa linha composta retornada pelo service."""
        if isinstance(instance, dict) and "matricula" in instance:
            instance = _turma_do_aluno_representation(instance)
        return cast(dict[str, Any], super().to_representation(instance))

    def get_data_atualizacao_contato(self, obj: Any) -> str:
        """Retorna data de atualização de contato formatada.

        Returns:
            Data no formato ISO-8601 ou '0001-01-01T00:00:00' quando ausente.
        """
        val = _valor(obj, "data_atualizacao_contato")
        if val is None:
            return "0001-01-01T00:00:00"
        if hasattr(val, "isoformat"):
            return cast(str, val.isoformat())
        return str(val)

    nome_responsavel = serializers.CharField(allow_null=True)
    tipo_responsavel = serializers.IntegerField(allow_null=True)
    ddd_celular = serializers.CharField(allow_null=True)
    numero_celular = serializers.CharField(allow_null=True)
    codigo_escola = serializers.CharField(allow_null=True)
    codigo_tipo_turma = serializers.IntegerField(allow_null=True)
    data_atualizacao_tabela = serializers.CharField(allow_null=True)


class AlunoDaUeSerializer(serializers.Serializer):
    """Serializa dados de aluno matriculado em uma unidade educacional."""

    codigo_aluno = serializers.IntegerField()
    tipo_turno = serializers.IntegerField(allow_null=True)
    ano_letivo = serializers.IntegerField()
    nome_aluno = serializers.CharField()
    nome_social_aluno = serializers.CharField(allow_null=True)
    codigo_situacao_matricula = serializers.IntegerField()
    situacao_matricula = serializers.CharField()
    data_situacao = serializers.CharField(allow_null=True)
    data_nascimento = serializers.DateField(allow_null=True)
    numero_aluno_chamada = serializers.CharField(allow_null=True)
    codigo_turma = serializers.IntegerField()
    nome_responsavel = serializers.CharField(allow_null=True)
    tipo_responsavel = serializers.IntegerField(allow_null=True)
    ddd_celular = serializers.CharField(allow_null=True)
    numero_celular = serializers.CharField(allow_null=True)
    data_atualizacao_contato = serializers.DateTimeField(allow_null=True)
    codigo_tipo_turma = serializers.IntegerField(allow_null=True)
    turma_nome = serializers.CharField(allow_null=True)
    etapa_ensino = serializers.IntegerField(allow_null=True)
    ciclo_ensino = serializers.IntegerField(allow_null=True)
    desc_etapa_ensino = serializers.CharField(allow_null=True)
    desc_ciclo_ensino = serializers.CharField(allow_null=True)
    data_atualizacao_tabela = serializers.DateTimeField(allow_null=True)

    def to_representation(self, instance: Any) -> dict[str, Any]:
        """Serializa linha composta retornada pelo service."""
        if isinstance(instance, dict) and "matricula" in instance:
            instance = _aluno_da_ue_representation(instance)
        return cast(dict[str, Any], super().to_representation(instance))


class AlunoAutocompleteSerializer(serializers.Serializer):
    """Serializa dados de autocomplete de aluno."""

    codigo_aluno = serializers.IntegerField()
    nome_aluno = serializers.CharField()
    nome_social_aluno = serializers.CharField(allow_null=True)
    codigo_turma = serializers.IntegerField()
    numero_aluno_chamada = serializers.CharField(allow_null=True)
    turma = serializers.CharField(allow_null=True)
    modalidade = serializers.CharField(allow_null=True)

    def to_representation(self, instance: Any) -> dict[str, Any]:
        """Serializa linha composta retornada pelo service."""
        if isinstance(instance, dict) and "matricula" in instance:
            instance = _autocomplete_representation(instance)
        return cast(dict[str, Any], super().to_representation(instance))


class AlunoAtivoTurmaSerializer(serializers.Serializer):
    """Serializa alunos ativos em uma turma."""

    codigo_aluno = serializers.IntegerField()
    nome_aluno = serializers.CharField()
    nome_social_aluno = serializers.CharField(allow_null=True)
    data_nascimento = serializers.DateField(allow_null=True)
    codigo_situacao_matricula = serializers.IntegerField()
    situacao_matricula = serializers.CharField()
    data_situacao = serializers.DateTimeField(allow_null=True)
    numero_aluno_chamada = serializers.CharField(allow_null=True)
    possui_deficiencia = serializers.BooleanField()
    codigo_matricula = serializers.IntegerField()
    codigo_turma = serializers.IntegerField()
    codigo_escola = serializers.CharField()
    ano_letivo = serializers.IntegerField()

    def to_representation(self, instance: Any) -> dict[str, Any]:
        """Serializa linha composta retornada pelo service."""
        if isinstance(instance, dict) and "linha" in instance:
            instance = _aluno_ativo_turma_representation(instance)
        return cast(dict[str, Any], super().to_representation(instance))


class AlunoAtivoDataAulaSerializer(serializers.Serializer):
    """Serializa alunos ativos na turma por data de aula."""

    codigo_aluno = serializers.IntegerField()
    nome_aluno = serializers.CharField()
    nome_social_aluno = serializers.CharField(allow_null=True)
    data_nascimento = serializers.DateField(allow_null=True)
    codigo_situacao_matricula = serializers.IntegerField()
    situacao_matricula = serializers.CharField()
    data_situacao = serializers.DateTimeField(allow_null=True)
    numero_aluno_chamada = serializers.CharField(allow_null=True)
    possui_deficiencia = serializers.BooleanField()
    codigo_matricula = serializers.IntegerField()
    codigo_turma = serializers.IntegerField()
    codigo_escola = serializers.CharField()
    ano_letivo = serializers.IntegerField()
    data_matricula = serializers.DateTimeField(allow_null=True)
    nome_responsavel = serializers.CharField(allow_null=True)
    tipo_responsavel = serializers.IntegerField(allow_null=True)
    celular_responsavel = serializers.CharField(allow_null=True)
    data_atualizacao_contato = serializers.DateTimeField(allow_null=True)
    sequencia = serializers.IntegerField(allow_null=True)
    codigo_dre = serializers.CharField()

    def to_representation(self, instance: Any) -> dict[str, Any]:
        """Serializa linha composta retornada pelo service."""
        if isinstance(instance, dict) and "linha" in instance:
            instance = _aluno_ativo_data_aula_representation(instance)
        return cast(dict[str, Any], super().to_representation(instance))


class AlunoAcompanhamentoEscolarSerializer(serializers.Serializer):
    """Serializa alunos e responsáveis para acompanhamento escolar."""

    numero_chamada = serializers.CharField(allow_null=True)
    nome_aluno = serializers.CharField()
    codigo_eol_aluno = serializers.IntegerField()
    cpf = serializers.IntegerField()
    nome_responsavel = serializers.CharField(allow_null=True)
    tipo_responsavel = serializers.IntegerField(allow_null=True)
    ddd_celular = serializers.CharField(allow_null=True)
    celular = serializers.CharField(allow_null=True)
    ddd_fixo = serializers.CharField(allow_null=True)
    telefone_fixo = serializers.CharField(allow_null=True)
    situacao_aluno = serializers.IntegerField(allow_null=True)
    data_situacao_aluno = serializers.DateTimeField(allow_null=True)


class NecessidadeEspecialSerializer(serializers.Serializer):
    """Serializa necessidades especiais do aluno."""

    codigo_aluno = serializers.IntegerField()
    tipo_necessidade_especial = serializers.IntegerField()
    descricao_necessidade_especial = serializers.CharField()
    tipo_recurso = serializers.IntegerField(allow_null=True)
    descricao_recurso = serializers.CharField(allow_null=True)

    def to_representation(self, instance: Any) -> dict[str, Any]:
        """Serializa linha composta retornada pelo service."""
        if isinstance(instance, dict) and "necessidade" in instance:
            instance = _necessidade_especial_representation(instance)
        return cast(dict[str, Any], super().to_representation(instance))


class InformacoesAlunoSerializer(serializers.Serializer):
    """Serializa informações do aluno."""

    codigo_aluno = serializers.IntegerField()
    nome_aluno = serializers.CharField()
    nome_social_aluno = serializers.CharField(allow_null=True)
    nome_mae = serializers.CharField(allow_null=True)
    sexo = serializers.CharField(allow_null=True)
    nacionalidade = serializers.CharField(allow_null=True)
    raca_cor = serializers.CharField(allow_null=True)
    nis = serializers.CharField(allow_null=True)
    cpf = serializers.CharField(allow_null=True)
    cns = serializers.CharField(allow_null=True)
    endereco = serializers.DictField(allow_null=True)
    data_nascimento = serializers.DateField(allow_null=True)
    possui_deficiencia = serializers.BooleanField()

    def to_representation(self, instance: Any) -> dict[str, Any]:
        """Serializa linha composta retornada pelo service."""
        if isinstance(instance, dict) and "aluno" in instance:
            instance = _informacoes_aluno_representation(instance)
        return cast(dict[str, Any], super().to_representation(instance))


class InformacoesAlunoTurmaSerializer(serializers.Serializer):
    """Serializa resumo de aluno em turma."""

    numero_aluno_chamada = serializers.CharField(allow_null=True)
    numero_chamada = serializers.IntegerField(allow_null=True)
    codigo_aluno = serializers.IntegerField()
    nome_aluno = serializers.CharField()
    nome_social_aluno = serializers.CharField(allow_null=True)
    sexo = serializers.CharField(allow_null=True)
    raca_cor = serializers.CharField(allow_null=True)
    raca = serializers.CharField(allow_null=True)
    codigo_raca = serializers.IntegerField(allow_null=True)

    def to_representation(self, instance: Any) -> dict[str, Any]:
        """Serializa linha composta retornada pelo service."""
        if isinstance(instance, dict) and "row" in instance:
            instance = _informacoes_aluno_turma_representation(instance)
        return cast(dict[str, Any], super().to_representation(instance))


class QuantidadeMatriculadosCCSerializer(serializers.Serializer):
    """Serializa quantidade de matriculados por turma."""

    codigo_turma = serializers.IntegerField()
    quantidade = serializers.IntegerField()
    ordem = serializers.IntegerField()


class QuantidadeMatriculadosSerializer(serializers.Serializer):
    """Serializa quantidade de matriculados por UE/turma."""

    quantidade = serializers.IntegerField()
    ordem = serializers.IntegerField()
    codigo_turma = serializers.IntegerField()
    ue_codigo = serializers.CharField()


class DadosAcompanhamentoEscolarSerializer(serializers.Serializer):
    """Serializa dados de acompanhamento escolar."""

    codigo_eol = serializers.IntegerField()
    nome_responsavel = serializers.CharField(allow_null=True)
    cpf_responsavel = serializers.CharField(allow_null=True)
    nome = serializers.CharField()
    nome_social = serializers.CharField(allow_null=True)
    codigo_escola = serializers.CharField()
    tipo_responsavel = serializers.IntegerField(allow_null=True)
    codigo_turma = serializers.IntegerField()
    situacao_matricula = serializers.CharField()
    data_nascimento = serializers.DateField(allow_null=True)
    data_situacao_matricula = serializers.DateField(allow_null=True)
    ano_letivo = serializers.IntegerField()


class QuantidadeMatriculadosCCContratoSerializer(serializers.Serializer):
    """Serializa matriculados por componente no contrato do legado."""

    componente_curricular_id = serializers.IntegerField()
    quantidade = serializers.IntegerField()
    ordem = serializers.IntegerField()
    modalidade = serializers.CharField(allow_null=True)
    ano = serializers.CharField(allow_null=True)
    turma = serializers.CharField(allow_null=True)

    def to_representation(self, instance: Any) -> dict[str, Any]:
        """Serializa linha crua retornada pelo service."""
        if isinstance(instance, dict):
            instance = _quantidade_cc_contrato_representation(instance)
        return cast(dict[str, Any], super().to_representation(instance))


class QuantidadeMatriculadosContratoSerializer(serializers.Serializer):
    """Serializa a quantidade de matriculados no contrato do legado."""

    quantidade = serializers.IntegerField()
    ordem = serializers.IntegerField(allow_null=True)
    modalidade = serializers.CharField(allow_null=True)
    ano = serializers.CharField(allow_null=True)
    turma = serializers.CharField(allow_null=True)
    dre_codigo = serializers.CharField(allow_null=True)
    ue_codigo = serializers.CharField(allow_null=True)

    def to_representation(self, instance: Any) -> dict[str, Any]:
        """Serializa linha crua retornada pelo service."""
        if isinstance(instance, dict) and "codigo_dre" in instance:
            instance = _quantidade_contrato_representation(instance)
        return cast(dict[str, Any], super().to_representation(instance))


class DadosAcompanhamentoEscolarContratoSerializer(serializers.Serializer):
    """Serializa dados de acompanhamento escolar no contrato do legado."""

    codigo_eol = serializers.IntegerField()
    nome_responsavel = serializers.CharField(allow_null=True)
    cpf_responsavel = serializers.CharField(allow_null=True)
    nome = serializers.CharField()
    nome_social = serializers.CharField(allow_null=True)
    codigo_escola = serializers.CharField()
    codigo_dre = serializers.CharField(allow_null=True)
    escola = serializers.CharField(allow_null=True)
    tipo_responsavel = serializers.IntegerField(allow_null=True)
    codigo_tipo_escola = serializers.IntegerField(allow_null=True)
    descricao_tipo_escola = serializers.CharField(allow_null=True)
    sigla_dre = serializers.CharField(allow_null=True)
    codigo_turma = serializers.IntegerField()
    turma = serializers.CharField(allow_null=True)
    situacao_matricula = serializers.CharField(allow_null=True)
    data_nascimento = serializers.DateField(allow_null=True)
    data_situacao_matricula = serializers.DateTimeField(allow_null=True)
    codigo_ciclo_ensino = serializers.IntegerField(allow_null=True)
    codigo_etapa_ensino = serializers.IntegerField(allow_null=True)
    serie_resumida = serializers.CharField(allow_null=True)

    def to_representation(self, instance: Any) -> dict[str, Any]:
        """Serializa linha crua retornada pelo service."""
        if isinstance(instance, dict) and "codigo_aluno" in instance:
            instance = _acompanhamento_contrato_representation(instance)
        return cast(dict[str, Any], super().to_representation(instance))


class ResponsavelTurmaSerializer(serializers.Serializer):
    """Serializa dados do responsável por turma."""

    codigo_dre = serializers.CharField()
    dre = serializers.CharField(allow_null=True)
    codigo_ue = serializers.CharField()
    ue = serializers.CharField(allow_null=True)
    codigo_turma = serializers.IntegerField()
    turma = serializers.CharField(allow_null=True)
    cpf_responsavel = serializers.IntegerField()
    codigo_aluno = serializers.IntegerField()
    codigo_tipo_escola = serializers.IntegerField()
    codigo_etapa_ensino = serializers.IntegerField()
    codigo_ciclo_ensino = serializers.IntegerField()
    serie_resumida = serializers.CharField(allow_null=True)
    codigo_modalidade_turma = serializers.IntegerField()
    tem_app_instalado = serializers.BooleanField()


class DadosResponsavelSerializer(serializers.Serializer):
    """Serializa dados completos do responsável."""

    codigo_responsavel = serializers.IntegerField()
    cpf = serializers.CharField(allow_null=True)
    email = serializers.CharField(allow_null=True)
    nome = serializers.CharField(allow_null=True)
    tipo_responsavel = serializers.IntegerField(allow_null=True)
    nome_aluno = serializers.CharField()
    nome_social_aluno = serializers.CharField(allow_null=True)
    data_nascimento_aluno = serializers.DateField(allow_null=True)
    codigo_aluno = serializers.CharField()
    ddd_celular = serializers.CharField(allow_null=True)
    numero_celular = serializers.CharField(allow_null=True)
    autoriza_sms = serializers.CharField(allow_null=True)
    logradouro = serializers.CharField(allow_null=True)
    cep = serializers.IntegerField(allow_null=True)
    data_fim_vinculo = serializers.DateField(allow_null=True)

    def to_representation(self, instance: Any) -> dict[str, Any]:
        """Serializa linha composta retornada pelo service."""
        if isinstance(instance, dict) and "responsavel" in instance:
            instance = _dados_responsavel_representation(instance)
        return cast(dict[str, Any], super().to_representation(instance))


class DadosResponsavelContratoSerializer(serializers.Serializer):
    """Serializa os dados do responsável no contrato de integração."""

    id = serializers.IntegerField()
    cpf = serializers.CharField(allow_null=True)
    email = serializers.CharField(allow_null=True)
    nome = serializers.CharField(allow_null=True)
    tipo_responsavel = serializers.IntegerField()
    nome_social_aluno = serializers.CharField(allow_null=True)
    data_nascimento_aluno = serializers.DateField(allow_null=True)
    data_nascimento = serializers.DateField(allow_null=True)
    data_atualizacao = serializers.DateTimeField(allow_null=True)
    nome_mae = serializers.CharField(allow_null=True)
    tipo_sigilo = serializers.IntegerField()
    ddd_celular = serializers.CharField(allow_null=True)
    numero_celular = serializers.CharField(allow_null=True)
    nome_aluno = serializers.CharField()
    codigo_aluno = serializers.CharField()
    numero_rg = serializers.CharField(allow_null=True, trim_whitespace=False)
    digito_rg = serializers.CharField(allow_null=True, trim_whitespace=False)
    uf_rg = serializers.CharField(allow_null=True)
    cpf_confere = serializers.CharField(allow_null=True)
    tipo_turno_celular = serializers.CharField(allow_null=True)
    ddd_telefone_fixo = serializers.CharField(allow_blank=True)
    numero_telefone_fixo = serializers.CharField(allow_blank=True)
    tipo_turno_telefone_fixo = serializers.CharField(allow_null=True)
    ddd_telefone_comercial = serializers.CharField(allow_blank=True)
    numero_telefone_comercial = serializers.CharField(allow_blank=True)
    tipo_turno_telefone_comercial = serializers.CharField(allow_null=True)
    autoriza_envio_sms = serializers.CharField(allow_null=True)


class DadosResponsavelResumidoSerializer(serializers.Serializer):
    """Serializa dados resumidos do responsável."""

    id = serializers.IntegerField()
    cpf = serializers.CharField(allow_null=True)
    email = serializers.CharField(allow_null=True)
    nome = serializers.CharField(allow_null=True)
    tipo_responsavel = serializers.IntegerField(allow_null=True)
    data_nascimento = serializers.DateField(allow_null=True)
    data_atualizacao = serializers.DateTimeField(allow_null=True)
    nome_mae = serializers.CharField(allow_null=True)
    ddd_celular = serializers.CharField(allow_null=True)
    numero_celular = serializers.CharField(allow_null=True)
    codigo_aluno = serializers.CharField(allow_null=True)

    def to_representation(self, instance: Any) -> dict[str, Any]:
        """Serializa linha composta retornada pelo service."""
        if isinstance(instance, dict) and "responsavel" in instance:
            instance = _dados_responsavel_resumido_representation(instance)
        return cast(dict[str, Any], super().to_representation(instance))


class EnderecoFiliacaoSerializer(serializers.Serializer):
    """Serializa o endereço do responsável."""

    id = serializers.IntegerField(allow_null=True)
    nro = serializers.CharField(allow_null=True)
    complemento = serializers.CharField(allow_null=True)
    bairro = serializers.CharField(allow_null=True)
    cep = serializers.IntegerField(allow_null=True)
    nome_municipio = serializers.CharField(allow_null=True)
    sigla_uf = serializers.CharField(allow_null=True)
    tipo_logradouro = serializers.CharField(allow_null=True)
    logradouro = serializers.CharField(allow_null=True)


class DadosResponsavelFiliacaoSerializer(serializers.Serializer):
    """Serializa dados de filiação do responsável."""

    nome_responsavel = serializers.CharField(allow_null=True)
    cpf = serializers.CharField(allow_null=True)
    email = serializers.CharField(allow_null=True)
    ddd_celular = serializers.CharField(allow_null=True)
    numero_celular = serializers.CharField(allow_null=True)
    ddd_residencial = serializers.CharField(allow_null=True)
    numero_residencial = serializers.CharField(allow_null=True)
    ddd_comercial = serializers.CharField(allow_null=True)
    numero_comercial = serializers.CharField(allow_null=True)
    tipo_responsavel = serializers.IntegerField(allow_null=True)
    endereco = EnderecoFiliacaoSerializer()

    def to_representation(self, instance: Any) -> dict[str, Any]:
        """Serializa linha composta retornada pelo service."""
        if isinstance(instance, dict) and "responsavel" in instance:
            instance = _dados_responsavel_filiacao_representation(instance)
        return cast(dict[str, Any], super().to_representation(instance))


class TotalAlunosAtivosPeriodoSerializer(serializers.Serializer):
    """Serializa o total de alunos ativos em um período."""

    quantidade = serializers.IntegerField()


class ConsolidacaoMatriculaSerializer(serializers.Serializer):
    """Serializa dados de consolidação por turma."""

    turma_codigo = serializers.CharField()
    quantidade = serializers.IntegerField()

    def to_representation(self, instance: Any) -> dict[str, Any]:
        """Serializa linha crua retornada pelo service."""
        if isinstance(instance, dict) and "turma_codigo" not in instance:
            instance = _consolidacao_matricula_representation(instance)
        return cast(dict[str, Any], super().to_representation(instance))


class MatriculaEscolaAlunoSerializer(serializers.Serializer):
    """Serializa dados da matrícula de aluno em escola."""

    codigo_aluno = serializers.IntegerField()
    nome_aluno = serializers.CharField()
    nome_social_aluno = serializers.CharField(allow_null=True)
    codigo_situacao_matricula = serializers.IntegerField()
    situacao_matricula = serializers.CharField()
    data_situacao = serializers.DateTimeField(allow_null=True)
    codigo_turma = serializers.IntegerField()
    codigo_matricula = serializers.IntegerField()
    ano_letivo = serializers.IntegerField()

    def to_representation(self, instance: Any) -> dict[str, Any]:
        """Serializa linha composta retornada pelo service."""
        if isinstance(instance, dict) and "matricula" in instance:
            instance = _matricula_escola_aluno_representation(instance)
        data = cast(dict[str, Any], super().to_representation(instance))
        # Formatar data_situacao sem timezone, igual ao legado
        if data.get("data_situacao") and isinstance(data["data_situacao"], str):
            # Remove timezone se presente
            data["data_situacao"] = data["data_situacao"].replace("-03:00", "").replace("+00:00", "")
            # Remove zeros extras dos microssegundos para ficar igual ao legado (.187 ao invés de .183000)
            if "." in data["data_situacao"]:
                partes = data["data_situacao"].split(".")
                if len(partes) == 2:
                    # Limita a 3 dígitos de microssegundos
                    data["data_situacao"] = f"{partes[0]}.{partes[1][:3]}"
        return data


class AtualizarResponsavelBuscaAtivaRequestSerializer(serializers.Serializer):
    """Serializa dados de atualização de contato do responsável."""

    codigo_aluno = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    cpf = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    email = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    ddd_celular = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    numero_celular = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    ddd_residencial = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    numero_residencial = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    ddd_comercial = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    numero_comercial = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )


class AtualizarResponsavelRequestSerializer(serializers.Serializer):
    """Serializa dados cadastrais para atualização de responsável."""

    id = serializers.IntegerField(required=False, allow_null=True)
    cpf = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    email = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    nome = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    tipo_responsavel = serializers.IntegerField(
        required=False, allow_null=True
    )
    data_nascimento = serializers.DateTimeField(
        required=False, allow_null=True
    )
    data_atualizacao = serializers.DateTimeField(
        required=False, allow_null=True
    )
    nome_mae = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    ddd_celular = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    numero_celular = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    codigo_aluno = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )


class CadastrarResponsavelRequestSerializer(serializers.Serializer):
    """Serializa dados de cadastro de responsável."""

    cpf = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    nome = serializers.CharField(required=False, allow_blank=True)
    tipo_responsavel = serializers.IntegerField(
        required=False, allow_null=True
    )
    ddd_celular = serializers.CharField(required=False, allow_blank=True)
    numero_celular = serializers.CharField(required=False, allow_blank=True)
    codigo_aluno = serializers.CharField(required=False, allow_blank=True)


class ObterNomesAlunosRequestSerializer(serializers.Serializer):
    """Serializa os filtros da consulta de nomes de alunos."""

    codigos_alunos = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_null=True,
    )
    ano_letivo = serializers.IntegerField(required=False, allow_null=True)


class NomeAlunoSerializer(serializers.Serializer):
    """Serializa nomes e dados de matrícula-turma dos alunos."""

    nome_aluno = serializers.CharField()
    situacao_matricula = serializers.CharField()
    codigo_escola = serializers.CharField()
    data_matricula = serializers.DateTimeField(allow_null=True)
    codigo_aluno = serializers.IntegerField()
    codigo_turma = serializers.IntegerField()
    codigo_situacao_matricula = serializers.IntegerField()
