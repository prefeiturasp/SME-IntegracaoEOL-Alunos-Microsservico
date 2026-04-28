"""Testes dos models read-only do app alunos — __str__ e shape básico."""

from __future__ import annotations

from datetime import date

from django.test import TestCase

from apps.alunos.models import (
    Aluno,
    Matricula,
    MatriculaTurma,
    NecessidadeEspecialAluno,
    ResponsavelAluno,
    TipoNecessidadeEspecial,
)


class AlunoTestCase(TestCase):
    def test_str(self) -> None:
        aluno = Aluno(
            codigo_aluno=1234567,
            nome="JOAO DA SILVA",
            data_nascimento=date(2012, 5, 15),
        )
        self.assertEqual(str(aluno), "1234567 - JOAO DA SILVA")

    def test_db_table(self) -> None:
        self.assertEqual(Aluno._meta.db_table, "aluno")


class TipoNecessidadeEspecialTestCase(TestCase):
    def test_str(self) -> None:
        tipo = TipoNecessidadeEspecial(
            codigo_necessidade_especial=1,
            descricao="Deficiência Visual",
        )
        self.assertEqual(str(tipo), "1 - Deficiência Visual")


class MatriculaTestCase(TestCase):
    def test_str(self) -> None:
        m = Matricula(
            codigo_matricula=998877,
            aluno_id=1234567,
            codigo_ue="100001",
            ano_letivo=2026,
            codigo_situacao_matricula=1,
            situacao_matricula="Ativo",
        )
        self.assertEqual(str(m), "998877 (2026)")


class MatriculaTurmaTestCase(TestCase):
    def test_str(self) -> None:
        mt = MatriculaTurma(
            codigo_matricula=998877,
            codigo_turma=12345,
            numero_chamada="12",
        )
        self.assertEqual(str(mt), "M: 998877 - T: 12345")


class NecessidadeEspecialAlunoTestCase(TestCase):
    def test_str(self) -> None:
        n = NecessidadeEspecialAluno(
            codigo_necessidade_especial_aluno=1,
            aluno_id=1234567,
            necessidade_especial_id=2,
        )
        resultado = str(n)
        self.assertIn("1234567", resultado)
        self.assertIn("2", resultado)


class ResponsavelAlunoTestCase(TestCase):
    def test_str(self) -> None:
        r = ResponsavelAluno(
            codigo_responsavel=5501,
            aluno_id=1234567,
            nome="João Exemplo",
        )
        self.assertEqual(str(r), "João Exemplo (Aluno: 1234567)")
