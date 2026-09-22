"""Protege resultados e leituras das listagens de alunos."""

from copy import deepcopy
from datetime import UTC, date, datetime
from types import SimpleNamespace

from django.db import connection
from django.test import SimpleTestCase, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.alunos.api.serializers import (
    AlunoDaUeSerializer,
    QuantidadeMatriculadosContratoSerializer,
)
from apps.alunos.models import (
    Aluno,
    Matricula,
    MatriculaAnoLetivo,
    MatriculaTurma,
)
from apps.alunos.services.quantidades import (
    obter_quantidade_matriculados_contrato,
)
from apps.alunos.services.turmas import buscar_alunos_da_ue
from apps.alunos.tests.helpers import seed_matriculas


class QuantidadeRepresentationTest(SimpleTestCase):
    """Preserva tipos, nulos e entradas da representação de quantidades."""

    def test_representa_linhas_cruas_sem_alterar_entrada(self) -> None:
        """Mantém coerções de campo e ordem das linhas."""
        entrada = {
            "quantidade": "28",
            "ordem": "2",
            "modalidade": "EF",
            "ano": 3,
            "turma": "3A",
            "codigo_dre": "001",
            "codigo_ue": "000002",
        }
        nulos = dict.fromkeys(entrada)
        nulos["quantidade"] = 0
        original = entrada.copy()
        resultado = QuantidadeMatriculadosContratoSerializer(
            [entrada, nulos, entrada], many=True
        ).data
        esperado = {
            "quantidade": 28,
            "ordem": 2,
            "modalidade": "EF",
            "ano": "3",
            "turma": "3A",
            "dre_codigo": "001",
            "ue_codigo": "000002",
        }
        esperado_nulos = dict.fromkeys(esperado)
        esperado_nulos["quantidade"] = 0
        self.assertEqual(resultado, [esperado, esperado_nulos, esperado])
        self.assertEqual(entrada, original)

    def test_preserva_entrada_ja_normalizada_e_objeto(self) -> None:
        """Mantém a representação das entradas sem nomes de coluna."""
        entrada = {
            "quantidade": "0",
            "ordem": None,
            "modalidade": "",
            "ano": None,
            "turma": "",
            "dre_codigo": None,
            "ue_codigo": "000002",
        }
        for item in (entrada, SimpleNamespace(**entrada)):
            with self.subTest(item=type(item).__name__):
                self.assertEqual(
                    QuantidadeMatriculadosContratoSerializer(item).data,
                    {**entrada, "quantidade": 0},
                )

    def test_preserva_erro_de_campo_obrigatorio_ausente(self) -> None:
        """Não mascara uma linha crua incompleta com valores padrão."""
        with self.assertRaises(KeyError):
            _ = QuantidadeMatriculadosContratoSerializer(
                {"codigo_dre": "001"}
            ).data


@override_settings(TIME_ZONE="America/Sao_Paulo", USE_TZ=True)
class AlunoDaUeRepresentationTest(SimpleTestCase):
    """Preserva os dados e valores padrão da listagem por UE."""

    def test_preserva_nulos_campos_ausentes_e_repeticoes(self) -> None:
        """Não omite contato nulo nem transforma ausência em string."""
        entrada = {
            "matricula": {"aluno_id": "123"},
            "matricula_turma": {"codigo_turma": "456"},
            "aluno": {},
            "ano_letivo": "2026",
        }
        original = deepcopy(entrada)
        esperado = {
            "codigo_aluno": 123,
            "tipo_turno": None,
            "ano_letivo": 2026,
            "nome_aluno": "",
            "nome_social_aluno": None,
            "codigo_situacao_matricula": 0,
            "situacao_matricula": "Não Informada",
            "data_situacao": None,
            "data_nascimento": None,
            "numero_aluno_chamada": "0",
            "codigo_turma": 456,
            "nome_responsavel": None,
            "tipo_responsavel": None,
            "ddd_celular": None,
            "numero_celular": None,
            "data_atualizacao_contato": "0001-01-01T00:00:00-03:06:28",
            "codigo_tipo_turma": None,
            "turma_nome": None,
            "etapa_ensino": None,
            "ciclo_ensino": None,
            "desc_etapa_ensino": None,
            "desc_ciclo_ensino": None,
            "data_atualizacao_tabela": "0001-01-01T00:00:00-03:06:28",
        }
        resultado = AlunoDaUeSerializer([entrada, entrada], many=True).data
        self.assertEqual(resultado, [esperado, esperado])
        self.assertEqual(list(resultado[0]), list(esperado))
        self.assertEqual(entrada, original)
        for item in (esperado, SimpleNamespace(**esperado)):
            self.assertEqual(AlunoDaUeSerializer(item).data, esperado)

    def test_preserva_coercao_de_datas_e_prioridade_da_data_hora(self) -> None:
        """Mantém formatos de datas e situação da matrícula-turma."""
        entrada = {
            "matricula": {"aluno_id": "123"},
            "matricula_turma": {
                "codigo_turma": "456",
                "codigo_situacao_aluno": "14",
                "ano_letivo_turma": 2025,
                "data_situacao_aluno": date(2026, 2, 1),
                "data_situacao_aluno_data_hora": datetime(2026, 2, 2, 10, 30),
                "numero_chamada": "001",
            },
            "aluno": {
                "nome": "ALUNO TESTE",
                "data_nascimento": date(2015, 1, 2),
            },
            "ano_letivo": 2026,
        }
        resultado = AlunoDaUeSerializer(entrada).data
        self.assertEqual(resultado["data_situacao"], "2026-02-02 10:30:00")
        self.assertEqual(resultado["data_nascimento"], "2015-01-02")
        self.assertEqual(resultado["ano_letivo"], 2025)
        self.assertEqual(resultado["codigo_situacao_matricula"], 14)
        self.assertEqual(resultado["situacao_matricula"], "Remanejado Saída")
        self.assertEqual(resultado["numero_aluno_chamada"], "001")
        entrada["matricula_turma"]["data_situacao_aluno_data_hora"] = None
        self.assertEqual(
            AlunoDaUeSerializer(entrada).data["data_situacao"], "2026-02-01"
        )

    def test_datas_padrao_respeitam_o_fuso_de_cada_instancia(self) -> None:
        """Não reutiliza a formatação de outra requisição ou fuso."""
        entrada = {
            "matricula": {"aluno_id": 123},
            "matricula_turma": {"codigo_turma": 456},
            "aluno": {},
            "ano_letivo": 2026,
        }
        for fuso, esperado in (
            ("UTC", "0001-01-01T00:00:00Z"),
            ("America/Sao_Paulo", "0001-01-01T00:00:00-03:06:28"),
        ):
            with self.subTest(fuso=fuso), timezone.override(fuso):
                linhas = AlunoDaUeSerializer(
                    [entrada, entrada], many=True
                ).data
                for linha in linhas:
                    self.assertEqual(
                        linha["data_atualizacao_contato"], esperado
                    )
                    self.assertEqual(
                        linha["data_atualizacao_tabela"], esperado
                    )


class ListagensQueriesTest(TestCase):
    """Mantém leituras em lote e a seleção dos vínculos."""

    def test_ue_preserva_aluno_ausente_e_tipo_da_data(self) -> None:
        """Não descarta matrícula sem aluno nem perde o fuso da data."""
        seed_matriculas()
        data = datetime(2026, 2, 1, 12, 30, tzinfo=UTC)
        MatriculaTurma.objects.filter(codigo_matricula=998877).update(
            data_situacao_aluno_data_hora=data
        )
        Matricula.objects.filter(pk=998877).update(aluno_id=112233)
        try:
            with self.assertNumQueries(1):
                dados = buscar_alunos_da_ue("100001", 2026)
            self.assertEqual(len(dados), 2)
            self.assertEqual(dados[0]["aluno"], {})
            self.assertEqual(dados[0]["matricula"]["aluno_id"], 112233)
            self.assertEqual(
                dados[0]["matricula_turma"]["data_situacao_aluno_data_hora"],
                data,
            )
            self.assertEqual(
                len(buscar_alunos_da_ue("100001", 2026, codigo_eol="223")),
                1,
            )
            self.assertEqual(
                buscar_alunos_da_ue("100001", 2026, nome_aluno="JOAO"), []
            )
        finally:
            Matricula.objects.filter(pk=998877).update(aluno_id=1234567)

    def test_ue_exclui_vinculos_sem_matricula_atual(self) -> None:
        """Não inclui matrículas históricas nem vínculos órfãos."""
        seed_matriculas()
        Matricula.objects.filter(pk=998878).update(origem_atual=False)
        MatriculaTurma.objects.create(
            codigo_matricula=999999,
            codigo_turma=10,
            sequencia=1,
            codigo_ue_turma="100001",
            ano_letivo_turma=2026,
            origem_atual=True,
        )
        with self.assertNumQueries(1):
            dados = buscar_alunos_da_ue("100001", 2026)
        self.assertEqual(
            [linha["matricula_turma"]["codigo_turma"] for linha in dados],
            [12345],
        )

    def test_ue_preserva_filtros_literais_e_minusculas_python(self) -> None:
        """Não converte caracteres literais em curingas nem usa nome social."""
        seed_matriculas()
        Aluno.objects.filter(pk=1234567).update(
            nome="İSTANBUL %_ ALUNO", nome_social="SOCIAL APENAS"
        )
        for nome, codigo, esperado in (
            (" %_ ", None, [1234567]),
            ("istanbul", None, []),
            ("i\u0307", "234", [1234567]),
            ("SOCIAL APENAS", None, []),
            (" ", " ", [1234567, 7654321]),
            (None, "%_", []),
            ("i\u0307", "765", []),
        ):
            with self.subTest(nome=nome, codigo=codigo):
                with self.assertNumQueries(1):
                    dados = buscar_alunos_da_ue(
                        "100001", 2026, nome_aluno=nome, codigo_eol=codigo
                    )
                self.assertEqual(
                    [linha["matricula"]["aluno_id"] for linha in dados],
                    esperado,
                )

    def test_ue_preserva_vinculos_e_busca_somente_campos_consumidos(
        self,
    ) -> None:
        """Não cresce por aluno nem transfere dados pessoais não usados."""
        seed_matriculas()
        MatriculaTurma.objects.create(
            codigo_matricula=998877,
            codigo_turma=12345,
            codigo_situacao_aluno=14,
            sequencia=2,
            codigo_tipo_turma=3,
            codigo_ue_turma="100001",
            ano_letivo_turma=2026,
            origem_atual=True,
        )
        with CaptureQueriesContext(connection) as consultas:
            dados = buscar_alunos_da_ue("100001", 2026)
        self.assertEqual(len(consultas), 1)
        self.assertEqual(
            [
                (
                    d["matricula_turma"]["codigo_turma"],
                    d["matricula_turma"]["codigo_situacao_aluno"],
                )
                for d in dados
            ],
            [(12345, 1), (12345, 14), (22222, 1)],
        )
        with self.assertNumQueries(0):
            corpo = AlunoDaUeSerializer(dados, many=True).data
        self.assertEqual(len(corpo), 3)
        self.assertEqual(corpo[1]["codigo_tipo_turma"], 3)
        self.assertEqual(corpo[1]["numero_aluno_chamada"], "0")
        self.assertIsNone(corpo[0]["nome_social_aluno"])
        consulta_alunos = consultas.captured_queries[-1]["sql"]
        self.assertNotIn('"cpf"', consulta_alunos)
        self.assertNotIn('"nome_mae"', consulta_alunos)
        self.assertNotIn('"nis"', consulta_alunos)

    def test_quantidade_usa_uma_consulta_e_preserva_nulos(self) -> None:
        """Não introduz consultas por linha ao representar agregados."""
        MatriculaAnoLetivo.objects.create(
            codigo_dre="001",
            codigo_ue="000002",
            tipo_escola=1,
            ano_letivo=2026,
            codigo_modalidade=5,
            modalidade="EF",
            ano="3",
            turma="3A",
            quantidade=28,
            ordem=None,
        )
        with self.assertNumQueries(1):
            dados = obter_quantidade_matriculados_contrato(2026)
            corpo = QuantidadeMatriculadosContratoSerializer(
                dados, many=True
            ).data
        self.assertEqual(
            corpo,
            [
                {
                    "quantidade": 28,
                    "ordem": None,
                    "modalidade": "EF",
                    "ano": "3",
                    "turma": "3A",
                    "dre_codigo": "001",
                    "ue_codigo": "000002",
                }
            ],
        )
