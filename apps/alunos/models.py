"""Models read-only do domínio Alunos."""

from django.db import models


class TipoNecessidadeEspecial(models.Model):
    """Catálogo de tipos de necessidade especial educacional (NEE)."""

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
    """Dados cadastrais do aluno na rede municipal."""

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
    cns = models.CharField(max_length=20, null=True, blank=True)
    data_atualizacao_contato = models.DateTimeField(null=True, blank=True)
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
    """Vínculo de um responsável (mãe, pai, guardião) com o aluno."""

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
    endereco_id = models.BigIntegerField(null=True, blank=True)
    numero_endereco = models.CharField(max_length=20, null=True, blank=True)
    complemento = models.CharField(max_length=100, null=True, blank=True)
    bairro = models.CharField(max_length=100, null=True, blank=True)
    logradouro = models.CharField(max_length=255, null=True, blank=True)
    cep = models.IntegerField(null=True, blank=True)
    nome_municipio = models.CharField(max_length=100, null=True, blank=True)
    sigla_uf = models.CharField(max_length=2, null=True, blank=True)
    tipo_logradouro = models.CharField(max_length=50, null=True, blank=True)
    data_atualizacao_tabela = models.DateTimeField(null=True, blank=True)
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
    """Vínculo entre o aluno e uma NEE diagnosticada."""

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
    codigo_tipo_recurso = models.SmallIntegerField(null=True, blank=True)
    descricao_tipo_recurso = models.CharField(
        max_length=100,
        null=True,
        blank=True,
    )

    class Meta:
        app_label = "alunos"
        db_table = "necessidade_especial_aluno"
        managed = False

    def __str__(self) -> str:
        return f"Aluno {self.aluno_id} - NEE {self.necessidade_especial_id}"


class Matricula(models.Model):
    """Matrícula do aluno em uma UE (Unidade Escolar) num ano letivo."""

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
    data_situacao_matricula_data_hora = models.DateTimeField(
        null=True,
        blank=True,
    )
    codigo_situacao_matricula = models.SmallIntegerField()
    situacao_matricula = models.CharField(max_length=100)
    origem_atual = models.BooleanField(default=True)

    class Meta:
        app_label = "alunos"
        db_table = "matricula"
        managed = False
        verbose_name = "matrícula"
        verbose_name_plural = "matrículas"

    def __str__(self) -> str:
        return f"{self.codigo_matricula} ({self.ano_letivo})"


class MatriculaTurma(models.Model):
    """Alocação da matrícula em uma turma específica da UE."""

    id = models.BigAutoField(primary_key=True)
    codigo_matricula = models.BigIntegerField(
        db_index=True, null=True, blank=True
    )
    codigo_turma = models.BigIntegerField()
    numero_chamada = models.CharField(max_length=5, null=True, blank=True)
    data_situacao_aluno = models.DateField(null=True, blank=True)
    data_situacao_aluno_data_hora = models.DateTimeField(
        null=True,
        blank=True,
    )
    codigo_situacao_aluno = models.SmallIntegerField(null=True, blank=True)
    codigo_tipo_turma = models.SmallIntegerField(null=True, blank=True)
    data_atualizacao_tabela = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = "alunos"
        db_table = "matricula_turma"
        managed = False
        unique_together = [("codigo_matricula", "codigo_turma")]

    def __str__(self) -> str:
        return f"M: {self.codigo_matricula} - T: {self.codigo_turma}"
