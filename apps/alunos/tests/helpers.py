"""Helpers compartilhados pelos testes do app alunos."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import cast

from apps.alunos.models import (
    Aluno,
    Matricula,
    MatriculaTurma,
    NecessidadeEspecialAluno,
    ResponsavelAluno,
    TipoNecessidadeEspecial,
)


def agora() -> datetime:
    """Retorna um datetime fixo para os testes."""
    return datetime(2026, 4, 1, tzinfo=UTC)


def seed_alunos() -> dict[int, Aluno]:
    """Cria dois alunos de teste indexados por código."""
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


def seed_matriculas(origem_atual: bool = True) -> list[Matricula]:
    """Cria alunos, matrículas e vínculos de turma para os testes."""
    seed_alunos()
    m1 = Matricula.objects.create(
        codigo_matricula=998877,
        aluno_id=1234567,
        codigo_ue="100001",
        ano_letivo=2026,
        codigo_situacao_matricula=1,
        situacao_matricula="Ativo",
        data_situacao_matricula=date(2026, 2, 1),
        origem_atual=origem_atual,
    )
    m2 = Matricula.objects.create(
        codigo_matricula=998878,
        aluno_id=7654321,
        codigo_ue="100001",
        ano_letivo=2026,
        codigo_situacao_matricula=1,
        situacao_matricula="Ativo",
        data_situacao_matricula=date(2026, 2, 1),
        origem_atual=origem_atual,
    )
    MatriculaTurma.objects.create(
        codigo_matricula=998877,
        codigo_turma=12345,
        numero_chamada="12",
        data_situacao_aluno=date(2026, 2, 1),
        codigo_situacao_aluno=1,
        codigo_tipo_turma=1,
    )
    MatriculaTurma.objects.create(
        codigo_matricula=998878,
        codigo_turma=22222,
        numero_chamada="07",
        data_situacao_aluno=date(2026, 2, 1),
        codigo_situacao_aluno=1,
        codigo_tipo_turma=1,
    )
    return [m1, m2]


def seed_responsaveis() -> ResponsavelAluno:
    """Cria um responsável vinculado ao aluno 1234567 para os testes."""
    return cast(
        ResponsavelAluno,
        ResponsavelAluno.objects.create(
            codigo_responsavel=5501,
            aluno_id=1234567,
            tipo_responsavel=1,
            nome="Responsavel Exemplo",
            cpf="12345678901",
            ddd_celular="11",
            numero_celular="977778888",
            email="contato.exemplo@sme.com.br",
            autoriza_sms="S",
            endereco_id=123,
            numero_endereco="100",
            complemento="AP 1",
            bairro="Centro",
            logradouro="Rua das Flores",
            cep=1310200,
            nome_municipio="SAO PAULO",
            sigla_uf="SP",
            tipo_logradouro="Rua",
            data_atualizacao_tabela=date(2026, 1, 10),
        ),
    )


def seed_necessidades(
    codigo_aluno: int = 1234567,
) -> NecessidadeEspecialAluno:
    """Cria um tipo e um vínculo de necessidade especial."""
    tipo = TipoNecessidadeEspecial.objects.create(
        codigo_necessidade_especial=1,
        descricao="Deficiência Visual",
        codigo_estado=1,
        ativo=True,
    )
    return cast(
        NecessidadeEspecialAluno,
        NecessidadeEspecialAluno.objects.create(
            codigo_necessidade_especial_aluno=10001,
            aluno_id=codigo_aluno,
            necessidade_especial=tipo,
            data_inicio=date(2025, 1, 1),
        ),
    )
