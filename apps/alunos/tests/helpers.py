"""Helpers compartilhados pelos testes do app alunos."""

from __future__ import annotations

from datetime import date, datetime, timezone

from apps.alunos.models import (
    Aluno,
    Matricula,
    MatriculaTurma,
    NecessidadeEspecialAluno,
    ResponsavelAluno,
    TipoNecessidadeEspecial,
)


def agora() -> datetime:
    """Datetime fixo (UTC) usado em testes."""
    return datetime(2026, 4, 1, tzinfo=timezone.utc)


def seed_alunos() -> dict[int, Aluno]:
    a1 = Aluno.objects.create(
        codigo_aluno=1234567,
        nome="JOAO DA SILVA",
        nome_social=None,
        nome_mae="MARIA DA SILVA",
        sexo="M",
        cpf=None,
        nacionalidade="Brasileira",
        nis="123456789",
        raca_cor="NAO INFORMADO",
        data_nascimento=date(2012, 5, 15),
        data_atualizacao_contato=date(2026, 1, 15),
        possui_deficiencia=False,
    )
    a2 = Aluno.objects.create(
        codigo_aluno=7654321,
        nome="MARIA OLIVEIRA",
        nome_social="MARIA SOCIAL",
        nome_mae="ANA OLIVEIRA",
        sexo="F",
        nacionalidade="Brasileira",
        raca_cor="NAO INFORMADO",
        data_nascimento=date(2014, 3, 10),
        possui_deficiencia=False,
    )
    return {a.codigo_aluno: a for a in (a1, a2)}


def seed_matriculas() -> list[Matricula]:
    seed_alunos()
    m1 = Matricula.objects.create(
        codigo_matricula=998877,
        aluno_id=1234567,
        codigo_ue="100001",
        ano_letivo=2026,
        codigo_situacao_matricula=1,
        situacao_matricula="Ativo",
        data_situacao_matricula=date(2026, 2, 1),
    )
    m2 = Matricula.objects.create(
        codigo_matricula=998878,
        aluno_id=7654321,
        codigo_ue="100001",
        ano_letivo=2026,
        codigo_situacao_matricula=1,
        situacao_matricula="Ativo",
        data_situacao_matricula=date(2026, 2, 1),
    )
    MatriculaTurma.objects.create(
        codigo_matricula=998877,
        codigo_turma=12345,
        numero_chamada="12",
        data_situacao_aluno=date(2026, 2, 1),
    )
    MatriculaTurma.objects.create(
        codigo_matricula=998878,
        codigo_turma=22222,
        numero_chamada="07",
        data_situacao_aluno=date(2026, 2, 1),
    )
    return [m1, m2]


def seed_responsaveis() -> ResponsavelAluno:
    return ResponsavelAluno.objects.create(
        codigo_responsavel=5501,
        aluno_id=1234567,
        tipo_responsavel=1,
        nome="Responsavel Exemplo",
        cpf="12345678901",
        ddd_celular="11",
        numero_celular="977778888",
        email="contato.exemplo@sme.com.br",
        autoriza_sms="S",
        logradouro="Rua das Flores, 100",
        cep=1310200,
    )


def seed_necessidades(
    codigo_aluno: int = 1234567,
) -> NecessidadeEspecialAluno:
    tipo = TipoNecessidadeEspecial.objects.create(
        codigo_necessidade_especial=1,
        descricao="Deficiência Visual",
        codigo_estado=1,
        ativo=True,
    )
    return NecessidadeEspecialAluno.objects.create(
        codigo_necessidade_especial_aluno=10001,
        aluno_id=codigo_aluno,
        necessidade_especial=tipo,
        data_inicio=date(2025, 1, 1),
    )
