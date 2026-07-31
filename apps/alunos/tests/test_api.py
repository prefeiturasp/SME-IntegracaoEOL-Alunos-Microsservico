"""Testes dos endpoints HTTP do app alunos."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import cast
from unittest.mock import MagicMock, patch
from urllib.parse import urlencode

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.alunos.models import (
    DadosAlunoAcompanhamentoEscolar,
    Matricula,
    MatriculaAnoLetivo,
    MatriculaComponenteCurricularAnoLetivo,
    MatriculaTurma,
    ResponsavelAluno,
)
from apps.alunos.tests.helpers import (
    seed_alunos,
    seed_matriculas,
    seed_matriculas_ano_anterior,
    seed_matriculas_com_responsaveis,
    seed_necessidades,
    seed_responsaveis,
    seed_turma_data_aula,
)


def _autenticado() -> APIClient:
    """Retorna um APIClient com header de API key configurado."""
    cliente = APIClient()
    cliente.credentials(HTTP_X_API_KEY="test-api-key")
    return cliente


class AutenticacaoTestCase(TestCase):
    """Valida as respostas de autenticação dos endpoints."""

    def test_sem_api_key_retorna_401(self) -> None:
        """Verifica que requisição sem API key retorna 401."""
        cliente = APIClient()
        url = reverse("alunos-por-codigos")
        resp = cliente.get(url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_api_key_invalida_retorna_403(self) -> None:
        """Verifica que API key incorreta retorna 403."""
        cliente = APIClient()
        cliente.credentials(HTTP_X_API_KEY="errada")
        url = reverse("alunos-por-codigos")
        resp = cliente.get(url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


class A01TurmasDoAlunoTestCase(TestCase):
    """Valida o endpoint de turmas do aluno."""

    def test_retorna_turmas(self) -> None:
        """Verifica shape do payload e omissão de campos fora do domínio."""
        seed_matriculas_com_responsaveis()
        with patch(
            "django.utils.timezone.now",
            return_value=datetime(2026, 6, 1, tzinfo=UTC),
        ):
            url = reverse(
                "busca-turmas-do-aluno", kwargs={"codigo_aluno": "1234567"}
            )
            resp = _autenticado().get(url)
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["codigo_aluno"], 1234567)
        self.assertEqual(body[0]["codigo_turma"], 12345)
        self.assertIn("data_atualizacao_tabela", body[0])
        self.assertIn("codigo_tipo_turma", body[0])
        self.assertIn("nome_responsavel", body[0])

    def test_aluno_invalido_400(self) -> None:
        """Verifica que codigo_aluno não numérico retorna 400."""
        url = reverse("busca-turmas-do-aluno", kwargs={"codigo_aluno": "abc"})
        resp = _autenticado().get(url)
        self.assertEqual(resp.status_code, 400)

    def test_aluno_inexistente_404(self) -> None:
        """Verifica que aluno sem matrículas retorna 404."""
        url = reverse(
            "busca-turmas-do-aluno", kwargs={"codigo_aluno": "9999999"}
        )
        resp = _autenticado().get(url)
        self.assertEqual(resp.status_code, 404)


class A04A05A06AutocompleteApiTestCase(TestCase):
    """Valida os endpoints de listagem e autocomplete por UE."""

    def test_a04_retorna_alunos(self) -> None:
        """Verifica a listagem de alunos da UE no ano letivo."""
        seed_matriculas()
        url = reverse(
            "buscar-alunos-da-ue",
            kwargs={"codigo_ue": "100001", "ano_letivo": "2026"},
        )
        resp = _autenticado().get(url)
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(len(body), 2)
        self.assertEqual(body[0]["tipo_turno"], 2)
        self.assertEqual(body[0]["turma_nome"], "5A")
        self.assertEqual(body[0]["etapa_ensino"], 5)
        self.assertEqual(body[0]["ciclo_ensino"], 2)
        self.assertEqual(body[0]["desc_etapa_ensino"], "Ensino Fundamental")

    def test_a05_autocomplete(self) -> None:
        """Verifica o autocomplete por substring do nome."""
        seed_matriculas()
        url = reverse(
            "autocomplete-alunos-ue",
            kwargs={"codigo_ue": "100001", "ano_letivo": "2026"},
        )
        resp = _autenticado().get(url + "?nome_aluno=JOAO")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["nome_aluno"], "JOAO DA SILVA")

    def test_a06_exige_nome_minimo(self) -> None:
        """Verifica que nome com menos de 3 caracteres retorna 400."""
        url = reverse(
            "autocomplete-alunos-ativos", kwargs={"ue_codigo": "100001"}
        )
        resp = _autenticado().get(url + "?aluno_nome=ab")
        self.assertEqual(resp.status_code, 400)


class A07A08A09TurmaApiTestCase(TestCase):
    """Valida endpoints de totais e alunos ativos por turma."""

    def _url_total(self) -> str:
        """Monta a URL do EP6 com os parâmetros de rota padrão."""
        return reverse(
            "total-alunos-ativos-por-periodo",
            kwargs={
                "ano_turma": "5",
                "ano_letivo": "2026",
                "data_inicio": "2026-01-01",
                "data_fim": "2026-12-31",
            },
        )

    def test_a07_total(self) -> None:
        """Verifica a contagem de alunos ativos no período."""
        seed_matriculas()
        resp = _autenticado().get(
            self._url_total() + "?ue_id=100001&modalidades=5"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["quantidade"], 2)

    def test_a07_sem_modalidades_replica_erro_legado(self) -> None:
        """Verifica que a ausência de modalidades replica o erro do legado."""
        seed_matriculas()
        resp = _autenticado().get(self._url_total())
        self.assertEqual(resp.status_code, 400)
        self.assertIn("conexão com o banco do EOL", resp.json())

    def test_a07_sem_resultado_replica_erro_legado(self) -> None:
        """Verifica que a ausência de resultado replica o erro do legado."""
        seed_matriculas()
        resp = _autenticado().get(self._url_total() + "?modalidades=99")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("comportamento inesperado", resp.json())

    def test_a09_alunos_ativos(self) -> None:
        """Verifica os alunos ativos na turma informada."""
        seed_matriculas()
        url = reverse("alunos-ativos-turma", kwargs={"codigo_turma": "12345"})
        resp = _autenticado().get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 1)


class AlunosTurmaApiTestCase(TestCase):
    """Valida o endpoint unificado de alunos de uma turma."""

    def _path(self, codigo_turma: str) -> str:
        return cast(
            str,
            reverse(
                "alunos-turma",
                kwargs={"codigo_turma": codigo_turma},
            ),
        )

    def _url(self, codigo_turma: str, **params: str) -> str:
        query = {"considerar_inativos": "false", **params}
        return f"{self._path(codigo_turma)}?{urlencode(query)}"

    # Ticks .NET equivalentes a 2026-06-01, após as datas do seed.
    TICKS_2026_06_01 = "639158688000000000"

    def test_retorna_alunos_em_snake_case(self) -> None:
        """Verifica 200, dedup por aluno e contrato em snake_case."""
        codigo_turma = seed_turma_data_aula()
        resp = _autenticado().get(
            self._url(str(codigo_turma), data_aula_ticks=self.TICKS_2026_06_01)
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "application/json")
        body = resp.json()
        self.assertEqual(len(body), 2)
        joao = {item["codigo_aluno"]: item for item in body}[1234567]
        self.assertEqual(joao["nome_aluno"], "JOAO DA SILVA")
        self.assertEqual(joao["codigo_dre"], "108800")
        self.assertEqual(joao["sequencia"], 1)
        self.assertEqual(joao["celular_responsavel"], "11988887777")
        self.assertIn("data_situacao", joao)
        self.assertIn("data_matricula", joao)

    def test_sem_query_params_retorna_todos(self) -> None:
        """Verifica 200 sem filtros de data, com a turma completa."""
        codigo_turma = seed_turma_data_aula()
        resp = _autenticado().get(self._url(str(codigo_turma)))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 2)

    def test_sem_api_key_retorna_401(self) -> None:
        """Verifica que requisição sem API key retorna 401."""
        resp = APIClient().get(self._url("3015603"))
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_codigo_turma_invalido_retorna_400(self) -> None:
        """Verifica que codigo_turma não numérico retorna 400."""
        resp = _autenticado().get(self._url("abc"))
        self.assertEqual(resp.status_code, 400)

    def test_ticks_invalido_retorna_400(self) -> None:
        """Verifica que ticks não numérico retorna 400."""
        resp = _autenticado().get(self._url("3015603", data_aula_ticks="abc"))
        self.assertEqual(resp.status_code, 400)

    def test_ticks_fora_de_range_retorna_400(self) -> None:
        """Verifica que ticks fora do range de datetime retorna 400."""
        resp = _autenticado().get(
            self._url("3015603", data_aula_ticks=str(10**19))
        )
        self.assertEqual(resp.status_code, 400)

    def test_ticks_negativo_retorna_400(self) -> None:
        """Verifica que ticks negativo retorna 400."""
        resp = _autenticado().get(self._url("3015603", data_aula_ticks="-1"))
        self.assertEqual(resp.status_code, 400)

    def test_ticks_zero_retorna_200(self) -> None:
        """Verifica que ticks zero retorna 200 sem filtro por data."""
        codigo_turma = seed_turma_data_aula()
        resp = _autenticado().get(
            self._url(str(codigo_turma), data_aula_ticks="0")
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 2)

    def test_ticks_zero_e_primeira_sequencia_ordena_chamada(self) -> None:
        """Verifica ordenação por chamada com ticks zero e sequência 1."""
        codigo_turma = seed_turma_data_aula()
        MatriculaTurma.objects.filter(codigo_matricula=700002).update(
            sequencia=1
        )
        resp = _autenticado().get(
            self._url(str(codigo_turma), data_aula_ticks="0", sequencia="1")
        )
        self.assertEqual(resp.status_code, 200)
        codigos = [item["numero_aluno_chamada"] for item in resp.json()]
        self.assertEqual(codigos, ["07", "12"])

    def test_sequencia_filtra_via_query_param(self) -> None:
        """Verifica filtro de sequência via query param inteiro."""
        codigo_turma = seed_turma_data_aula()
        resp = _autenticado().get(
            self._url(
                str(codigo_turma),
                data_aula_ticks=self.TICKS_2026_06_01,
                sequencia="1",
            )
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["codigo_aluno"], 1234567)

    def test_sequencia_invalida_retorna_400(self) -> None:
        """Verifica que sequência não inteira retorna 400."""
        resp = _autenticado().get(self._url("3015603", sequencia="abc"))
        self.assertEqual(resp.status_code, 400)

    def test_considerar_inativos_traz_todas_situacoes(self) -> None:
        """Verifica que considerar inativos traz situações fora do conjunto."""
        codigo_turma = seed_turma_data_aula()
        MatriculaTurma.objects.filter(codigo_matricula=700002).update(
            codigo_situacao_aluno=14
        )
        resp = _autenticado().get(
            self._path(str(codigo_turma)),
            {
                "data_aula_ticks": self.TICKS_2026_06_01,
                "considerar_inativos": "true",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 2)

    def test_considerar_inativos_false_restringe_situacoes(self) -> None:
        """Verifica que considerar inativos falso exclui fora do conjunto."""
        codigo_turma = seed_turma_data_aula()
        MatriculaTurma.objects.filter(codigo_matricula=700002).update(
            codigo_situacao_aluno=14
        )
        resp = _autenticado().get(
            self._path(str(codigo_turma)),
            {
                "data_aula_ticks": self.TICKS_2026_06_01,
                "considerar_inativos": "false",
            },
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["codigo_aluno"], 1234567)

    def test_sem_considerar_inativos_retorna_400(self) -> None:
        """Verifica que considerar_inativos é obrigatório."""
        codigo_turma = seed_turma_data_aula()
        resp = _autenticado().get(
            self._path(str(codigo_turma)),
            {"data_aula_ticks": self.TICKS_2026_06_01},
        )
        self.assertEqual(resp.status_code, 400)

    def test_filtra_por_codigo_aluno(self) -> None:
        """Verifica que codigo_aluno restringe o resultado ao aluno."""
        codigo_turma = seed_turma_data_aula()
        resp = _autenticado().get(
            self._url(str(codigo_turma), codigo_aluno="7654321")
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["codigo_aluno"], 7654321)

    def test_data_matricula_ordena_por_nome(self) -> None:
        """Verifica ordenação por nome ao informar data_matricula_ticks."""
        codigo_turma = seed_turma_data_aula()
        resp = _autenticado().get(
            self._url(
                str(codigo_turma),
                data_matricula_ticks=self.TICKS_2026_06_01,
            )
        )
        self.assertEqual(resp.status_code, 200)
        nomes = [item["nome_aluno"] for item in resp.json()]
        self.assertEqual(nomes, sorted(nomes))

    def test_data_matricula_ticks_invalido_retorna_400(self) -> None:
        """Verifica que data_matricula_ticks inválido retorna 400."""
        resp = _autenticado().get(
            self._url("3015603", data_matricula_ticks="abc")
        )
        self.assertEqual(resp.status_code, 400)

    def test_turma_vazia_retorna_lista_vazia(self) -> None:
        """Verifica que turma sem alunos retorna 200 com lista vazia."""
        resp = _autenticado().get(
            self._url("999999", data_aula_ticks=self.TICKS_2026_06_01)
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])


class TurmasRotaResolucaoTestCase(TestCase):
    """Garante que as rotas de turma não colidem entre si."""

    def test_rota_ativos_resolve_para_view_propria(self) -> None:
        """Verifica que turmas/<codigo>/ativos não cai na rota genérica."""
        url = reverse("alunos-ativos-turma", kwargs={"codigo_turma": "30156"})
        self.assertTrue(url.endswith("/turmas/30156/ativos"))

    def test_rota_ativos_periodo_resolve_para_view_propria(self) -> None:
        """Verifica a rota de período por data de referência."""
        url = reverse(
            "alunos-ativos-periodo-turma",
            kwargs={"codigo_turma": "30156", "data_referencia_fim": "2026"},
        )
        self.assertTrue(url.endswith("/turmas/30156/ativos/2026"))

    def test_rota_unificada_resolve_para_view_generica(self) -> None:
        """Verifica que turmas/<codigo>/ resolve para a rota unificada."""
        url = reverse("alunos-turma", kwargs={"codigo_turma": "30156"})
        self.assertTrue(url.endswith("/turmas/30156/"))


class QuantidadeMatriculasTurmasPeriodoApiTestCase(TestCase):
    """Valida o endpoint POST de quantidade de matrículas-turma."""

    def _url(self) -> str:
        return reverse("quantidade-matriculas-turmas-periodo")

    def test_conta_alocacoes_no_periodo(self) -> None:
        """Verifica a contagem de alocações válidas até a data."""
        codigo_turma = seed_turma_data_aula()
        # Ticks de 2026-12-31 (data bem posterior às alocações do seed).
        ticks = 639_000_000_000_000_000 + 10_000_000 * 60 * 60 * 24 * 365 * 26
        resp = _autenticado().post(
            self._url(),
            data={"codigos_turmas": [codigo_turma], "data_fim": ticks},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("quantidade", resp.json())

    def test_codigos_turmas_ausente_retorna_400(self) -> None:
        """Verifica erro 400 quando o corpo não traz a lista de turmas."""
        resp = _autenticado().post(
            self._url(), data={"data_fim": 1}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_data_fim_zero_retorna_400(self) -> None:
        """Verifica erro 400 quando a data de fim é zero."""
        resp = _autenticado().post(
            self._url(),
            data={"codigos_turmas": [1], "data_fim": 0},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class AcompanhamentoEscolarTurmaApiTestCase(TestCase):
    """Valida o endpoint de acompanhamento escolar da turma."""

    def _url(self, codigo_turma: str) -> str:
        return reverse(
            "acompanhamento-escolar-turma",
            kwargs={"codigo_turma": codigo_turma},
        )

    def test_lista_aluno_e_responsavel(self) -> None:
        """Verifica a listagem de aluno com responsável vigente."""
        from apps.alunos.tests.helpers import seed_responsaveis

        codigo_turma = seed_turma_data_aula()
        seed_responsaveis()
        resp = _autenticado().get(self._url(str(codigo_turma)))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        corpo = resp.json()
        self.assertEqual(len(corpo), 1)
        self.assertEqual(corpo[0]["codigo_eol_aluno"], 1234567)
        self.assertEqual(corpo[0]["cpf"], 12345678901)

    def test_turma_sem_responsavel_retorna_lista_vazia(self) -> None:
        """Verifica que turma sem responsável vigente devolve lista vazia."""
        codigo_turma = seed_turma_data_aula()
        ResponsavelAluno.objects.filter(aluno_id=1234567).update(
            data_fim_vinculo=date(2026, 3, 1)
        )
        resp = _autenticado().get(self._url(str(codigo_turma)))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json(), [])

    def test_codigo_turma_nao_numerico_retorna_400(self) -> None:
        """Verifica erro 400 para código de turma não numérico."""
        resp = _autenticado().get(self._url("abc"))
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class TodosAlunosTurmaApiTestCase(TestCase):
    """Valida o endpoint de histórico de vínculos com a turma."""

    def _url(self, codigo_turma: str) -> str:
        return reverse(
            "todos-alunos-turma",
            kwargs={"codigo_turma": codigo_turma},
        )

    def test_lista_vinculos_da_turma(self) -> None:
        """Verifica a listagem dos vínculos da turma."""
        codigo_turma = seed_turma_data_aula()
        resp = _autenticado().get(self._url(str(codigo_turma)))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.json()), 2)

    def test_filtra_por_codigo_aluno(self) -> None:
        """Verifica o filtro por código de aluno."""
        codigo_turma = seed_turma_data_aula()
        resp = _autenticado().get(
            f"{self._url(str(codigo_turma))}?codigo_aluno=1234567"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        corpo = resp.json()
        self.assertEqual(len(corpo), 1)
        self.assertEqual(corpo[0]["codigo_aluno"], 1234567)

    def test_turma_sem_vinculo_retorna_lista_vazia(self) -> None:
        """Verifica que turma sem vínculo devolve 200 com lista vazia."""
        seed_turma_data_aula()
        resp = _autenticado().get(self._url("9999999"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json(), [])

    def test_codigo_turma_nao_numerico_retorna_400(self) -> None:
        """Verifica erro 400 para código de turma não numérico."""
        resp = _autenticado().get(self._url("abc"))
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class MatriculasTurmasAlunoApiTestCase(TestCase):
    """Valida o endpoint de matrículas-turma do aluno."""

    def _url(self, codigo_aluno: str = "1234567") -> str:
        return reverse(
            "matriculas-turmas-aluno",
            kwargs={"codigo_aluno": codigo_aluno},
        )

    def test_lista_matriculas_do_aluno(self) -> None:
        """Verifica a listagem de matrículas-turma do aluno."""
        seed_turma_data_aula()
        resp = _autenticado().get(self._url())
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        corpo = resp.json()
        self.assertEqual(len(corpo), 1)
        self.assertEqual(corpo[0]["codigo_aluno"], 1234567)
        self.assertEqual(corpo[0]["codigo_matricula"], 700001)

    def test_ano_letivo_sem_correspondencia_retorna_lista_vazia(self) -> None:
        """Verifica que ano letivo sem alocação devolve 200 com lista vazia."""
        seed_turma_data_aula()
        MatriculaTurma.objects.all().update(ano_letivo_turma=2026)
        resp = _autenticado().get(f"{self._url()}?ano_letivo=2024")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json(), [])

    def test_data_aula_ticks_zero_restringe_resultado(self) -> None:
        """Verifica que ticks zero restringe o resultado a vazio."""
        seed_turma_data_aula()
        resp = _autenticado().get(f"{self._url()}?data_aula_ticks=0")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json(), [])

    def test_codigo_aluno_nao_numerico_retorna_400(self) -> None:
        """Verifica erro 400 para código de aluno não numérico."""
        resp = _autenticado().get(self._url("abc"))
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class A10A13A14ApiTestCase(TestCase):
    """Valida endpoints de necessidades, informações e alunos da turma."""

    def test_a10_necessidades(self) -> None:
        """Verifica a listagem de necessidades especiais do aluno."""
        seed_alunos()
        seed_necessidades()
        url = reverse(
            "necessidades-especiais-aluno",
            kwargs={"codigo_aluno": "1234567"},
        )
        resp = _autenticado().get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 1)

    def test_a13_informacoes_shape_legado_enriquecido(self) -> None:
        """Verifica campos enriquecidos no payload."""
        seed_alunos()
        seed_responsaveis()
        url = reverse("informacoes-aluno", kwargs={"codigo_aluno": "1234567"})
        resp = _autenticado().get(url)
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["codigo_aluno"], 1234567)
        self.assertEqual(body["nome_aluno"], "JOAO DA SILVA")
        self.assertIn("endereco", body)
        self.assertEqual(body["endereco"]["id"], 123)
        self.assertIn("cns", body)

    def test_a13_inexistente_404(self) -> None:
        """Verifica que aluno inexistente retorna 404."""
        url = reverse("informacoes-aluno", kwargs={"codigo_aluno": "1111111"})
        resp = _autenticado().get(url)
        self.assertEqual(resp.status_code, 404)

    def test_a14_alunos_da_turma(self) -> None:
        """Verifica a listagem de alunos da turma informada."""
        seed_matriculas()
        url = reverse(
            "informacoes-alunos-turma",
            kwargs={"codigo_turma": "12345"},
        )
        resp = _autenticado().get(url)
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["codigo_aluno"], 1234567)


class A19A20A21ResponsavelApiTestCase(TestCase):
    """Valida os endpoints de consulta de responsáveis."""

    def test_a19_lista(self) -> None:
        """Verifica a listagem de responsáveis vigentes por DRE/UE/ano."""
        seed_matriculas_com_responsaveis()
        url = reverse("responsaveis-dre-ue-turma")
        resp = _autenticado().get(
            url + "?codigo_dre=108&codigo_ue=100001&ano_letivo=2026"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 1)

    def test_a19_sem_dados_retorna_lista_vazia(self) -> None:
        """Verifica que UE sem responsáveis devolve lista vazia."""
        url = reverse("responsaveis-dre-ue-turma")
        resp = _autenticado().get(url + "?codigo_dre=108&codigo_ue=999")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])

    def test_a19_sem_codigo_dre_aceita(self) -> None:
        """Verifica que a consulta funciona sem codigo_dre."""
        seed_matriculas_com_responsaveis()
        url = reverse("responsaveis-dre-ue-turma")
        resp = _autenticado().get(url + "?codigo_ue=100001&ano_letivo=2026")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 1)

    def test_a19_so_codigo_dre_filtra_responsaveis(self) -> None:
        """Verifica a consulta apenas com o filtro de DRE."""
        seed_matriculas_com_responsaveis()
        url = reverse("responsaveis-dre-ue-turma")
        resp = _autenticado().get(url + "?codigo_dre=108")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 1)

    def test_a20_dados_completos(self) -> None:
        """Verifica o retorno completo do responsável pelo CPF."""
        seed_alunos()
        seed_responsaveis()
        url = reverse(
            "dados-responsavel",
            kwargs={"cpf_responsavel": "12345678901"},
        )
        resp = _autenticado().get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 1)

    def test_a21_resumido(self) -> None:
        """Verifica o retorno resumido do responsável pelo CPF."""
        seed_alunos()
        seed_responsaveis()
        url = reverse(
            "dados-responsavel-resumido",
            kwargs={"cpf_responsavel": "12345678901"},
        )
        resp = _autenticado().get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["cpf"], "12345678901")
        self.assertEqual(resp.json()["data_nascimento"], "1980-05-20")
        self.assertEqual(resp.json()["nome_mae"], "Mae do Responsavel")

    def test_dados_responsavel_no_contrato_legado(self) -> None:
        """Verifica os 27 campos do contrato completo."""
        seed_matriculas_com_responsaveis()
        url = reverse(
            "dados-responsavel-contrato",
            kwargs={"cpf_responsavel": "12345678901"},
        )

        with patch(
            "apps.alunos.services.responsaveis.timezone.now",
            return_value=datetime(2026, 6, 1, tzinfo=UTC),
        ):
            resp = _autenticado().get(url)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 1)
        self.assertEqual(
            list(resp.json()[0]),
            [
                "id",
                "cpf",
                "email",
                "nome",
                "tipo_responsavel",
                "nome_social_aluno",
                "data_nascimento_aluno",
                "data_nascimento",
                "data_atualizacao",
                "nome_mae",
                "tipo_sigilo",
                "ddd_celular",
                "numero_celular",
                "nome_aluno",
                "codigo_aluno",
                "numero_rg",
                "digito_rg",
                "uf_rg",
                "cpf_confere",
                "tipo_turno_celular",
                "ddd_telefone_fixo",
                "numero_telefone_fixo",
                "tipo_turno_telefone_fixo",
                "ddd_telefone_comercial",
                "numero_telefone_comercial",
                "tipo_turno_telefone_comercial",
                "autoriza_envio_sms",
            ],
        )
        self.assertEqual(resp.json()[0]["codigo_aluno"], "1234567")
        self.assertEqual(resp.json()[0]["digito_rg"], "4   ")


class A22A23EscritaApiTestCase(TestCase):
    """Valida os endpoints de escrita de responsável."""

    def test_a22_atualiza_via_put(self) -> None:
        """Verifica a atualização de telefones pelo PUT."""
        seed_alunos()
        seed_responsaveis()
        url = reverse(
            "responsavel-aluno",
            kwargs={
                "codigo_aluno": "1234567",
                "cpf_responsavel": "12345678901",
            },
        )
        resp = _autenticado().put(
            url,
            data={
                "codigo_aluno": 1234567,
                "cpf": "12345678901",
                "email": "novo@sme.com.br",
                "ddd_celular": "11",
                "numero_celular": "999996666",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIs(resp.json(), True)

    def test_a23_atualiza_via_post(self) -> None:
        """Verifica a atualização cadastral pelo POST."""
        seed_alunos()
        seed_responsaveis()
        url = reverse(
            "responsavel-aluno",
            kwargs={
                "codigo_aluno": "1234567",
                "cpf_responsavel": "12345678901",
            },
        )
        resp = _autenticado().post(
            url,
            data={
                "cpf": "12345678901",
                "email": "novo2@sme.com.br",
                "data_nascimento": "1981-06-21T00:00:00",
                "nome_mae": "Mae Atualizada",
                "ddd_celular": "11",
                "numero_celular": "988887777",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIs(resp.json(), True)

    def test_escritas_inexistentes_retornam_falso(self) -> None:
        """Verifica que os verbos não criam vínculos ausentes."""
        seed_alunos()
        url = reverse(
            "responsavel-aluno",
            kwargs={
                "codigo_aluno": "1234567",
                "cpf_responsavel": "55544433322",
            },
        )

        post = _autenticado().post(url, data={}, format="json")
        put = _autenticado().put(url, data={}, format="json")

        self.assertEqual(post.status_code, 200)
        self.assertEqual(put.status_code, 200)
        self.assertIs(post.json(), False)
        self.assertIs(put.json(), False)


class ObterNomesAlunosApiTestCase(TestCase):
    """Valida a consulta de nomes por códigos de alunos."""

    def test_retorna_todas_as_situacoes_de_matricula_turma(self) -> None:
        """Verifica o contrato e a ausência de filtro por situação."""
        seed_matriculas()
        MatriculaTurma.objects.create(
            codigo_matricula=998877,
            codigo_turma=54321,
            codigo_situacao_aluno=14,
            codigo_tipo_turma=1,
            sequencia=2,
            origem_atual=True,
            ano_letivo_turma=2026,
        )
        url = reverse("obter-nomes-alunos-contrato")

        resp = _autenticado().post(
            url,
            data={
                "codigos_alunos": ["1234567"],
                "ano_letivo": 2026,
            },
            format="json",
        )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 2)
        self.assertEqual(
            list(resp.json()[0]),
            [
                "nome_aluno",
                "situacao_matricula",
                "codigo_escola",
                "data_matricula",
                "codigo_aluno",
                "codigo_turma",
                "codigo_situacao_matricula",
            ],
        )
        self.assertEqual(
            {item["codigo_situacao_matricula"] for item in resp.json()},
            {1, 14},
        )

    def test_lista_vazia_retorna_erro_legado(self) -> None:
        """Verifica mensagem e status para lista vazia."""
        url = reverse("obter-nomes-alunos-contrato")

        resp = _autenticado().post(
            url,
            data={"codigos_alunos": [], "ano_letivo": 2026},
            format="json",
        )

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(
            resp.json(), "Os códigos dos alunos são obrigatórios."
        )


class A27FiliacaoApiTestCase(TestCase):
    """Valida o endpoint de filiação do responsável do aluno."""

    def test_retorna_responsaveis_de_filiacao(self) -> None:
        """Verifica o retorno dos responsáveis de filiação."""
        seed_alunos()
        seed_responsaveis()
        url = reverse("filiacao-aluno", kwargs={"codigo_aluno": "1234567"})
        resp = _autenticado().get(url)
        self.assertEqual(resp.status_code, 200)
        dados = resp.json()
        self.assertEqual(len(dados), 1)
        self.assertEqual(dados[0]["nome_responsavel"], "Responsavel Exemplo")
        self.assertEqual(dados[0]["ddd_residencial"], "11")
        self.assertEqual(dados[0]["endereco"]["id"], 123)


class A12AlunosPorCodigosApiTestCase(TestCase):
    """Valida o endpoint de busca de alunos por códigos."""

    def test_retorna_alunos(self) -> None:
        """Verifica os alunos retornados para os códigos informados."""
        seed_matriculas()
        url = reverse("alunos-por-codigos")
        resp = _autenticado().get(url + "?codigos_aluno=1234567")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["codigo_aluno"], 1234567)

    def test_sem_codigos_retorna_vazio(self) -> None:
        """Verifica que entrada vazia em codigos_aluno gera saída vazia."""
        url = reverse("alunos-por-codigos")
        resp = _autenticado().get(url + "?codigos_aluno=")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])


class MatriculasApiTestCase(TestCase):
    """Valida os endpoints de matrículas (consolidação e agregações)."""

    def test_m01(self) -> None:
        """Verifica a consolidação do ano atual por UE."""
        seed_matriculas()
        url = reverse("matriculas-ano-atual")
        resp = _autenticado().get(url + "?ano_letivo=2026&ue_codigo=100001")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 2)

    def test_m01_sem_parametros_400(self) -> None:
        """Verifica que faltar ano_letivo/ue_codigo retorna 400."""
        url = reverse("matriculas-ano-atual")
        resp = _autenticado().get(url)
        self.assertEqual(resp.status_code, 400)

    def test_m02(self) -> None:
        """Verifica a consolidação histórica no contrato publicado."""
        seed_matriculas_ano_anterior()
        url = reverse("matriculas-anos-anteriores")
        resp = _autenticado().get(url + "?ano_letivo=2025&ue_codigo=100001")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.json(), [{"turma_codigo": "54321", "quantidade": 27}]
        )

    def test_m03_retorna_total_por_turno_ue(self) -> None:
        """Verifica que M03 retorna total por turno no contrato legado."""
        url = reverse(
            "matriculas-quantidades-ue", kwargs={"ue_codigo": "100001"}
        )
        seed_matriculas()
        resp = _autenticado().get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.json(),
            {
                "totalMatricula": 2,
                "turnos": [
                    {
                        "turno": "Intermediário",
                        "tipoTurno": 2,
                        "quantidade": 1,
                    },
                    {
                        "turno": "Tarde",
                        "tipoTurno": 3,
                        "quantidade": 1,
                    },
                ],
            },
        )

    def test_m04_retorna_total_por_turno_dre(self) -> None:
        """Verifica que M04 retorna total por escola no contrato legado."""
        seed_alunos()
        Matricula.objects.create(
            codigo_matricula=999001,
            aluno_id=1234567,
            codigo_ue="100001",
            codigo_dre="108100",
            ano_letivo=2026,
            codigo_situacao_matricula=1,
            situacao_matricula="Ativo",
            data_situacao_matricula=date(2026, 2, 1),
            origem_atual=True,
            origem_historica=False,
            codigo_serie_ensino=100,
            codigo_tipo_escola=1,
        )
        MatriculaTurma.objects.create(
            codigo_matricula=999001,
            codigo_turma=32345,
            numero_chamada="12",
            data_situacao_aluno=date(2026, 2, 1),
            codigo_situacao_aluno=1,
            codigo_tipo_turma=1,
            tipo_turno=6,
            nome_turma="5A",
            codigo_ue_turma="100001",
            codigo_etapa_ensino=5,
            codigo_ciclo_ensino=2,
            descricao_etapa_ensino="Ensino Fundamental",
            descricao_ciclo_ensino="Ciclo Interdisciplinar",
            sequencia=1,
            origem_atual=True,
            ano_letivo_turma=2026,
            serie_resumida="5",
        )

        url = reverse(
            "matriculas-quantidades-dre",
            kwargs={"dre_codigo": "108100"},
        )
        resp = _autenticado().get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.json(),
            [
                {
                    "totalMatriculas": 1,
                    "codigoEolEscola": "100001",
                    "turnos": [
                        {
                            "turno": "Integral",
                            "tipoTurno": 6,
                            "quantidade": 1,
                        }
                    ],
                }
            ],
        )

    def test_m04_agrupa_pela_ue_da_ultima_alocacao(self) -> None:
        """Verifica que M04 usa a UE da última alocação da matrícula."""
        seed_alunos()
        Matricula.objects.create(
            codigo_matricula=999002,
            aluno_id=1234567,
            codigo_ue="100001",
            codigo_dre="108100",
            ano_letivo=2026,
            codigo_situacao_matricula=1,
            situacao_matricula="Ativo",
            data_situacao_matricula=date(2026, 2, 1),
            origem_atual=True,
            origem_historica=False,
            codigo_serie_ensino=100,
            codigo_tipo_escola=1,
        )
        MatriculaTurma.objects.create(
            codigo_matricula=999002,
            codigo_turma=42345,
            numero_chamada="12",
            data_situacao_aluno=date(2026, 2, 10),
            codigo_situacao_aluno=1,
            codigo_tipo_turma=1,
            tipo_turno=6,
            nome_turma="5A",
            codigo_ue_turma="100001",
            codigo_etapa_ensino=5,
            codigo_ciclo_ensino=2,
            descricao_etapa_ensino="Ensino Fundamental",
            descricao_ciclo_ensino="Ciclo Interdisciplinar",
            sequencia=1,
            origem_atual=True,
            ano_letivo_turma=2026,
            serie_resumida="5",
        )
        MatriculaTurma.objects.create(
            codigo_matricula=999002,
            codigo_turma=52345,
            numero_chamada="12",
            data_situacao_aluno=date(2026, 2, 20),
            codigo_situacao_aluno=1,
            codigo_tipo_turma=1,
            tipo_turno=3,
            nome_turma="5B",
            codigo_ue_turma="100002",
            codigo_etapa_ensino=5,
            codigo_ciclo_ensino=2,
            descricao_etapa_ensino="Ensino Fundamental",
            descricao_ciclo_ensino="Ciclo Interdisciplinar",
            sequencia=2,
            origem_atual=True,
            ano_letivo_turma=2026,
            serie_resumida="5",
        )

        url = reverse(
            "matriculas-quantidades-dre",
            kwargs={"dre_codigo": "108100"},
        )
        resp = _autenticado().get(url)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.json(),
            [
                {
                    "totalMatriculas": 1,
                    "codigoEolEscola": "100002",
                    "turnos": [
                        {
                            "turno": "Tarde",
                            "tipoTurno": 3,
                            "quantidade": 1,
                        }
                    ],
                }
            ],
        )


class EscolasApiTestCase(TestCase):
    """Valida os endpoints de escola (E05 e E24)."""

    def test_e05(self) -> None:
        """Verifica a quantidade de alunos por turma da escola."""
        seed_matriculas()
        url = reverse(
            "quantidade-alunos-por-turma-escola",
            kwargs={"codigo_escola": "100001"},
        )
        resp = _autenticado().get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 2)

    def test_e24(self) -> None:
        """Verifica as matrículas do aluno na escola."""
        seed_matriculas()
        url = reverse(
            "matriculas-aluno-escola",
            kwargs={
                "codigo_escola": "100001",
                "codigo_aluno": "1234567",
            },
        )
        resp = _autenticado().get(url)
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["codigo_matricula"], 998877)

    def test_e24_codigo_invalido_400(self) -> None:
        """Verifica que codigo_aluno não numérico retorna 400."""
        url = reverse(
            "matriculas-aluno-escola",
            kwargs={
                "codigo_escola": "100001",
                "codigo_aluno": "abc",
            },
        )
        resp = _autenticado().get(url)
        self.assertEqual(resp.status_code, 400)


class TurmasDoAlunoComHistoricoApiTestCase(TestCase):
    """Valida as turmas do aluno com origem histórica explícita."""

    def _url(self, historico: str = "false", **extras: str) -> str:
        kwargs = {
            "codigo_aluno": "1234567",
            "ano_letivo": "2026",
            "historico": historico,
            "filtrar_situacao": "true",
            "tipo_turma": "true",
        }
        kwargs.update(extras)
        return reverse("busca-turmas-do-aluno-com-historico", kwargs=kwargs)

    def test_historico_false_retorna_vinculos_correntes(self) -> None:
        """Verifica o retorno dos vínculos correntes."""
        seed_matriculas()
        resp = _autenticado().get(self._url())
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 1)

    def test_fallback_para_historico_quando_corrente_vazio(self) -> None:
        """Verifica o fallback para o histórico, como no legado."""
        seed_matriculas(origem_atual=False)
        resp = _autenticado().get(self._url(historico="false"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 1)

    def test_codigo_invalido_400(self) -> None:
        """Verifica que código de aluno não positivo retorna 400."""
        resp = _autenticado().get(self._url(codigo_aluno="0"))
        self.assertEqual(resp.status_code, 400)

    def test_sem_turmas_404(self) -> None:
        """Verifica 404 quando não há turmas para o aluno."""
        resp = _autenticado().get(self._url())
        self.assertEqual(resp.status_code, 404)


class QuantidadeMatriculadosCCContratoApiTestCase(TestCase):
    """Valida matriculados por componente no contrato do legado."""

    def _url(self, ano_letivo: str = "2026") -> str:
        return reverse(
            "quantidade-matriculados-cc-contrato",
            kwargs={"ano_letivo": ano_letivo},
        )

    def test_sem_componentes_replica_erro_legado(self) -> None:
        """Verifica que a ausência de componentes replica o erro do legado."""
        resp = _autenticado().get(self._url())
        self.assertEqual(resp.status_code, 601)
        self.assertEqual(
            resp.json(),
            "Os códigos dos componentes curriculares são obrigatórios.",
        )

    def test_filtra_por_componente_e_ue(self) -> None:
        """Verifica o retorno agregado com ordem nula como zero."""
        MatriculaComponenteCurricularAnoLetivo.objects.create(
            codigo_ue="093181",
            codigo_dre="108100",
            ano_letivo=2026,
            modalidade=None,
            ordem=None,
            componente_curricular_id=1310,
            ano="1",
            turma="1A",
            quantidade=1,
        )
        MatriculaComponenteCurricularAnoLetivo.objects.create(
            codigo_ue="999999",
            codigo_dre="108100",
            ano_letivo=2026,
            modalidade="EM",
            ordem=3,
            componente_curricular_id=1310,
            ano="2",
            turma="2M",
            quantidade=5,
        )
        resp = _autenticado().get(
            self._url() + "?componentes_curriculares=1310&ue_id=093181"
        )
        self.assertEqual(resp.status_code, 200)
        corpo = resp.json()
        self.assertEqual(len(corpo), 1)
        self.assertEqual(corpo[0]["componente_curricular_id"], 1310)
        self.assertEqual(corpo[0]["ordem"], 0)
        self.assertIsNone(corpo[0]["modalidade"])
        self.assertEqual(corpo[0]["quantidade"], 1)


class QuantidadeMatriculadosContratoApiTestCase(TestCase):
    """Valida a quantidade de matriculados no contrato do legado."""

    def _criar_agregado(self, **extras: object) -> None:
        campos: dict[str, object] = {
            "codigo_dre": "108200",
            "codigo_ue": "019267",
            "tipo_escola": 1,
            "ano_letivo": 2026,
            "codigo_modalidade": 5,
            "modalidade": "EF",
            "ordem": 2,
            "ano": "3",
            "turma": "3B",
            "quantidade": 28,
        }
        campos.update(extras)
        MatriculaAnoLetivo.objects.create(**campos)

    def _url(self, ano_letivo: str = "2026") -> str:
        return reverse(
            "quantidade-matriculados-contrato",
            kwargs={"ano_letivo": ano_letivo},
        )

    def test_ano_letivo_zero_replica_erro_legado(self) -> None:
        """Verifica que ano letivo zero replica o erro do legado."""
        resp = _autenticado().get(self._url("0"))
        self.assertEqual(resp.status_code, 601)
        self.assertEqual(resp.json(), "Ano Letivo deve ser informado")

    def test_filtra_por_ue(self) -> None:
        """Verifica o retorno agregado filtrado por UE."""
        self._criar_agregado()
        self._criar_agregado(codigo_ue="999999", turma="9Z")
        resp = _autenticado().get(self._url() + "?ue_codigo=019267")
        self.assertEqual(resp.status_code, 200)
        corpo = resp.json()
        self.assertEqual(len(corpo), 1)
        self.assertEqual(corpo[0]["quantidade"], 28)
        self.assertEqual(corpo[0]["modalidade"], "EF")
        self.assertEqual(corpo[0]["dre_codigo"], "108200")
        self.assertEqual(corpo[0]["ue_codigo"], "019267")

    def test_modalidade_infantil_restringe_tipo_escola(self) -> None:
        """Verifica o filtro de tipo de escola da modalidade infantil."""
        self._criar_agregado(
            codigo_modalidade=1, modalidade="EI", ordem=1, tipo_escola=1
        )
        self._criar_agregado(
            codigo_modalidade=1,
            modalidade="EI",
            ordem=1,
            tipo_escola=2,
            turma="EI-A",
        )
        resp = _autenticado().get(self._url() + "?modalidade=1")
        self.assertEqual(resp.status_code, 200)
        corpo = resp.json()
        self.assertEqual(len(corpo), 1)
        self.assertEqual(corpo[0]["turma"], "EI-A")

    def test_ano_menos_99_desativa_filtro(self) -> None:
        """Verifica que -99 na lista de anos desativa o filtro."""
        self._criar_agregado()
        resp = _autenticado().get(self._url() + "?ano=-99&ano=9")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 1)


class A18ContratoApiTestCase(TestCase):
    """Valida o acompanhamento escolar no contrato do legado."""

    def _criar_registro(self, **extras: object) -> None:
        campos: dict[str, object] = {
            "codigo_aluno": 1234567,
            "nome": "JOAO DA SILVA",
            "nome_responsavel": "MARIA DA SILVA",
            "cpf_responsavel": "12345678901",
            "codigo_dre": "108200",
            "sigla_dre": "DRE - CL",
            "codigo_ue": "100001",
            "unidade_educacional": "EMEF TESTE",
            "codigo_turma": 12345,
            "turma": "5A",
            "codigo_tipo_escola": 1,
            "descricao_tipo_escola": "EMEF",
            "situacao_matricula": "Ativo",
            "serie_resumida": "5",
        }
        campos.update(extras)
        DadosAlunoAcompanhamentoEscolar.objects.create(**campos)

    def test_sem_filtro_replica_erro_legado(self) -> None:
        """Verifica que a ausência de filtros replica o erro do legado."""
        url = reverse("dados-acompanhamento-escolar-contrato")
        resp = _autenticado().get(url)
        self.assertEqual(resp.status_code, 601)
        self.assertIn("Nenhum filtro foi especificado", resp.json())

    def test_filtra_por_codigo_aluno(self) -> None:
        """Verifica o retorno com os campos do contrato do legado."""
        self._criar_registro()
        url = reverse("dados-acompanhamento-escolar-contrato")
        resp = _autenticado().get(url + "?codigo_aluno=1234567")
        self.assertEqual(resp.status_code, 200)
        corpo = resp.json()
        self.assertEqual(len(corpo), 1)
        self.assertEqual(corpo[0]["codigo_eol"], 1234567)
        self.assertEqual(corpo[0]["codigo_escola"], "100001")
        self.assertEqual(corpo[0]["codigo_dre"], "108200")
        self.assertEqual(corpo[0]["escola"], "EMEF TESTE")
        self.assertEqual(corpo[0]["serie_resumida"], "5")

    def test_exclui_responsavel_sem_cpf(self) -> None:
        """Verifica a exclusão de registro sem CPF do responsável."""
        self._criar_registro(cpf_responsavel=None)
        url = reverse("dados-acompanhamento-escolar-contrato")
        resp = _autenticado().get(url + "?codigo_aluno=1234567")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])

    def test_exclui_aluno_com_sigilo(self) -> None:
        """Verifica a exclusão de aluno com sigilo."""
        self._criar_registro(tipo_sigilo=1)
        url = reverse("dados-acompanhamento-escolar-contrato")
        resp = _autenticado().get(url + "?codigo_aluno=1234567")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])


class A18AcompanhamentoApiTestCase(TestCase):
    """Valida o endpoint de dados de acompanhamento escolar."""

    def test_lista(self) -> None:
        """Verifica o retorno por UE e ano letivo."""
        seed_matriculas()
        seed_responsaveis()
        url = reverse("dados-acompanhamento-escolar")
        resp = _autenticado().get(url + "?codigo_ue=100001&ano_letivo=2026")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(len(body), 2)

    def test_sem_nenhum_filtro_retorna_400(self) -> None:
        """Verifica que ausência total de filtros retorna 400."""
        url = reverse("dados-acompanhamento-escolar")
        resp = _autenticado().get(url)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(
            resp.json()["detail"],
            "Nenhum filtro foi especificado para busca de dados "
            "dos alunos para acompanhamento do estudante",
        )

    def test_so_ano_letivo_retorna_400(self) -> None:
        """Verifica que apenas ano_letivo (sem demais filtros) retorna 400."""
        url = reverse("dados-acompanhamento-escolar")
        resp = _autenticado().get(url + "?ano_letivo=2026")
        self.assertEqual(resp.status_code, 400)

    def test_filtra_por_codigo_aluno(self) -> None:
        """Verifica o retorno filtrado pelo código do aluno."""
        seed_matriculas_com_responsaveis()
        url = reverse("dados-acompanhamento-escolar")
        resp = _autenticado().get(url + "?codigo_aluno=1234567")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["codigo_eol"], 1234567)

    def test_filtra_por_cpf_responsavel(self) -> None:
        """Verifica o retorno filtrado pelo CPF do responsável."""
        seed_matriculas_com_responsaveis()
        url = reverse("dados-acompanhamento-escolar")
        resp = _autenticado().get(url + "?cpf_responsavel=12345678901")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["cpf_responsavel"], "12345678901")

    def test_codigo_aluno_invalido_retorna_400(self) -> None:
        """Verifica que codigo_aluno não numérico retorna 400."""
        url = reverse("dados-acompanhamento-escolar")
        resp = _autenticado().get(url + "?codigo_aluno=abc")
        self.assertEqual(resp.status_code, 400)


class A15QuantidadeMatriculadosCCApiTestCase(TestCase):
    """Valida o endpoint de quantidade de matriculados por CC."""

    def test_lista_com_ue_id_e_componentes(self) -> None:
        """Verifica o retorno com filtros de UE e componentes."""
        seed_matriculas()
        url = reverse(
            "quantidade-matriculados-cc", kwargs={"ano_letivo": "2026"}
        )
        resp = _autenticado().get(
            url + "?ue_id=100001&componentes_curriculares=1"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(len(resp.json()), 1)

    def test_sem_ue_id_retorna_200(self) -> None:
        """Verifica que a consulta funciona sem ue_id."""
        seed_matriculas()
        url = reverse(
            "quantidade-matriculados-cc", kwargs={"ano_letivo": "2026"}
        )
        resp = _autenticado().get(url + "?componentes_curriculares=1")
        self.assertEqual(resp.status_code, 200)

    def test_sem_componentes_curriculares_retorna_400(self) -> None:
        """Verifica que faltar componentes_curriculares retorna 400."""
        url = reverse(
            "quantidade-matriculados-cc", kwargs={"ano_letivo": "2026"}
        )
        resp = _autenticado().get(url + "?ue_id=100001")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("componentes_curriculares", resp.json()["detail"])


class A16QuantidadeMatriculadosApiTestCase(TestCase):
    """Valida o endpoint de quantidade de matriculados (filtros gerais)."""

    def test_lista_com_ue_codigo(self) -> None:
        """Verifica o retorno com filtro de UE."""
        seed_matriculas()
        url = reverse("quantidade-matriculados", kwargs={"ano_letivo": "2026"})
        resp = _autenticado().get(url + "?ue_codigo=100001")
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(len(resp.json()), 1)

    def test_sem_ue_codigo_retorna_200(self) -> None:
        """Verifica que a consulta funciona sem ue_codigo."""
        seed_matriculas()
        url = reverse("quantidade-matriculados", kwargs={"ano_letivo": "2026"})
        resp = _autenticado().get(url)
        self.assertEqual(resp.status_code, 200)


class A03TurmasPorSituacaoMatriculaApiTestCase(TestCase):
    """Valida o endpoint de turmas filtradas por situação de matrícula."""

    def _url(
        self,
        codigo_aluno: str = "1234567",
        ano_letivo: str = "2026",
        filtrar: str = "true",
        tipo_turma: str = "false",
    ) -> str:
        """Monta a URL do endpoint com os parâmetros informados."""
        return cast(
            str,
            reverse(
                "busca-turmas-do-aluno-por-situacao-matricula",
                kwargs={
                    "codigo_aluno": codigo_aluno,
                    "ano_letivo": ano_letivo,
                    "filtrar_situacao_matricula": filtrar,
                    "tipo_turma": tipo_turma,
                },
            ),
        )

    def test_happy_path(self) -> None:
        """Verifica o retorno com parâmetros válidos."""
        seed_matriculas(origem_atual=False)
        with patch(
            "django.utils.timezone.now",
            return_value=datetime(2027, 6, 1, tzinfo=UTC),
        ):
            resp = _autenticado().get(self._url())
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 1)

    @patch(
        "apps.alunos.api.views.services."
        "buscar_turmas_do_aluno_por_situacao_matricula"
    )
    def test_repassa_tipo_turma(self, mock_buscar: MagicMock) -> None:
        """Verifica que o filtro de tipo de turma chega ao serviço."""
        mock_buscar.return_value = []

        resp = _autenticado().get(self._url(tipo_turma="true"))

        self.assertEqual(resp.status_code, 404)
        mock_buscar.assert_called_once_with(
            codigo_aluno=1234567,
            ano_letivo=2026,
            filtrar_situacao_matricula=True,
            tipo_turma=True,
        )

    def test_codigo_aluno_invalido_400(self) -> None:
        """Verifica que codigo_aluno não numérico retorna 400."""
        resp = _autenticado().get(self._url(codigo_aluno="abc"))
        self.assertEqual(resp.status_code, 400)

    def test_ano_letivo_invalido_400(self) -> None:
        """Verifica que ano_letivo não numérico retorna 400."""
        resp = _autenticado().get(self._url(ano_letivo="xx"))
        self.assertEqual(resp.status_code, 400)

    def test_filtrar_invalido_400(self) -> None:
        """Verifica que filtrar_situacao_matricula inválido retorna 400."""
        resp = _autenticado().get(self._url(filtrar="talvez"))
        self.assertEqual(resp.status_code, 400)

    def test_codigo_aluno_zero_400(self) -> None:
        """Verifica que codigo_aluno=0 retorna 400."""
        resp = _autenticado().get(self._url(codigo_aluno="0"))
        self.assertEqual(resp.status_code, 400)

    def test_aluno_sem_turma_404(self) -> None:
        """Verifica que aluno sem turmas retorna 404."""
        resp = _autenticado().get(self._url(codigo_aluno="9999999"))
        self.assertEqual(resp.status_code, 404)


class ValidacoesParametros400ApiTestCase(TestCase):
    """Cobre ramos de _erro_400 (parsing) das views."""

    def test_a04_ano_letivo_invalido(self) -> None:
        """Verifica que ano_letivo inválido em A04 retorna 400."""
        url = reverse(
            "buscar-alunos-da-ue",
            kwargs={"codigo_ue": "100001", "ano_letivo": "xx"},
        )
        resp = _autenticado().get(url)
        self.assertEqual(resp.status_code, 400)

    def test_a04_sem_dados_404(self) -> None:
        """Verifica que UE sem alunos retorna 404 em A04."""
        url = reverse(
            "buscar-alunos-da-ue",
            kwargs={"codigo_ue": "999999", "ano_letivo": "2026"},
        )
        resp = _autenticado().get(url)
        self.assertEqual(resp.status_code, 404)

    def test_a05_ano_letivo_invalido(self) -> None:
        """Verifica que ano_letivo inválido em A05 retorna 400."""
        url = reverse(
            "autocomplete-alunos-ue",
            kwargs={"codigo_ue": "100001", "ano_letivo": "xx"},
        )
        resp = _autenticado().get(url)
        self.assertEqual(resp.status_code, 400)

    def test_a05_codigos_turmas_invalidos(self) -> None:
        """Verifica que codigos_turmas com valor não numérico retorna 400."""
        url = reverse(
            "autocomplete-alunos-ue",
            kwargs={"codigo_ue": "100001", "ano_letivo": "2026"},
        )
        resp = _autenticado().get(url + "?codigos_turmas=abc")
        self.assertEqual(resp.status_code, 400)

    def test_a05_sem_resultado_404(self) -> None:
        """Verifica que UE sem alunos em A05 retorna 404."""
        url = reverse(
            "autocomplete-alunos-ue",
            kwargs={"codigo_ue": "999999", "ano_letivo": "2026"},
        )
        resp = _autenticado().get(url)
        self.assertEqual(resp.status_code, 404)

    def test_a06_data_referencia_invalida(self) -> None:
        """Verifica que data_referencia inválida em A06 retorna 400."""
        url = reverse(
            "autocomplete-alunos-ativos", kwargs={"ue_codigo": "100001"}
        )
        resp = _autenticado().get(
            url + "?aluno_codigo=1234567&data_referencia=naoEhData"
        )
        self.assertEqual(resp.status_code, 400)

    def test_a06_busca_por_codigo_aluno(self) -> None:
        """Verifica a busca em A06 por código de aluno."""
        seed_matriculas()
        url = reverse(
            "autocomplete-alunos-ativos", kwargs={"ue_codigo": "100001"}
        )
        resp = _autenticado().get(url + "?aluno_codigo=1234567")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 1)

    def test_a06_sem_resultado_404(self) -> None:
        """Verifica que nome sem match em A06 retorna 404."""
        url = reverse(
            "autocomplete-alunos-ativos", kwargs={"ue_codigo": "100001"}
        )
        resp = _autenticado().get(url + "?aluno_nome=INEXISTENTE")
        self.assertEqual(resp.status_code, 404)

    def test_a07_ano_letivo_invalido(self) -> None:
        """Verifica que ano_letivo inválido em A07 retorna 400."""
        url = reverse(
            "total-alunos-ativos-por-periodo",
            kwargs={
                "ano_turma": "5",
                "ano_letivo": "xx",
                "data_inicio": "2026-01-01",
                "data_fim": "2026-12-31",
            },
        )
        resp = _autenticado().get(url)
        self.assertEqual(resp.status_code, 400)

    def test_a08_happy_path(self) -> None:
        """Verifica o retorno de A08 com janela de datas válida."""
        seed_matriculas()
        url = reverse(
            "alunos-ativos-periodo-turma",
            kwargs={
                "codigo_turma": "12345",
                "data_referencia_fim": "2026-12-31",
            },
        )
        resp = _autenticado().get(url + "?data_referencia_inicio=2026-01-01")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 1)

    def test_a08_data_invalida_400(self) -> None:
        """Verifica que data_referencia_fim inválida em A08 retorna 400."""
        url = reverse(
            "alunos-ativos-periodo-turma",
            kwargs={
                "codigo_turma": "12345",
                "data_referencia_fim": "naoEhData",
            },
        )
        resp = _autenticado().get(url)
        self.assertEqual(resp.status_code, 400)

    def test_a08_codigo_turma_invalido_400(self) -> None:
        """Verifica que codigo_turma não numérico em A08 retorna 400."""
        url = reverse(
            "alunos-ativos-periodo-turma",
            kwargs={
                "codigo_turma": "abc",
                "data_referencia_fim": "2026-12-31",
            },
        )
        resp = _autenticado().get(url)
        self.assertEqual(resp.status_code, 400)

    def test_a09_codigo_turma_invalido_400(self) -> None:
        """Verifica que codigo_turma não numérico em A09 retorna 400."""
        url = reverse("alunos-ativos-turma", kwargs={"codigo_turma": "abc"})
        resp = _autenticado().get(url)
        self.assertEqual(resp.status_code, 400)

    def test_a10_codigo_aluno_invalido_400(self) -> None:
        """Verifica que codigo_aluno não numérico em A10 retorna 400."""
        url = reverse(
            "necessidades-especiais-aluno", kwargs={"codigo_aluno": "abc"}
        )
        resp = _autenticado().get(url)
        self.assertEqual(resp.status_code, 400)

    def test_a11_happy_path(self) -> None:
        """Verifica o retorno de A11 com parâmetros válidos."""
        seed_matriculas()
        url = reverse(
            "alunos-por-codigos-e-ano", kwargs={"ano_letivo": "2026"}
        )
        resp = _autenticado().get(url + "?codigos_aluno=1234567")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 1)

    def test_a11_ano_letivo_invalido_400(self) -> None:
        """Verifica que ano_letivo inválido em A11 retorna 400."""
        url = reverse("alunos-por-codigos-e-ano", kwargs={"ano_letivo": "xx"})
        resp = _autenticado().get(url + "?codigos_aluno=1234567")
        self.assertEqual(resp.status_code, 400)

    def test_a11_codigos_invalidos_400(self) -> None:
        """Verifica que codigos_aluno inválidos em A11 retorna 400."""
        url = reverse(
            "alunos-por-codigos-e-ano", kwargs={"ano_letivo": "2026"}
        )
        resp = _autenticado().get(url + "?codigos_aluno=abc")
        self.assertEqual(resp.status_code, 400)

    def test_a11_sem_codigos_replica_erro_legado(self) -> None:
        """Verifica que a ausência de códigos replica o erro do legado."""
        url = reverse(
            "alunos-por-codigos-e-ano", kwargs={"ano_letivo": "2026"}
        )
        resp = _autenticado().get(url)
        self.assertEqual(resp.status_code, 601)
        self.assertEqual(
            resp.json(), "Os códigos dos Alunos são obrigatórios."
        )

    def test_a11_nao_filtra_situacao_de_matricula(self) -> None:
        """Verifica que situações fora das ativas também retornam."""
        seed_matriculas()
        MatriculaTurma.objects.filter(codigo_matricula=998877).update(
            codigo_situacao_aluno=2
        )
        url = reverse(
            "alunos-por-codigos-e-ano", kwargs={"ano_letivo": "2026"}
        )
        resp = _autenticado().get(url + "?codigos_aluno=1234567")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 1)

    def test_a12_codigos_invalidos_400(self) -> None:
        """Verifica que codigos_aluno inválidos em A12 retorna 400."""
        url = reverse("alunos-por-codigos")
        resp = _autenticado().get(url + "?codigos_aluno=abc")
        self.assertEqual(resp.status_code, 400)

    def test_a13_codigo_aluno_invalido_400(self) -> None:
        """Verifica que codigo_aluno não numérico em A13 retorna 400."""
        url = reverse("informacoes-aluno", kwargs={"codigo_aluno": "abc"})
        resp = _autenticado().get(url)
        self.assertEqual(resp.status_code, 400)

    def test_a14_codigo_turma_invalido_400(self) -> None:
        """Verifica que codigo_turma não numérico em A14 retorna 400."""
        url = reverse(
            "informacoes-alunos-turma", kwargs={"codigo_turma": "abc"}
        )
        resp = _autenticado().get(url)
        self.assertEqual(resp.status_code, 400)

    def test_a15_ano_letivo_invalido_400(self) -> None:
        """Verifica que ano_letivo inválido em A15 retorna 400."""
        url = reverse(
            "quantidade-matriculados-cc", kwargs={"ano_letivo": "xx"}
        )
        resp = _autenticado().get(url + "?componentes_curriculares=1")
        self.assertEqual(resp.status_code, 400)

    def test_a16_ano_letivo_invalido_400(self) -> None:
        """Verifica que ano_letivo inválido em A16 retorna 400."""
        url = reverse("quantidade-matriculados", kwargs={"ano_letivo": "xx"})
        resp = _autenticado().get(url)
        self.assertEqual(resp.status_code, 400)

    def test_a18_codigo_dre_sozinho_retorna_vazio(self) -> None:
        """Verifica que codigo_dre sozinho em A18 devolve lista vazia."""
        url = reverse("dados-acompanhamento-escolar")
        resp = _autenticado().get(url + "?codigo_dre=108")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])

    def test_a19_ano_letivo_invalido_400(self) -> None:
        """Verifica que ano_letivo inválido em A19 retorna 400."""
        url = reverse("responsaveis-dre-ue-turma")
        resp = _autenticado().get(url + "?codigo_ue=100001&ano_letivo=xx")
        self.assertEqual(resp.status_code, 400)

    def test_a22_codigo_aluno_invalido_400(self) -> None:
        """Verifica que codigo_aluno não numérico em A22 retorna 400."""
        url = reverse(
            "responsavel-aluno",
            kwargs={
                "codigo_aluno": "abc",
                "cpf_responsavel": "12345678901",
            },
        )
        resp = _autenticado().put(url, data={}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_a23_codigo_aluno_invalido_400(self) -> None:
        """Verifica que codigo_aluno não numérico em A23 retorna 400."""
        url = reverse(
            "responsavel-aluno",
            kwargs={
                "codigo_aluno": "abc",
                "cpf_responsavel": "12345678901",
            },
        )
        resp = _autenticado().post(url, data={}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_a27_codigo_aluno_invalido_400(self) -> None:
        """Verifica que codigo_aluno não numérico em A27 retorna 400."""
        url = reverse("filiacao-aluno", kwargs={"codigo_aluno": "abc"})
        resp = _autenticado().get(url)
        self.assertEqual(resp.status_code, 400)

    def test_a27_inexistente_retorna_lista_vazia(self) -> None:
        """Verifica que aluno sem filiação retorna lista vazia."""
        url = reverse("filiacao-aluno", kwargs={"codigo_aluno": "9999999"})
        resp = _autenticado().get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])

    def test_a21_inexistente_404(self) -> None:
        """Verifica que CPF inexistente em A21 retorna 404."""
        url = reverse(
            "dados-responsavel-resumido",
            kwargs={"cpf_responsavel": "00000000000"},
        )
        resp = _autenticado().get(url)
        self.assertEqual(resp.status_code, 404)

    def test_m01_ano_letivo_invalido_400(self) -> None:
        """Verifica que ano_letivo inválido em M01 retorna 400."""
        url = reverse("matriculas-ano-atual")
        resp = _autenticado().get(url + "?ano_letivo=xx&ue_codigo=100001")
        self.assertEqual(resp.status_code, 400)

    def test_m02_ano_letivo_invalido_400(self) -> None:
        """Verifica que ano_letivo inválido em M02 retorna 400."""
        url = reverse("matriculas-anos-anteriores")
        resp = _autenticado().get(url + "?ano_letivo=xx&ue_codigo=100001")
        self.assertEqual(resp.status_code, 400)

    def test_m02_sem_parametros_400(self) -> None:
        """Verifica que ausência de parâmetros em M02 retorna 400."""
        url = reverse("matriculas-anos-anteriores")
        resp = _autenticado().get(url)
        self.assertEqual(resp.status_code, 400)


class AutocompleteCenariosApiTestCase(TestCase):
    """Cobre cenários adicionais do autocomplete por UE/ano."""

    def test_a05_codigos_turmas_filtra(self) -> None:
        """Verifica que codigos_turmas filtra o resultado."""
        seed_matriculas()
        url = reverse(
            "autocomplete-alunos-ue",
            kwargs={"codigo_ue": "100001", "ano_letivo": "2026"},
        )
        resp = _autenticado().get(
            url + "?codigos_turmas=12345&somente_ativos=true"
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(all(item["codigo_turma"] == 12345 for item in body))

    def test_a05_codigo_eol_nao_numerico_retorna_404(self) -> None:
        """Verifica que codigo_eol não numérico devolve 404 (sem resultado)."""
        seed_matriculas()
        url = reverse(
            "autocomplete-alunos-ue",
            kwargs={"codigo_ue": "100001", "ano_letivo": "2026"},
        )
        resp = _autenticado().get(url + "?codigo_eol=abc")
        self.assertEqual(resp.status_code, 404)

    def test_a05_eh_historico_true_consulta_vinculos_historicos(self) -> None:
        """Verifica que eh_historico=true usa apenas vínculos históricos."""
        seed_matriculas()
        url = reverse(
            "autocomplete-alunos-ue",
            kwargs={"codigo_ue": "100001", "ano_letivo": "2026"},
        )
        resp = _autenticado().get(url + "?eh_historico=true")
        self.assertEqual(resp.status_code, 404)

    def test_a05_eh_historico_true_com_dados_historicos(self) -> None:
        """Verifica o retorno de vínculos históricos no modo histórico."""
        seed_matriculas(origem_atual=False)
        url = reverse(
            "autocomplete-alunos-ue",
            kwargs={"codigo_ue": "100001", "ano_letivo": "2026"},
        )
        resp = _autenticado().get(url + "?eh_historico=true")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 2)

    def test_a05_limite_um(self) -> None:
        """Verifica que limite=1 corta o resultado em um único item."""
        seed_matriculas()
        url = reverse(
            "autocomplete-alunos-ue",
            kwargs={"codigo_ue": "100001", "ano_letivo": "2026"},
        )
        resp = _autenticado().get(url + "?limite=1")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 1)


class TurmasDoAlunoComFiltrosTestCase(TestCase):
    """Valida os filtros de query do endpoint de turmas do aluno."""

    def test_inclui_programa_e_nao_filtra_situacao(self) -> None:
        """Verifica que os filtros de query são aceitos e respondem 200."""
        seed_matriculas()
        seed_responsaveis()
        with patch(
            "django.utils.timezone.now",
            return_value=datetime(2026, 6, 1, tzinfo=UTC),
        ):
            url = reverse(
                "busca-turmas-do-aluno",
                kwargs={"codigo_aluno": "1234567"},
            )
            resp = _autenticado().get(
                url + "?tipo_turma=false&filtrar_situacao=false"
            )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body)
        self.assertEqual(body[0]["codigo_aluno"], 1234567)
        self.assertIn("codigo_tipo_turma", body[0])

    def test_filtro_booleano_invalido_400(self) -> None:
        """Verifica que filtro booleano inválido retorna 400."""
        url = reverse(
            "busca-turmas-do-aluno",
            kwargs={"codigo_aluno": "1234567"},
        )
        resp = _autenticado().get(url + "?tipo_turma=talvez")
        self.assertEqual(resp.status_code, 400)


class CodigosTurmasRegularesAlunoAPITestCase(TestCase):
    """Valida o endpoint HTTP de códigos de turma do aluno no ano."""

    def test_retorna_codigos_ordenados(self) -> None:
        """Retorna 200 com os códigos de turma do aluno no ano letivo."""
        seed_matriculas()
        cliente = _autenticado()
        url = reverse(
            "codigos-turmas-regulares-aluno",
            kwargs={"ano_letivo": "2026", "codigo_aluno": "1234567"},
        )
        with patch(
            "django.utils.timezone.now",
            return_value=datetime(2026, 6, 1, tzinfo=UTC),
        ):
            resp = cliente.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json(), [12345])

    def test_codigo_invalido_retorna_400(self) -> None:
        """Código não numérico gera 400."""
        cliente = _autenticado()
        url = reverse(
            "codigos-turmas-regulares-aluno",
            kwargs={"ano_letivo": "2026", "codigo_aluno": "abc"},
        )
        resp = cliente.get(url)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_aluno_sem_turmas_retorna_lista_vazia(self) -> None:
        """Aluno sem vínculos válidos recebe 200 com lista vazia."""
        seed_alunos()
        cliente = _autenticado()
        url = reverse(
            "codigos-turmas-regulares-aluno",
            kwargs={"ano_letivo": "2026", "codigo_aluno": "1234567"},
        )
        resp = cliente.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json(), [])
