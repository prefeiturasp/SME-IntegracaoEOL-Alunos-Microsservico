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
    """A05/A06 — Autocomplete de aluno (shape reduzido)."""

    codigo_aluno = serializers.IntegerField()
    nome_aluno = serializers.CharField()
    nome_social_aluno = serializers.CharField(allow_null=True)
    codigo_turma = serializers.IntegerField()
    numero_aluno_chamada = serializers.CharField(allow_null=True)


class AlunoAtivoTurmaSerializer(serializers.Serializer):
    """A08/A09 — Alunos ativos em uma turma (shape reduzido)."""

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
    """A10 — Necessidade especial do aluno (shape reduzido)."""

    codigo_aluno = serializers.IntegerField()
    tipo_necessidade_especial = serializers.IntegerField()
    descricao_necessidade_especial = serializers.CharField()


class InformacoesAlunoSerializer(serializers.Serializer):
    """A13/A27 — Informações do aluno (shape reduzido).

    Campos out-of-scope (Transition Gateway agrega): grupo_etnico,
    nacionalidade_responsavel, eh_imigrante, responsavel_eh_imigrante, cns,
    teg, endereço completo (id, nro, complemento, bairro, cep,
    nome_municipio, sigla_uf, tipo_logradouro, logradouro).
    """

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
    """A14 — Resumo de aluno em turma (shape reduzido)."""

    numero_aluno_chamada = serializers.CharField(allow_null=True)
    codigo_aluno = serializers.IntegerField()
    nome_aluno = serializers.CharField()
    nome_social_aluno = serializers.CharField(allow_null=True)
    sexo = serializers.CharField(allow_null=True)
    raca_cor = serializers.CharField(allow_null=True)


class QuantidadeMatriculadosCCSerializer(serializers.Serializer):
    """A15 — Quantidade de matriculados por turma (shape reduzido).

    Campos out-of-scope (Pedagógico): componente_curricular_id, modalidade,
    ano (turma), turma (nome).
    """

    codigo_turma = serializers.IntegerField()
    quantidade = serializers.IntegerField()
    ordem = serializers.IntegerField()


class QuantidadeMatriculadosSerializer(serializers.Serializer):
    """A16 — Quantidade de matriculados por UE/turma (shape reduzido).

    Campos out-of-scope: dre_codigo, modalidade, ano (turma), turma.
    """

    quantidade = serializers.IntegerField()
    ordem = serializers.IntegerField()
    codigo_turma = serializers.IntegerField()
    ue_codigo = serializers.CharField()


class DadosAcompanhamentoEscolarSerializer(serializers.Serializer):
    """A18 — Acompanhamento escolar (shape reduzido).

    Campos out-of-scope (Transition Gateway agrega via Pedagógico):
    escola (nome), codigo_dre, sigla_dre, codigo_tipo_escola,
    descricao_tipo_escola, codigo_ciclo_ensino, codigo_etapa_ensino,
    serie_resumida, modalidade_codigo, modalidade_descricao.
    """

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
    """A19 — Responsável por turma (shape reduzido).

    Campos out-of-scope (Pedagógico): codigo_dre, dre, ue (nome),
    turma (nome), codigo_tipo_escola, codigo_etapa_ensino, codigo_ciclo_ensino,
    serie_resumida, codigo_modalidade_turma, tem_app_instalado.
    """

    codigo_ue = serializers.CharField()
    codigo_turma = serializers.IntegerField()
    cpf_responsavel = serializers.CharField()
    codigo_aluno = serializers.IntegerField()


class DadosResponsavelSerializer(serializers.Serializer):
    """A20 — Dados do responsável (shape reduzido).

    Campos out-of-scope (não existem em ``responsavel_aluno`` do MS-ETL):
    tipo_sigilo, data_nascimento (do responsável), nome_mae do responsável,
    numero_rg, digito_rg, uf_rg, cpf_confere, tipo_turno_celular,
    ddd_telefone_fixo/comercial e turnos, data_nascimento_mae.
    """

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
    """A21/A22/A23 — Dados resumidos do responsável."""

    codigo_responsavel = serializers.IntegerField()
    cpf = serializers.CharField(allow_null=True)
    email = serializers.CharField(allow_null=True)
    nome = serializers.CharField(allow_null=True)
    tipo_responsavel = serializers.IntegerField(allow_null=True)
    ddd_celular = serializers.CharField(allow_null=True)
    numero_celular = serializers.CharField(allow_null=True)
    codigo_aluno = serializers.CharField()


class TotalAlunosAtivosPeriodoSerializer(serializers.Serializer):
    """A07 — Total de alunos ativos em um período."""

    quantidade = serializers.IntegerField()


class ConsolidacaoMatriculaSerializer(serializers.Serializer):
    """M01/M02/E05 — Consolidação por turma."""

    turma_codigo = serializers.CharField()
    quantidade = serializers.IntegerField()


class MatriculaEscolaAlunoSerializer(serializers.Serializer):
    """E24 — Matrícula de aluno em escola."""

    codigo_aluno = serializers.IntegerField()
    nome_aluno = serializers.CharField()
    nome_social_aluno = serializers.CharField(allow_null=True)
    codigo_situacao_matricula = serializers.IntegerField()
    situacao_matricula = serializers.CharField()
    data_situacao = serializers.DateField(allow_null=True)
    codigo_turma = serializers.IntegerField()
    codigo_matricula = serializers.IntegerField()
    ano_letivo = serializers.IntegerField()


# ---------------------------------------------------------------------------
# Request bodies (escrita)
# ---------------------------------------------------------------------------


class AtualizarResponsavelBuscaAtivaRequestSerializer(serializers.Serializer):
    """A22 — Body do PUT /alunos/{codigoAluno}/responsaveis/{cpf}.

    Campos do contrato legado que não pertencem ao domínio Alunos
    (``dddResidencial``, ``numeroResidencial``, ``dddComercial``,
    ``numeroComercial``) são aceitos no body para compatibilidade,
    mas ignorados pela camada de service.
    """

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
    """A23 — Body do POST /alunos/{codigoAluno}/responsaveis/{cpf}."""

    cpf = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    nome = serializers.CharField(required=False, allow_blank=True)
    tipo_responsavel = serializers.IntegerField(
        required=False, allow_null=True
    )
    ddd_celular = serializers.CharField(required=False, allow_blank=True)
    numero_celular = serializers.CharField(required=False, allow_blank=True)
    codigo_aluno = serializers.CharField(required=False, allow_blank=True)
