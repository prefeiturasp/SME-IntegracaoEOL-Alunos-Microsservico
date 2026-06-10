"""Testes dos utilitários genéricos do core."""

from datetime import UTC, date, datetime

from django.test import RequestFactory, TestCase
from rest_framework.request import Request

from apps.core.utils import (
    calcular_idade,
    numero_chamada_int,
    query_bool,
    query_int_list,
    to_bool,
    to_datetime,
    to_int,
)


class ToIntTestCase(TestCase):
    """Valida a conversão de parâmetros para inteiro."""

    def test_converte_valor_valido(self) -> None:
        """Verifica que string numérica vira inteiro."""
        self.assertEqual(to_int("123", "codigo"), 123)

    def test_valor_invalido_lanca_value_error(self) -> None:
        """Verifica que valor não numérico lança ValueError."""
        with self.assertRaises(ValueError):
            to_int("abc", "codigo")


class ToBoolTestCase(TestCase):
    """Valida a conversão de parâmetros para booleano."""

    def test_variantes_verdadeiras(self) -> None:
        """Verifica as variantes aceitas como verdadeiro."""
        for valor in ("true", "1", "t", "yes", "sim"):
            self.assertTrue(to_bool(valor, "flag"))

    def test_variantes_falsas(self) -> None:
        """Verifica as variantes aceitas como falso."""
        for valor in ("false", "0", "f", "no", "nao", "não"):
            self.assertFalse(to_bool(valor, "flag"))

    def test_valor_invalido_lanca_value_error(self) -> None:
        """Verifica que valor fora do domínio lança ValueError."""
        with self.assertRaises(ValueError):
            to_bool("talvez", "flag")

    def test_none_lanca_value_error(self) -> None:
        """Verifica que None lança ValueError."""
        with self.assertRaises(ValueError):
            to_bool(None, "flag")  # type: ignore[arg-type]


class ToDatetimeTestCase(TestCase):
    """Valida a conversão de parâmetros para datetime."""

    def test_data_sem_horario(self) -> None:
        """Verifica o formato somente data."""
        self.assertEqual(
            to_datetime("2026-02-03", "data"),
            datetime(2026, 2, 3),
        )

    def test_data_com_horario_e_z(self) -> None:
        """Verifica ISO 8601 com Z tratado como UTC."""
        self.assertEqual(
            to_datetime("2026-02-03T10:00:00Z", "data"),
            datetime(2026, 2, 3, 10, 0, 0, tzinfo=UTC),
        )

    def test_valor_invalido_lanca_value_error(self) -> None:
        """Verifica que valor não ISO lança ValueError."""
        with self.assertRaises(ValueError):
            to_datetime("03/02/2026", "data")


class QueryBoolTestCase(TestCase):
    """Valida a leitura de parâmetro booleano da query string."""

    def setUp(self) -> None:
        """Configura o RequestFactory dos testes."""
        self.factory = RequestFactory()

    def _request(self, query: str) -> Request:
        return Request(self.factory.get(f"/?{query}"))

    def test_ausente_usa_default(self) -> None:
        """Verifica que parâmetro ausente retorna o default."""
        request = self._request("")

        self.assertTrue(query_bool(request, "flag", default=True))
        self.assertFalse(query_bool(request, "flag", default=False))

    def test_valor_informado_sobrescreve_default(self) -> None:
        """Verifica que o valor informado prevalece sobre o default."""
        request = self._request("flag=false")

        self.assertFalse(query_bool(request, "flag", default=True))

    def test_valor_invalido_lanca_value_error(self) -> None:
        """Verifica que valor não booleano lança ValueError."""
        request = self._request("flag=talvez")

        with self.assertRaises(ValueError):
            query_bool(request, "flag", default=True)


class QueryIntListTestCase(TestCase):
    """Valida a extração de listas de inteiros da query string."""

    def setUp(self) -> None:
        """Configura o RequestFactory dos testes."""
        self.factory = RequestFactory()

    def _request(self, query: str) -> Request:
        return Request(self.factory.get(f"/?{query}"))

    def test_extrai_inteiros_ignorando_vazios(self) -> None:
        """Verifica extração de repetidos ignorando entradas vazias."""
        request = self._request("codigos=1&codigos=&codigos=2")

        self.assertEqual(query_int_list(request, "codigos"), [1, 2])

    def test_entrada_invalida_lanca_value_error(self) -> None:
        """Verifica que entrada não numérica lança ValueError."""
        request = self._request("codigos=1&codigos=x")

        with self.assertRaises(ValueError):
            query_int_list(request, "codigos")


class CalcularIdadeTestCase(TestCase):
    """Valida o cálculo de idade em anos completos."""

    def test_calcular_idade_none(self) -> None:
        """Verifica que data de nascimento None resulta em None."""
        self.assertIsNone(calcular_idade(None))

    def test_calcular_idade_aniversario_nao_completo(self) -> None:
        """Verifica que aniversário não atingido subtrai um ano."""
        self.assertEqual(
            calcular_idade(date(2010, 12, 31), referencia=date(2026, 6, 1)),
            15,
        )

    def test_calcular_idade_com_datetime(self) -> None:
        """Verifica que datetime é aceito como data de nascimento."""
        self.assertEqual(
            calcular_idade(datetime(2010, 1, 1), referencia=date(2026, 6, 1)),
            16,
        )


class NumeroChamadaIntTestCase(TestCase):
    """Valida a conversão do número de chamada."""

    def test_converte_valor_valido(self) -> None:
        """Verifica que texto numérico vira inteiro."""
        self.assertEqual(numero_chamada_int("15"), 15)

    def test_vazio_ou_none_resulta_em_none(self) -> None:
        """Verifica que vazio e None preservam ausência."""
        self.assertIsNone(numero_chamada_int(None))
        self.assertIsNone(numero_chamada_int(""))

    def test_valor_invalido_resulta_em_none(self) -> None:
        """Verifica que valor não numérico resulta em None."""
        self.assertIsNone(numero_chamada_int("abc"))
