"""Serializers do domínio Alunos."""

from rest_framework import serializers


class TurmaDoAlunoSerializer(serializers.Serializer):
    """Serializa turmas do aluno."""

    codigo_aluno = serializers.IntegerField()
    ano_letivo = serializers.IntegerField()
    nome_aluno = serializers.CharField()
    nome_social_aluno = serializers.CharField(allow_null=True)
    codigo_situacao_matricula = serializers.IntegerField()
    situacao_matricula = serializers.CharField()
    data_situacao = serializers.DateField(allow_null=True)
    data_nascimento = serializers.DateField(allow_null=True)
    numero_aluno_chamada = serializers.CharField(allow_null=True)
    codigo_turma = serializers.IntegerField()
    data_atualizacao_contato = serializers.DateField(allow_null=True)


class AlunoAutocompleteSerializer(serializers.Serializer):
    """Serializa dados de autocomplete de aluno."""

    codigo_aluno = serializers.IntegerField()
    nome_aluno = serializers.CharField()
    nome_social_aluno = serializers.CharField(allow_null=True)
    codigo_turma = serializers.IntegerField()
    numero_aluno_chamada = serializers.CharField(allow_null=True)


class AlunoAtivoTurmaSerializer(serializers.Serializer):
    """Serializa alunos ativos em uma turma."""

    codigo_aluno = serializers.IntegerField()
    nome_aluno = serializers.CharField()
    nome_social_aluno = serializers.CharField(allow_null=True)
    data_nascimento = serializers.DateField(allow_null=True)
    codigo_situacao_matricula = serializers.IntegerField()
    situacao_matricula = serializers.CharField()
    data_situacao = serializers.DateField(allow_null=True)
    numero_aluno_chamada = serializers.CharField(allow_null=True)
    possui_deficiencia = serializers.BooleanField()
    codigo_matricula = serializers.IntegerField()
    codigo_turma = serializers.IntegerField()
    codigo_escola = serializers.CharField()
    ano_letivo = serializers.IntegerField()


class NecessidadeEspecialSerializer(serializers.Serializer):
    """Serializa necessidades especiais do aluno."""

    codigo_aluno = serializers.IntegerField()
    tipo_necessidade_especial = serializers.IntegerField()
    descricao_necessidade_especial = serializers.CharField()


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
    data_nascimento = serializers.DateField(allow_null=True)
    possui_deficiencia = serializers.BooleanField()


class InformacoesAlunoTurmaSerializer(serializers.Serializer):
    """Serializa resumo de aluno em turma."""

    numero_aluno_chamada = serializers.CharField(allow_null=True)
    codigo_aluno = serializers.IntegerField()
    nome_aluno = serializers.CharField()
    nome_social_aluno = serializers.CharField(allow_null=True)
    sexo = serializers.CharField(allow_null=True)
    raca_cor = serializers.CharField(allow_null=True)


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


class ResponsavelTurmaSerializer(serializers.Serializer):
    """Serializa dados do responsável por turma."""

    codigo_ue = serializers.CharField()
    codigo_turma = serializers.IntegerField()
    cpf_responsavel = serializers.CharField()
    codigo_aluno = serializers.IntegerField()


class DadosResponsavelSerializer(serializers.Serializer):
    """Serializa os dados do responsável."""

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
    """Serializa os dados resumidos do responsável."""

    codigo_responsavel = serializers.IntegerField()
    cpf = serializers.CharField(allow_null=True)
    email = serializers.CharField(allow_null=True)
    nome = serializers.CharField(allow_null=True)
    tipo_responsavel = serializers.IntegerField(allow_null=True)
    ddd_celular = serializers.CharField(allow_null=True)
    numero_celular = serializers.CharField(allow_null=True)
    codigo_aluno = serializers.CharField()


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
    """Serializa os dados para atualizar o responsável do aluno."""

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
    """Serializa os dados para cadastrar um novo responsável."""

    cpf = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    nome = serializers.CharField(required=False, allow_blank=True)
    tipo_responsavel = serializers.IntegerField(
        required=False, allow_null=True
    )
    ddd_celular = serializers.CharField(required=False, allow_blank=True)
    numero_celular = serializers.CharField(required=False, allow_blank=True)
    codigo_aluno = serializers.CharField(required=False, allow_blank=True)
