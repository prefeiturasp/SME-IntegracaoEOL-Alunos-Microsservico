"""Testes dos models read-only do app aluno."""

from __future__ import annotations

from datetime import date

from django.test import TestCase

from apps.alunos.enums import SituacaoMatricula
from apps.alunos.models import (
    Aluno,
    Matricula,
    MatriculaTurma,
    NecessidadeEspecialAluno,
    ResponsavelAluno,
    TipoNecessidadeEspecial,
)


class AlunoTestCase(TestCase):
    """Valida representação e mapeamento do model Aluno."""

    def test_str(self) -> None:
        """Verifica a string amigável do aluno."""
        aluno = Aluno(
            codigo_aluno=1234567,
            nome="JOAO DA SILVA",
            data_nascimento=date(2012, 5, 15),
        )
        self.assertEqual(str(aluno), "1234567 - JOAO DA SILVA")

    def test_db_table(self) -> None:
        """Verifica o nome da tabela mapeada."""
        self.assertEqual(Aluno._meta.db_table, "aluno")


class TipoNecessidadeEspecialTestCase(TestCase):
    """Valida representação do model TipoNecessidadeEspecial."""

    def test_str(self) -> None:
        """Verifica que a string amigável inclui código e descrição."""
        tipo = TipoNecessidadeEspecial(
            codigo_necessidade_especial=1,
            descricao="Deficiência Visual",
        )
        self.assertEqual(str(tipo), "1 - Deficiência Visual")


class MatriculaTestCase(TestCase):
    """Valida representação do model Matricula."""

    def test_str(self) -> None:
        """Verifica que a string amigável inclui código e ano letivo."""
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
    """Valida representação do model MatriculaTurma."""

    def test_str(self) -> None:
        """Verifica que a string amigável inclui matrícula e turma."""
        mt = MatriculaTurma(
            codigo_matricula=998877,
            codigo_turma=12345,
            numero_chamada="12",
        )
        self.assertEqual(str(mt), "M: 998877 - T: 12345")


class NecessidadeEspecialAlunoTestCase(TestCase):
    """Valida representação do model NecessidadeEspecialAluno."""

    def test_str(self) -> None:
        """Verifica que a string amigável inclui aluno e necessidade."""
        n = NecessidadeEspecialAluno(
            codigo_necessidade_especial_aluno=1,
            aluno_id=1234567,
            necessidade_especial_id=2,
        )
        resultado = str(n)
        self.assertIn("1234567", resultado)
        self.assertIn("2", resultado)


class ResponsavelAlunoTestCase(TestCase):
    """Valida representação do model ResponsavelAluno."""

    def test_str(self) -> None:
        """Verifica que a string amigável inclui nome e aluno vinculado."""
        r = ResponsavelAluno(
            codigo_responsavel=5501,
            aluno_id=1234567,
            nome="João Exemplo",
        )
        self.assertEqual(str(r), "João Exemplo (Aluno: 1234567)")


class SituacaoMatriculaTestCase(TestCase):
    """Valida a tradução de códigos em SituacaoMatricula.get_descricao."""

    def test_descricao_none(self) -> None:
        """Verifica que código None resulta em 'Não Informada'."""
        self.assertEqual(
            SituacaoMatricula.get_descricao(None), "Não Informada"
        )

    def test_descricao_int_valido(self) -> None:
        """Verifica a tradução de códigos inteiros válidos."""
        self.assertEqual(SituacaoMatricula.get_descricao(1), "Ativo")
        self.assertEqual(SituacaoMatricula.get_descricao(5), "Concluído")

    def test_descricao_string_numerica(self) -> None:
        """Verifica que strings numéricas são aceitas como código."""
        self.assertEqual(SituacaoMatricula.get_descricao("2"), "Desistente")

    def test_descricao_codigo_fora_do_dominio(self) -> None:
        """Verifica que código fora do enum cai no fallback PRODAM."""
        resultado = SituacaoMatricula.get_descricao(99)
        self.assertIn("PRODAM", resultado)

    def test_descricao_string_invalida(self) -> None:
        """Verifica que strings não numéricas caem no fallback PRODAM."""
        resultado = SituacaoMatricula.get_descricao("abc")
        self.assertIn("PRODAM", resultado)
