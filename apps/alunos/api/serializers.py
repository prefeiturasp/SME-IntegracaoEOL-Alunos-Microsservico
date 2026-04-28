"""Serializers DRF do domínio Alunos.

Mapeiam os DTOs retornados por ``apps.alunos.services`` para o shape
camelCase. **Shape reduzido**: campos pertencentes a outros domínios
(metadados de Turma, Escola, DRE, Modalidade, Endereço completo,
agregação por turno, view de acompanhamento materializada) NÃO são
expostos aqui — o Transition Gateway agrega esses dados a partir dos
demais microsserviços.
"""

from rest_framework import serializers


class TurmaDoAlunoSerializer(serializers.Serializer):
    """A01/A02/A03/A04/A11/A12 — Turma do aluno (shape reduzido)."""

    codigoAluno = serializers.CharField(source="codigo_aluno")
    anoLetivo = serializers.IntegerField(source="ano_letivo")
    nomeAluno = serializers.CharField(source="nome_aluno")
    nomeSocialAluno = serializers.CharField(
        source="nome_social_aluno", allow_null=True
    )
    codigoSituacaoMatricula = serializers.IntegerField(
        source="codigo_situacao_matricula"
    )
    situacaoMatricula = serializers.CharField(source="situacao_matricula")
    dataSituacao = serializers.DateField(
        source="data_situacao", allow_null=True
    )
    dataNascimento = serializers.DateField(
        source="data_nascimento", allow_null=True
    )
    idade = serializers.IntegerField(allow_null=True)
    documentoCpf = serializers.CharField(
        source="documento_cpf", allow_null=True
    )
    dataMatricula = serializers.DateField(
        source="data_matricula", allow_null=True
    )
    numeroAlunoChamada = serializers.CharField(
        source="numero_aluno_chamada", allow_null=True
    )
    codigoTurma = serializers.IntegerField(source="codigo_turma")
    codigoEscola = serializers.CharField(source="codigo_escola")
    dataAtualizacaoContato = serializers.DateField(
        source="data_atualizacao_contato", allow_null=True
    )


class AlunoAutocompleteSerializer(serializers.Serializer):
    """A05/A06 — Autocomplete de aluno (shape reduzido)."""

    codigoAluno = serializers.IntegerField(source="codigo_aluno")
    nomeAluno = serializers.CharField(source="nome_aluno")
    nomeSocialAluno = serializers.CharField(
        source="nome_social_aluno", allow_null=True
    )
    codigoTurma = serializers.IntegerField(source="codigo_turma")
    numeroAlunoChamada = serializers.CharField(
        source="numero_aluno_chamada", allow_null=True
    )


class AlunoAtivoTurmaSerializer(serializers.Serializer):
    """A08/A09 — Alunos ativos em uma turma (shape reduzido)."""

    codigoAluno = serializers.IntegerField(source="codigo_aluno")
    nomeAluno = serializers.CharField(source="nome_aluno")
    nomeSocialAluno = serializers.CharField(
        source="nome_social_aluno", allow_null=True
    )
    dataNascimento = serializers.DateField(
        source="data_nascimento", allow_null=True
    )
    codigoSituacaoMatricula = serializers.IntegerField(
        source="codigo_situacao_matricula"
    )
    situacaoMatricula = serializers.CharField(source="situacao_matricula")
    dataSituacao = serializers.DateField(
        source="data_situacao", allow_null=True
    )
    numeroAlunoChamada = serializers.CharField(
        source="numero_aluno_chamada", allow_null=True
    )
    possuiDeficiencia = serializers.BooleanField(source="possui_deficiencia")
    codigoMatricula = serializers.IntegerField(source="codigo_matricula")
    codigoTurma = serializers.IntegerField(source="codigo_turma")
    codigoEscola = serializers.CharField(source="codigo_escola")
    anoLetivo = serializers.IntegerField(source="ano_letivo")


class NecessidadeEspecialSerializer(serializers.Serializer):
    """A10 — Necessidade especial do aluno (shape reduzido)."""

    codigoAluno = serializers.IntegerField(source="codigo_aluno")
    tipoNecessidadeEspecial = serializers.IntegerField(
        source="tipo_necessidade_especial"
    )
    descricaoNecessidadeEspecial = serializers.CharField(
        source="descricao_necessidade_especial"
    )


class InformacoesAlunoSerializer(serializers.Serializer):
    """A13/A27 — Informações do aluno (shape reduzido).

    Campos out-of-scope (Transition Gateway agrega): grupoEtnico,
    nacionalidadeResponsavel, ehImigrante, responsavelEhImigrante, cns,
    teg, endereço completo (id, nro, complemento, bairro, cep,
    nomeMunicipio, siglaUf, tipoLogradouro, logradouro).
    """

    codigoAluno = serializers.IntegerField(source="codigo_aluno")
    nomeAluno = serializers.CharField(source="nome_aluno")
    nomeSocialAluno = serializers.CharField(
        source="nome_social_aluno", allow_null=True
    )
    nomeMae = serializers.CharField(source="nome_mae", allow_null=True)
    sexo = serializers.CharField(allow_null=True)
    nacionalidade = serializers.CharField(allow_null=True)
    racaCor = serializers.CharField(source="raca_cor", allow_null=True)
    nis = serializers.CharField(allow_null=True)
    cpf = serializers.CharField(allow_null=True)
    dataNascimento = serializers.DateField(
        source="data_nascimento", allow_null=True
    )
    possuiDeficiencia = serializers.BooleanField(source="possui_deficiencia")


class InformacoesAlunoTurmaSerializer(serializers.Serializer):
    """A14 — Resumo de aluno em turma (shape reduzido)."""

    numeroAlunoChamada = serializers.CharField(
        source="numero_aluno_chamada", allow_null=True
    )
    codigoAluno = serializers.IntegerField(source="codigo_aluno")
    nomeAluno = serializers.CharField(source="nome_aluno")
    nomeSocialAluno = serializers.CharField(
        source="nome_social_aluno", allow_null=True
    )
    sexo = serializers.CharField(allow_null=True)
    racaCor = serializers.CharField(source="raca_cor", allow_null=True)


class QuantidadeMatriculadosCCSerializer(serializers.Serializer):
    """A15 — Quantidade de matriculados por turma (shape reduzido).

    Campos out-of-scope (Pedagógico): componenteCurricularId, modalidade,
    ano (turma), turma (nome).
    """

    codigoTurma = serializers.IntegerField(source="codigo_turma")
    quantidade = serializers.IntegerField()
    ordem = serializers.IntegerField()


class QuantidadeMatriculadosSerializer(serializers.Serializer):
    """A16 — Quantidade de matriculados por UE/turma (shape reduzido).

    Campos out-of-scope: dreCodigo, modalidade, ano (turma), turma.
    """

    quantidade = serializers.IntegerField()
    ordem = serializers.IntegerField()
    codigoTurma = serializers.IntegerField(source="codigo_turma")
    ueCodigo = serializers.CharField(source="ue_codigo")


class DadosAcompanhamentoEscolarSerializer(serializers.Serializer):
    """A18 — Acompanhamento escolar (shape reduzido).

    Campos out-of-scope (Transition Gateway agrega via Pedagógico):
    escola (nome), codigoDre, siglaDre, codigoTipoEscola,
    descricaoTipoEscola, codigoCicloEnsino, codigoEtapaEnsino,
    serieResumida, modalidadeCodigo, modalidadeDescricao.
    """

    codigoEol = serializers.IntegerField(source="codigo_eol")
    nomeResponsavel = serializers.CharField(
        source="nome_responsavel", allow_null=True
    )
    cpfResponsavel = serializers.CharField(
        source="cpf_responsavel", allow_null=True
    )
    nome = serializers.CharField()
    nomeSocial = serializers.CharField(source="nome_social", allow_null=True)
    codigoEscola = serializers.CharField(source="codigo_escola")
    tipoResponsavel = serializers.IntegerField(
        source="tipo_responsavel", allow_null=True
    )
    codigoTurma = serializers.IntegerField(source="codigo_turma")
    situacaoMatricula = serializers.CharField(source="situacao_matricula")
    dataNascimento = serializers.DateField(
        source="data_nascimento", allow_null=True
    )
    dataSituacaoMatricula = serializers.DateField(
        source="data_situacao_matricula", allow_null=True
    )
    anoLetivo = serializers.IntegerField(source="ano_letivo")


class ResponsavelTurmaSerializer(serializers.Serializer):
    """A19 — Responsável por turma (shape reduzido).

    Campos out-of-scope (Pedagógico): codigoDre, dre, ue (nome),
    turma (nome), codigoTipoEscola, codigoEtapaEnsino, codigoCicloEnsino,
    serieResumida, codigoModalidadeTurma, temAppInstalado.
    """

    codigoUe = serializers.CharField(source="codigo_ue")
    codigoTurma = serializers.IntegerField(source="codigo_turma")
    cpfResponsavel = serializers.CharField(source="cpf_responsavel")
    codigoAluno = serializers.IntegerField(source="codigo_aluno")


class DadosResponsavelSerializer(serializers.Serializer):
    """A20 — Dados do responsável (shape reduzido).

    Campos out-of-scope (não existem em ``responsavel_aluno`` do MS-ETL):
    tipoSigilo, dataNascimento (do responsável), nomeMae do responsável,
    numeroRG, digitoRG, ufRG, cpfConfere, tipoTurnoCelular,
    dddTelefoneFixo/Comercial e turnos, dataNascimentoMae.
    """

    codigoResponsavel = serializers.IntegerField(source="codigo_responsavel")
    cpf = serializers.CharField(allow_null=True)
    email = serializers.CharField(allow_null=True)
    nome = serializers.CharField(allow_null=True)
    tipoResponsavel = serializers.IntegerField(
        source="tipo_responsavel", allow_null=True
    )
    nomeAluno = serializers.CharField(source="nome_aluno")
    nomeSocialAluno = serializers.CharField(
        source="nome_social_aluno", allow_null=True
    )
    dataNascimentoAluno = serializers.DateField(
        source="data_nascimento_aluno", allow_null=True
    )
    codigoAluno = serializers.CharField(source="codigo_aluno")
    dddCelular = serializers.CharField(source="ddd_celular", allow_null=True)
    numeroCelular = serializers.CharField(
        source="numero_celular", allow_null=True
    )
    autorizaSms = serializers.CharField(
        source="autoriza_sms", allow_null=True
    )
    logradouro = serializers.CharField(allow_null=True)
    cep = serializers.IntegerField(allow_null=True)
    dataFimVinculo = serializers.DateField(
        source="data_fim_vinculo", allow_null=True
    )


class DadosResponsavelResumidoSerializer(serializers.Serializer):
    """A21/A22/A23 — Dados resumidos do responsável."""

    codigoResponsavel = serializers.IntegerField(source="codigo_responsavel")
    cpf = serializers.CharField(allow_null=True)
    email = serializers.CharField(allow_null=True)
    nome = serializers.CharField(allow_null=True)
    tipoResponsavel = serializers.IntegerField(
        source="tipo_responsavel", allow_null=True
    )
    dddCelular = serializers.CharField(source="ddd_celular", allow_null=True)
    numeroCelular = serializers.CharField(
        source="numero_celular", allow_null=True
    )
    codigoAluno = serializers.CharField(source="codigo_aluno")


class TotalAlunosAtivosPeriodoSerializer(serializers.Serializer):
    """A07 — Total de alunos ativos em um período."""

    quantidade = serializers.IntegerField()


class ConsolidacaoMatriculaSerializer(serializers.Serializer):
    """M01/M02/E05 — Consolidação por turma."""

    turmaCodigo = serializers.CharField(source="turma_codigo")
    quantidade = serializers.IntegerField()


class MatriculaEscolaAlunoSerializer(serializers.Serializer):
    """E24 — Matrícula de aluno em escola."""

    codigoAluno = serializers.IntegerField(source="codigo_aluno")
    nomeAluno = serializers.CharField(source="nome_aluno")
    nomeSocialAluno = serializers.CharField(
        source="nome_social_aluno", allow_null=True
    )
    codigoSituacaoMatricula = serializers.IntegerField(
        source="codigo_situacao_matricula"
    )
    situacaoMatricula = serializers.CharField(source="situacao_matricula")
    dataSituacao = serializers.DateField(
        source="data_situacao", allow_null=True
    )
    codigoTurma = serializers.IntegerField(source="codigo_turma")
    codigoMatricula = serializers.IntegerField(source="codigo_matricula")
    anoLetivo = serializers.IntegerField(source="ano_letivo")


# ---------------------------------------------------------------------------
# Request bodies (escrita)
# ---------------------------------------------------------------------------


class AtualizarResponsavelBuscaAtivaRequestSerializer(
    serializers.Serializer
):
    """A22 — Body do PUT /alunos/{codigoAluno}/responsaveis/{cpf}.

    Campos do contrato legado que não pertencem ao domínio Alunos
    (``dddResidencial``, ``numeroResidencial``, ``dddComercial``,
    ``numeroComercial``) são aceitos no body para compatibilidade,
    mas ignorados pela camada de service.
    """

    codigoAluno = serializers.IntegerField(
        source="codigo_aluno", required=False
    )
    cpf = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    dddCelular = serializers.CharField(
        source="ddd_celular", required=False, allow_blank=True
    )
    numeroCelular = serializers.CharField(
        source="numero_celular", required=False, allow_blank=True
    )
    dddResidencial = serializers.CharField(
        required=False, allow_blank=True
    )
    numeroResidencial = serializers.CharField(
        required=False, allow_blank=True
    )
    dddComercial = serializers.CharField(required=False, allow_blank=True)
    numeroComercial = serializers.CharField(
        required=False, allow_blank=True
    )


class CadastrarResponsavelRequestSerializer(serializers.Serializer):
    """A23 — Body do POST /alunos/{codigoAluno}/responsaveis/{cpf}."""

    cpf = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    nome = serializers.CharField(required=False, allow_blank=True)
    tipoResponsavel = serializers.IntegerField(
        source="tipo_responsavel", required=False, allow_null=True
    )
    dddCelular = serializers.CharField(
        source="ddd_celular", required=False, allow_blank=True
    )
    numeroCelular = serializers.CharField(
        source="numero_celular", required=False, allow_blank=True
    )
    codigoAluno = serializers.CharField(
        source="codigo_aluno", required=False, allow_blank=True
    )
