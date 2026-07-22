"""Serializers do domínio Alunos."""

from typing import Any, cast

from rest_framework import serializers


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

    def get_data_atualizacao_contato(self, obj: Any) -> str:
        """Retorna data de atualização de contato formatada.

        Returns:
            Data no formato ISO-8601 ou '0001-01-01T00:00:00' quando ausente.
        """
        val = getattr(obj, "data_atualizacao_contato", None)
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


class AlunoAutocompleteSerializer(serializers.Serializer):
    """Serializa dados de autocomplete de aluno."""

    codigo_aluno = serializers.IntegerField()
    nome_aluno = serializers.CharField()
    nome_social_aluno = serializers.CharField(allow_null=True)
    codigo_turma = serializers.IntegerField()
    numero_aluno_chamada = serializers.CharField(allow_null=True)
    turma = serializers.CharField(allow_null=True)
    modalidade = serializers.CharField(allow_null=True)


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


class QuantidadeMatriculadosContratoSerializer(serializers.Serializer):
    """Serializa a quantidade de matriculados no contrato do legado."""

    quantidade = serializers.IntegerField()
    ordem = serializers.IntegerField(allow_null=True)
    modalidade = serializers.CharField(allow_null=True)
    ano = serializers.CharField(allow_null=True)
    turma = serializers.CharField(allow_null=True)
    dre_codigo = serializers.CharField(allow_null=True)
    ue_codigo = serializers.CharField(allow_null=True)


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


class TotalAlunosAtivosPeriodoSerializer(serializers.Serializer):
    """Serializa o total de alunos ativos em um período."""

    quantidade = serializers.IntegerField()


class ConsolidacaoMatriculaSerializer(serializers.Serializer):
    """Serializa dados de consolidação por turma."""

    turma_codigo = serializers.CharField()
    quantidade = serializers.IntegerField()


class MatriculaEscolaAlunoSerializer(serializers.Serializer):
    """Serializa dados da matrícula de aluno em escola."""

    codigo_aluno = serializers.IntegerField()
    nome_aluno = serializers.CharField()
    nome_social_aluno = serializers.CharField(allow_null=True)
    codigo_situacao_matricula = serializers.IntegerField()
    situacao_matricula = serializers.CharField()
    data_situacao = serializers.DateField(allow_null=True)
    codigo_turma = serializers.IntegerField()
    codigo_matricula = serializers.IntegerField()
    ano_letivo = serializers.IntegerField()


class AtualizarResponsavelBuscaAtivaRequestSerializer(serializers.Serializer):
    """Serializa dados de atualização de contato do responsável."""

    codigo_aluno = serializers.IntegerField(required=False)
    cpf = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    ddd_celular = serializers.CharField(required=False, allow_blank=True)
    numero_celular = serializers.CharField(required=False, allow_blank=True)
    ddd_residencial = serializers.CharField(required=False, allow_blank=True)
    numero_residencial = serializers.CharField(
        required=False, allow_blank=True
    )
    ddd_comercial = serializers.CharField(required=False, allow_blank=True)
    numero_comercial = serializers.CharField(required=False, allow_blank=True)


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
