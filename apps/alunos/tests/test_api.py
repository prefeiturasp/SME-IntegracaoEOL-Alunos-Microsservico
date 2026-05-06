"""Testes dos endpoints HTTP do app alunos."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.alunos.tests.helpers import (
    seed_alunos,
    seed_matriculas,
    seed_necessidades,
    seed_responsaveis,
)


def _autenticado() -> APIClient:
    cliente = APIClient()
    cliente.credentials(HTTP_X_API_KEY="test-api-key")
    return cliente


class AutenticacaoTestCase(TestCase):
    def test_sem_api_key_retorna_401(self) -> None:
        cliente = APIClient()
        url = reverse("alunos-por-codigos")
        resp = cliente.get(url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_api_key_invalida_retorna_403(self) -> None:
        cliente = APIClient()
        cliente.credentials(HTTP_X_API_KEY="errada")
        url = reverse("alunos-por-codigos")
        resp = cliente.get(url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


class A01TurmasDoAlunoTestCase(TestCase):
    def test_retorna_turmas(self) -> None:
        seed_matriculas()
        seed_responsaveis()
        with patch(
            "django.utils.timezone.now",
            return_value=datetime(2026, 6, 1, tzinfo=UTC),
        ):
            url = reverse(
                "busca-turmas-do-aluno", kwargs={"codigoAluno": "1234567"}
            )
            resp = _autenticado().get(url)
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["codigoAluno"], 1234567)
        self.assertEqual(body[0]["codigoTurma"], 12345)
        for campo in (
            "codigoTipoTurma",
            "dataAtualizacaoTabela",
            "nomeResponsavel",
        ):
            self.assertNotIn(campo, body[0])

    def test_aluno_invalido_400(self) -> None:
        url = reverse("busca-turmas-do-aluno", kwargs={"codigoAluno": "abc"})
        resp = _autenticado().get(url)
        self.assertEqual(resp.status_code, 400)

    def test_aluno_inexistente_404(self) -> None:
        url = reverse(
            "busca-turmas-do-aluno", kwargs={"codigoAluno": "9999999"}
        )
        resp = _autenticado().get(url)
        self.assertEqual(resp.status_code, 404)


class A04A05A06AutocompleteApiTestCase(TestCase):
    def test_a04_retorna_alunos(self) -> None:
        seed_matriculas()
        url = reverse(
            "buscar-alunos-da-ue",
            kwargs={"codigoUe": "100001", "anoLetivo": "2026"},
        )
        resp = _autenticado().get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 2)

    def test_a05_autocomplete(self) -> None:
        seed_matriculas()
        url = reverse(
            "autocomplete-alunos-ue",
            kwargs={"codigoUe": "100001", "anoLetivo": "2026"},
        )
        resp = _autenticado().get(url + "?nomeAluno=JOAO")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["nomeAluno"], "JOAO DA SILVA")

    def test_a06_exige_nome_minimo(self) -> None:
        url = reverse(
            "autocomplete-alunos-ativos", kwargs={"ueCodigo": "100001"}
        )
        resp = _autenticado().get(url + "?alunoNome=ab")
        self.assertEqual(resp.status_code, 400)


class A07A08A09TurmaApiTestCase(TestCase):
    def test_a07_total(self) -> None:
        seed_matriculas()
        url = reverse(
            "total-alunos-ativos-por-periodo",
            kwargs={
                "anoTurma": "5",
                "anoLetivo": "2026",
                "dataInicio": "2026-01-01",
                "dataFim": "2026-12-31",
            },
        )
        resp = _autenticado().get(url + "?ueId=100001")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["quantidade"], 2)

    def test_a09_alunos_ativos(self) -> None:
        seed_matriculas()
        url = reverse("alunos-ativos-turma", kwargs={"codigoTurma": "12345"})
        resp = _autenticado().get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 1)


class A10A13A14ApiTestCase(TestCase):
    def test_a10_necessidades(self) -> None:
        seed_alunos()
        seed_necessidades()
        url = reverse(
            "necessidades-especiais-aluno",
            kwargs={"codigoAluno": "1234567"},
        )
        resp = _autenticado().get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 1)

    def test_a13_informacoes_shape_reduzido(self) -> None:
        seed_alunos()
        url = reverse("informacoes-aluno", kwargs={"codigoAluno": "1234567"})
        resp = _autenticado().get(url)
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["codigoAluno"], 1234567)
        self.assertEqual(body["nomeAluno"], "JOAO DA SILVA")
        for campo in (
            "endereco",
            "grupoEtnico",
            "nacionalidadeResponsavel",
            "ehImigrante",
            "responsavelEhImigrante",
            "cns",
            "teg",
        ):
            self.assertNotIn(campo, body)

    def test_a13_inexistente_404(self) -> None:
        url = reverse("informacoes-aluno", kwargs={"codigoAluno": "1111111"})
        resp = _autenticado().get(url)
        self.assertEqual(resp.status_code, 404)

    def test_a14_alunos_da_turma(self) -> None:
        seed_matriculas()
        url = reverse(
            "informacoes-alunos-turma",
            kwargs={"codigoTurma": "12345"},
        )
        resp = _autenticado().get(url)
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["codigoAluno"], 1234567)


class A19A20A21ResponsavelApiTestCase(TestCase):
    def test_a19_lista(self) -> None:
        seed_matriculas()
        seed_responsaveis()
        url = reverse("responsaveis-dre-ue-turma")
        resp = _autenticado().get(
            url + "?codigoDre=108&codigoUe=100001&anoLetivo=2026"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 1)

    def test_a19_sem_dados_204(self) -> None:
        url = reverse("responsaveis-dre-ue-turma")
        resp = _autenticado().get(url + "?codigoDre=108&codigoUe=999")
        self.assertEqual(resp.status_code, 204)

    def test_a19_sem_codigo_dre_retorna_400(self) -> None:
        url = reverse("responsaveis-dre-ue-turma")
        resp = _autenticado().get(url + "?codigoUe=100001&anoLetivo=2026")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("codigoDre", resp.json()["detail"])

    def test_a19_so_codigo_dre_retorna_200(self) -> None:
        # codigoDre sozinho satisfaz a validação de contrato (mesmo
        # sendo ignorado internamente). codigoUe deixa de ser exigido.
        seed_matriculas()
        seed_responsaveis()
        url = reverse("responsaveis-dre-ue-turma")
        resp = _autenticado().get(url + "?codigoDre=108")
        self.assertEqual(resp.status_code, 200)

    def test_a19_paginacao_limit(self) -> None:
        seed_matriculas()
        seed_responsaveis()
        url = reverse("responsaveis-dre-ue-turma")
        resp = _autenticado().get(
            url + "?codigoDre=108&codigoUe=100001&anoLetivo=2026&limit=0"
        )
        self.assertEqual(resp.status_code, 400)

    def test_a20_dados_completos(self) -> None:
        seed_alunos()
        seed_responsaveis()
        url = reverse(
            "dados-responsavel",
            kwargs={"cpfResponsavel": "12345678901"},
        )
        resp = _autenticado().get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 1)

    def test_a21_resumido(self) -> None:
        seed_alunos()
        seed_responsaveis()
        url = reverse(
            "dados-responsavel-resumido",
            kwargs={"cpfResponsavel": "12345678901"},
        )
        resp = _autenticado().get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["cpf"], "12345678901")


class A22A23EscritaApiTestCase(TestCase):
    def test_a22_atualiza_via_put(self) -> None:
        seed_alunos()
        seed_responsaveis()
        url = reverse(
            "responsavel-aluno",
            kwargs={
                "codigoAluno": "1234567",
                "cpfResponsavel": "12345678901",
            },
        )
        resp = _autenticado().put(
            url,
            data={
                "codigoAluno": 1234567,
                "cpf": "12345678901",
                "email": "novo@sme.com.br",
                "dddCelular": "11",
                "numeroCelular": "999996666",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["numeroCelular"], "999996666")

    def test_a23_cadastra_via_post(self) -> None:
        seed_alunos()
        url = reverse(
            "responsavel-aluno",
            kwargs={
                "codigoAluno": "1234567",
                "cpfResponsavel": "55544433322",
            },
        )
        resp = _autenticado().post(
            url,
            data={
                "cpf": "55544433322",
                "nome": "Novo Resp",
                "email": "novo2@sme.com.br",
                "tipoResponsavel": 2,
                "dddCelular": "11",
                "numeroCelular": "988887777",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["cpf"], "55544433322")


class A27FiliacaoApiTestCase(TestCase):
    def test_retorna_informacoes(self) -> None:
        seed_alunos()
        url = reverse("filiacao-aluno", kwargs={"codigoAluno": "1234567"})
        resp = _autenticado().get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["codigoAluno"], 1234567)


class A12AlunosPorCodigosApiTestCase(TestCase):
    def test_retorna_alunos(self) -> None:
        seed_matriculas()
        url = reverse("alunos-por-codigos")
        resp = _autenticado().get(url + "?codigosAluno=1234567")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["codigoAluno"], 1234567)

    def test_sem_codigos_retorna_vazio(self) -> None:
        url = reverse("alunos-por-codigos")
        resp = _autenticado().get(url + "?codigosAluno=")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])


class MatriculasApiTestCase(TestCase):
    def test_m01(self) -> None:
        seed_matriculas()
        url = reverse("matriculas-ano-atual")
        resp = _autenticado().get(url + "?anoLetivo=2026&ueCodigo=100001")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 2)

    def test_m01_sem_parametros_400(self) -> None:
        url = reverse("matriculas-ano-atual")
        resp = _autenticado().get(url)
        self.assertEqual(resp.status_code, 400)

    def test_m02(self) -> None:
        seed_matriculas()
        url = reverse("matriculas-anos-anteriores")
        resp = _autenticado().get(url + "?anoLetivo=2025&ueCodigo=100001")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])

    def test_m03_out_of_scope(self) -> None:
        url = reverse(
            "matriculas-quantidades-ue", kwargs={"ueCodigo": "100001"}
        )
        resp = _autenticado().get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])

    def test_m04_out_of_scope(self) -> None:
        url = reverse(
            "matriculas-quantidades-dre",
            kwargs={"dreCodigo": "100001"},
        )
        resp = _autenticado().get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])


class EscolasApiTestCase(TestCase):
    def test_e05(self) -> None:
        seed_matriculas()
        url = reverse(
            "quantidade-alunos-por-turma-escola",
            kwargs={"codigoEscola": "100001"},
        )
        resp = _autenticado().get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 2)

    def test_e24(self) -> None:
        seed_matriculas()
        url = reverse(
            "matriculas-aluno-escola",
            kwargs={
                "codigoEscola": "100001",
                "codigoAluno": "1234567",
            },
        )
        resp = _autenticado().get(url)
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["codigoMatricula"], 998877)

    def test_e24_codigo_invalido_400(self) -> None:
        url = reverse(
            "matriculas-aluno-escola",
            kwargs={
                "codigoEscola": "100001",
                "codigoAluno": "abc",
            },
        )
        resp = _autenticado().get(url)
        self.assertEqual(resp.status_code, 400)


class A18AcompanhamentoApiTestCase(TestCase):
    def test_lista(self) -> None:
        seed_matriculas()
        seed_responsaveis()
        url = reverse("dados-acompanhamento-escolar")
        resp = _autenticado().get(url + "?codigoUe=100001&anoLetivo=2026")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(len(body), 2)

    def test_sem_nenhum_filtro_retorna_400(self) -> None:
        url = reverse("dados-acompanhamento-escolar")
        resp = _autenticado().get(url)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(
            resp.json()["detail"],
            "Nenhum filtro foi especificado para busca de dados "
            "dos alunos para acompanhamento do estudante",
        )

    def test_so_ano_letivo_retorna_400(self) -> None:
        url = reverse("dados-acompanhamento-escolar")
        resp = _autenticado().get(url + "?anoLetivo=2026")
        self.assertEqual(resp.status_code, 400)

    def test_filtra_por_codigo_aluno(self) -> None:
        seed_matriculas()
        seed_responsaveis()
        url = reverse("dados-acompanhamento-escolar")
        resp = _autenticado().get(url + "?codigoAluno=1234567")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["codigoEol"], 1234567)

    def test_filtra_por_cpf_responsavel(self) -> None:
        seed_matriculas()
        seed_responsaveis()
        url = reverse("dados-acompanhamento-escolar")
        resp = _autenticado().get(url + "?cpfResponsavel=12345678901")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["cpfResponsavel"], "12345678901")

    def test_codigo_aluno_invalido_retorna_400(self) -> None:
        url = reverse("dados-acompanhamento-escolar")
        resp = _autenticado().get(url + "?codigoAluno=abc")
        self.assertEqual(resp.status_code, 400)

    def test_paginacao_limit_offset(self) -> None:
        seed_matriculas()
        seed_responsaveis()
        url = reverse("dados-acompanhamento-escolar")
        resp = _autenticado().get(
            url + "?codigoUe=100001&anoLetivo=2026&limit=1"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 1)
        resp2 = _autenticado().get(
            url + "?codigoUe=100001&anoLetivo=2026&limit=1&offset=1"
        )
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(len(resp2.json()), 1)
        # garante que o segundo item é diferente do primeiro
        self.assertNotEqual(resp.json(), resp2.json())

    def test_paginacao_limit_invalido_400(self) -> None:
        url = reverse("dados-acompanhamento-escolar")
        resp = _autenticado().get(
            url + "?codigoUe=100001&anoLetivo=2026&limit=abc"
        )
        self.assertEqual(resp.status_code, 400)


class A15QuantidadeMatriculadosCCApiTestCase(TestCase):
    def test_lista_com_ue_id_e_componentes(self) -> None:
        seed_matriculas()
        url = reverse(
            "quantidade-matriculados-cc", kwargs={"anoLetivo": "2026"}
        )
        resp = _autenticado().get(
            url + "?ueId=100001&componentesCurriculares=1"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(len(resp.json()), 1)

    def test_sem_ue_id_retorna_200(self) -> None:
        seed_matriculas()
        url = reverse(
            "quantidade-matriculados-cc", kwargs={"anoLetivo": "2026"}
        )
        resp = _autenticado().get(url + "?componentesCurriculares=1")
        self.assertEqual(resp.status_code, 200)

    def test_sem_componentes_curriculares_retorna_400(self) -> None:
        url = reverse(
            "quantidade-matriculados-cc", kwargs={"anoLetivo": "2026"}
        )
        resp = _autenticado().get(url + "?ueId=100001")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("componentesCurriculares", resp.json()["detail"])


class A16QuantidadeMatriculadosApiTestCase(TestCase):
    def test_lista_com_ue_codigo(self) -> None:
        seed_matriculas()
        url = reverse("quantidade-matriculados", kwargs={"anoLetivo": "2026"})
        resp = _autenticado().get(url + "?ueCodigo=100001")
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(len(resp.json()), 1)

    def test_sem_ue_codigo_retorna_200(self) -> None:
        seed_matriculas()
        url = reverse("quantidade-matriculados", kwargs={"anoLetivo": "2026"})
        resp = _autenticado().get(url)
        self.assertEqual(resp.status_code, 200)
