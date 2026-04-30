"""Models read-only do domínio Alunos — banco alunos_db.

Espelha 1-para-1 os models de ``apps/alunos/models.py`` do
``SME-IntegracaoEOL-MS-ETL``: este microsserviço apenas LÊ
(``Meta.managed = False``), enquanto a DDL é responsabilidade exclusiva
do MS-ETL.

Hierarquia (idêntica ao MS-ETL):
    TipoNecessidadeEspecial
    Aluno
        ├── ResponsavelAluno
        ├── NecessidadeEspecialAluno  ──► TipoNecessidadeEspecial
        └── Matricula
                └── MatriculaTurma

Qualquer dado fora deste universo (Endereço completo, metadados de
Turma/DRE/Modalidade, Escola, etapa/ciclo de ensino, agregações de
matrícula por turno etc.) NÃO é responsabilidade do domínio Alunos —
o Transition Gateway agrega esses dados a partir dos demais
microsserviços (Pedagógico, Programas).
"""

from django.db import models


class TipoNecessidadeEspecial(models.Model):
    """Catálogo de tipos de necessidade especial educacional (NEE).

    Espelha a tabela ``tipo_necessidade_especial`` em ``alunos_db``.
    Atua como tabela de domínio: cada registro é uma categoria
    referenciada por ``NecessidadeEspecialAluno`` para descrever a NEE
    de um aluno.

    Origem da DDL: ``SME-IntegracaoEOL-MS-ETL``. Este model é read-only
    (``Meta.managed = False``).
    """

    codigo_necessidade_especial = models.SmallIntegerField(primary_key=True)
    descricao = models.CharField(max_length=200)
    codigo_estado = models.SmallIntegerField(null=True, blank=True)
    ativo = models.BooleanField(default=True)
    data_cancelamento = models.DateField(null=True, blank=True)

    class Meta:
        app_label = "alunos"
        db_table = "tipo_necessidade_especial"
        managed = False
        verbose_name = "tipo de necessidade especial"
        verbose_name_plural = "tipos de necessidades especiais"

    def __str__(self) -> str:
        return f"{self.codigo_necessidade_especial} - {self.descricao}"


class Aluno(models.Model):
    """Dados cadastrais do aluno na rede municipal.

    Espelha a tabela ``aluno`` em ``alunos_db``. Concentra os campos
    pessoais (nome, CPF, data de nascimento, raça/cor, filiação) e o
    indicador ``possui_deficiencia``, derivado a partir das NEE ativas
    pelo MS-ETL.

    É a raiz do agregado do domínio Alunos: ``Matricula``,
    ``ResponsavelAluno`` e ``NecessidadeEspecialAluno`` apontam para
    este model via ``codigo_aluno``.

    Origem da DDL: ``SME-IntegracaoEOL-MS-ETL``. Este model é read-only
    (``Meta.managed = False``).
    """

    codigo_aluno = models.BigIntegerField(primary_key=True)
    nome = models.CharField(max_length=200)
    nome_social = models.CharField(max_length=200, null=True, blank=True)
    data_nascimento = models.DateField(null=True, blank=True)
    sexo = models.CharField(max_length=1, null=True, blank=True)
    cpf = models.CharField(max_length=11, null=True, blank=True)
    nome_mae = models.CharField(max_length=200, null=True, blank=True)
    nacionalidade = models.CharField(max_length=100, null=True, blank=True)
    nis = models.CharField(max_length=20, null=True, blank=True)
    raca_cor = models.CharField(max_length=50, null=True, blank=True)
    data_atualizacao_contato = models.DateField(null=True, blank=True)
    possui_deficiencia = models.BooleanField(default=False)

    class Meta:
        app_label = "alunos"
        db_table = "aluno"
        managed = False
        verbose_name = "aluno"
        verbose_name_plural = "alunos"

    def __str__(self) -> str:
        return f"{self.codigo_aluno} - {self.nome}"


class ResponsavelAluno(models.Model):
    """Vínculo de um responsável (mãe, pai, guardião) com o aluno.

    Espelha a tabela ``responsavel_aluno`` em ``alunos_db``. Cada
    registro representa um responsável vigente ou histórico: o vínculo
    é considerado **ativo** enquanto ``data_fim_vinculo`` for ``NULL``.

    Mantém os dados de contato (telefone, e-mail, endereço,
    consentimento de SMS) usados pelos endpoints A19/A20/A21 e pelo
    fluxo de busca ativa (atualização de contato).

    Origem da DDL: ``SME-IntegracaoEOL-MS-ETL``. Este model é read-only
    (``Meta.managed = False``).
    """

    codigo_responsavel = models.BigIntegerField(primary_key=True)
    aluno = models.ForeignKey(
        Aluno,
        db_column="codigo_aluno",
        on_delete=models.DO_NOTHING,
        related_name="responsaveis",
    )
    tipo_responsavel = models.SmallIntegerField(null=True, blank=True)
    nome = models.CharField(max_length=200, null=True, blank=True)
    cpf = models.CharField(max_length=11, null=True, blank=True)
    ddd_celular = models.CharField(max_length=4, null=True, blank=True)
    numero_celular = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(max_length=200, null=True, blank=True)
    autoriza_sms = models.CharField(max_length=1, null=True, blank=True)
    logradouro = models.CharField(max_length=255, null=True, blank=True)
    cep = models.IntegerField(null=True, blank=True)
    data_fim_vinculo = models.DateField(null=True, blank=True)

    class Meta:
        app_label = "alunos"
        db_table = "responsavel_aluno"
        managed = False
        verbose_name = "responsável"
        verbose_name_plural = "responsáveis"

    def __str__(self) -> str:
        return f"{self.nome} (Aluno: {self.aluno_id})"


class NecessidadeEspecialAluno(models.Model):
    """Vínculo entre o aluno e uma NEE diagnosticada.

    Espelha a tabela ``necessidade_especial_aluno`` em ``alunos_db``.
    Cada registro materializa o histórico de NEE de um aluno em um
    intervalo (``data_inicio`` / ``data_fim``); a NEE é considerada
    **vigente** enquanto ``data_fim`` for ``NULL``.

    Funciona como tabela associativa entre ``Aluno`` e
    ``TipoNecessidadeEspecial`` — preserva o tipo da NEE e o período
    em que esteve ativa, alimentando o endpoint A10 e o flag
    ``possui_deficiencia`` em ``Aluno``.

    Origem da DDL: ``SME-IntegracaoEOL-MS-ETL``. Este model é read-only
    (``Meta.managed = False``).
    """

    codigo_necessidade_especial_aluno = models.BigIntegerField(
        primary_key=True
    )
    aluno = models.ForeignKey(
        Aluno,
        db_column="codigo_aluno",
        on_delete=models.DO_NOTHING,
        related_name="necessidades",
    )
    necessidade_especial = models.ForeignKey(
        TipoNecessidadeEspecial,
        db_column="codigo_necessidade_especial",
        on_delete=models.DO_NOTHING,
    )
    data_inicio = models.DateField(null=True, blank=True)
    data_fim = models.DateField(null=True, blank=True)

    class Meta:
        app_label = "alunos"
        db_table = "necessidade_especial_aluno"
        managed = False

    def __str__(self) -> str:
        return f"Aluno {self.aluno_id} - NEE {self.necessidade_especial_id}"


class Matricula(models.Model):
    """Matrícula do aluno em uma UE (Unidade Escolar) num ano letivo.

    Espelha a tabela ``matricula`` em ``alunos_db``. Representa o
    vínculo do aluno com a escola — é a entidade central para os
    endpoints de listagem (A04/A05/A11/A12), totais (A07/A15/A16) e
    derivações de situação (ativa/válida) controladas por
    ``codigo_situacao_matricula`` (ver ``apps.alunos.enums``).

    Liga-se a ``Aluno`` (N:1) e a ``MatriculaTurma`` (1:N) — esta
    última materializa em qual turma o aluno está alocado dentro da
    UE.

    Origem da DDL: ``SME-IntegracaoEOL-MS-ETL``. Este model é read-only
    (``Meta.managed = False``).
    """

    codigo_matricula = models.BigIntegerField(primary_key=True)
    aluno = models.ForeignKey(
        Aluno,
        db_column="codigo_aluno",
        on_delete=models.DO_NOTHING,
        related_name="matriculas",
    )
    codigo_ue = models.CharField(max_length=20)
    ano_letivo = models.SmallIntegerField()
    data_situacao_matricula = models.DateField(null=True, blank=True)
    codigo_situacao_matricula = models.SmallIntegerField()
    situacao_matricula = models.CharField(max_length=100)

    class Meta:
        app_label = "alunos"
        db_table = "matricula"
        managed = False
        verbose_name = "matrícula"
        verbose_name_plural = "matrículas"

    def __str__(self) -> str:
        return f"{self.codigo_matricula} ({self.ano_letivo})"


class MatriculaTurma(models.Model):
    """Alocação da matrícula em uma turma específica da UE.

    Espelha a tabela ``matricula_turma`` em ``alunos_db``. Resolve a
    relação N:N entre ``Matricula`` e turma — uma matrícula pode passar
    por mais de uma turma ao longo do ano letivo (transferência,
    progressão), e cada vínculo carrega o ``numero_chamada`` e a
    ``data_situacao_aluno`` do aluno naquela turma.

    A constraint ``unique_together = (codigo_matricula, codigo_turma)``
    garante que cada par matrícula/turma apareça uma única vez, mesmo
    quando o histórico inclui reentradas.

    Os metadados da turma propriamente dita (nome, modalidade, etapa,
    turno, etc.) **não** vivem aqui — pertencem ao domínio Pedagógico
    e são compostos pelo Transition Gateway quando necessário.

    Origem da DDL: ``SME-IntegracaoEOL-MS-ETL``. Este model é read-only
    (``Meta.managed = False``).
    """

    id = models.BigAutoField(primary_key=True)
    codigo_matricula = models.BigIntegerField(
        db_index=True, null=True, blank=True
    )
    codigo_turma = models.BigIntegerField()
    numero_chamada = models.CharField(max_length=5, null=True, blank=True)
    data_situacao_aluno = models.DateField(null=True, blank=True)

    class Meta:
        app_label = "alunos"
        db_table = "matricula_turma"
        managed = False
        unique_together = [("codigo_matricula", "codigo_turma")]

    def __str__(self) -> str:
        return f"M: {self.codigo_matricula} - T: {self.codigo_turma}"
