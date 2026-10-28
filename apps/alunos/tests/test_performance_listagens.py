"""Protege resultados e leituras das listagens de alunos."""

import json
from copy import deepcopy
from datetime import UTC, date, datetime
from functools import partial
from hashlib import sha256
from types import SimpleNamespace
from unittest.mock import patch

from django.db import connection
from django.test import SimpleTestCase, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.alunos.api.serializers import (
    AlunoDaUeSerializer,
    QuantidadeMatriculadosContratoSerializer,
    TurmaDoAlunoSerializer,
)
from apps.alunos.models import (
    Aluno,
    Matricula,
    MatriculaAnoLetivo,
    MatriculaTurma,
    ResponsavelAluno,
)
from apps.alunos.services import turmas as turmas_service
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

    def test_quantidade_filtra_pares_sem_multiplicar_linhas(self) -> None:
        """Seleciona no banco a mesma UE e turma, sem duplicar agregados."""
        seed_matriculas()
        for ue, nome in (
            ("100001", "5A"),
            ("100001", "6A"),
            ("100002", "5A"),
            ("100001", "5a"),
            ("100001", "5A "),
        ):
            MatriculaAnoLetivo.objects.create(
                codigo_dre="001",
                codigo_ue=ue,
                tipo_escola=1,
                ano_letivo=2026,
                codigo_modalidade=5,
                modalidade="EF",
                ano="5",
                turma=nome,
                quantidade=28,
                ordem=None,
            )
        MatriculaTurma.objects.create(
            codigo_matricula=998877,
            codigo_turma=12345,
            sequencia=2,
            codigo_ue_turma="100001",
            nome_turma="5A",
            origem_atual=True,
        )
        esperado = [
            linha
            for linha in obter_quantidade_matriculados_contrato(2026)
            if (linha["codigo_ue"], linha["turma"]) == ("100001", "5A")
        ]
        with self.assertNumQueries(1):
            resultado = obter_quantidade_matriculados_contrato(
                2026, turma=[12345, 12345]
            )
        self.assertEqual(resultado, esperado)
        self.assertEqual(len(resultado), 1)

    def test_quantidade_ignora_turmas_sem_par_atual_valido(self) -> None:
        """Exclui origens históricas, pares vazios e códigos inexistentes."""
        for numero, (ue, nome, origem) in enumerate(
            (
                ("", "5A", True),
                ("100001", "", True),
                (None, "5A", True),
                ("100001", None, True),
                ("100001", "5A", False),
                ("100001", "5A", None),
            ),
            start=1,
        ):
            MatriculaTurma.objects.create(
                codigo_matricula=numero,
                codigo_turma=12345,
                sequencia=1,
                codigo_ue_turma=ue,
                nome_turma=nome,
                origem_atual=origem,
            )
            MatriculaAnoLetivo.objects.create(
                codigo_dre="001",
                codigo_ue=ue or "",
                tipo_escola=1,
                ano_letivo=2026,
                codigo_modalidade=5,
                modalidade="EF",
                ano="5",
                turma=nome,
                quantidade=28,
            )
        for turmas in ([12345], [99999]):
            with self.subTest(turmas=turmas), self.assertNumQueries(1):
                self.assertEqual(
                    obter_quantidade_matriculados_contrato(2026, turma=turmas),
                    [],
                )

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


class TurmasLotesPerformanceTest(TestCase):
    """Preserva as linhas das turmas e limita leituras dos lotes."""

    @classmethod
    def setUpTestData(cls) -> None:
        """Cria vínculos sintéticos com origens e contatos distintos."""
        for codigo in range(101, 107):
            Aluno.objects.create(
                codigo_aluno=codigo,
                nome=f"ALUNO SINTETICO {codigo}",
                nome_social="SOCIAL" if codigo == 101 else None,
                data_nascimento=date(2015, 1, 2),
                cpf="00000000000" if codigo == 101 else None,
            )
            Matricula.objects.create(
                codigo_matricula=codigo,
                aluno_id=codigo,
                codigo_ue="000001",
                ano_letivo=2026,
                codigo_situacao_matricula=1,
                situacao_matricula="Ativo",
                data_situacao_matricula=date(2026, 2, 1),
                origem_atual=True,
            )
            if codigo != 103:
                for sequencia in (1, 2):
                    MatriculaTurma.objects.create(
                        codigo_matricula=codigo,
                        codigo_turma=1000 + codigo,
                        sequencia=sequencia,
                        codigo_situacao_aluno=2 if codigo == 104 else 1,
                        codigo_tipo_turma=1,
                        numero_chamada="0" if sequencia == 1 else None,
                        data_situacao_aluno=date(2026, 2, sequencia),
                        data_atualizacao_tabela=datetime(
                            2026, 2, sequencia, tzinfo=UTC
                        ),
                        origem_atual=True,
                    )
            Matricula.objects.create(
                codigo_matricula=1000 + codigo,
                aluno_id=codigo,
                codigo_ue="000002",
                ano_letivo=2025,
                codigo_situacao_matricula=14,
                situacao_matricula="Remanejado Saída",
                data_situacao_matricula=date(2025, 3, 1),
                data_situacao_matricula_historica=datetime(
                    2025, 2, 1, tzinfo=UTC
                ),
                origem_atual=False,
                origem_historica=True,
            )
            MatriculaTurma.objects.create(
                codigo_matricula=1000 + codigo,
                codigo_turma=2000 + codigo,
                sequencia=1,
                codigo_situacao_aluno=14,
                codigo_tipo_turma=3,
                origem_atual=False,
            )
        for numero in (3, 1, 2):
            ResponsavelAluno.objects.create(
                codigo_responsavel=numero,
                aluno_id=101,
                nome=f"RESPONSAVEL SINTETICO {numero}",
                tipo_responsavel=numero,
                ddd_celular="00" if numero == 1 else None,
                numero_celular="000000000" if numero == 1 else None,
                data_fim_vinculo=date(2025, 1, 1) if numero == 3 else None,
                data_atualizacao_tabela=datetime(2026, 1, numero, tzinfo=UTC),
            )
        Matricula.objects.create(
            codigo_matricula=2104,
            aluno_id=104,
            codigo_ue="000003",
            ano_letivo=2026,
            codigo_situacao_matricula=1,
            situacao_matricula="Ativo",
            origem_atual=False,
            origem_historica=True,
        )
        MatriculaTurma.objects.create(
            codigo_matricula=2104,
            codigo_turma=3104,
            sequencia=1,
            codigo_situacao_aluno=1,
            codigo_tipo_turma=1,
            origem_atual=False,
        )

    def setUp(self) -> None:
        """Fixa o ano usado para selecionar a origem das matrículas."""
        self.enterContext(
            patch(
                "apps.alunos.services.turmas.timezone.now",
                return_value=datetime(2026, 10, 27, tzinfo=UTC),
            )
        )

    @staticmethod
    def _hash(linhas: list) -> str:
        dados = TurmaDoAlunoSerializer(linhas, many=True).data
        return sha256(
            json.dumps(dados, sort_keys=True, ensure_ascii=True).encode()
        ).hexdigest()

    def test_r03_lote_faz_quatro_consultas(self) -> None:
        """Não repete a busca de vínculos para cada aluno informado."""
        for codigos in (
            [101],
            [106, 101, 102, 103, 104, 105],
            [101, 102, 101],
        ):
            with self.subTest(codigos=codigos):
                with CaptureQueriesContext(connection) as capturadas:
                    linhas = turmas_service.obter_alunos_por_codigos_e_ano(
                        codigos, 2026
                    )
                self.assertEqual(len(capturadas), 4)
                self.assertTrue(linhas)

    def test_paridade_r03_com_resultado_anterior(self) -> None:
        """Mantém ordem, multiplicidade, ausências e origem das linhas."""
        cenarios = {
            "um": [101],
            "seis": [106, 101, 102, 103, 104, 105],
            "repetido": [101, 102, 101],
            "inexistente": [9999],
            "misto": [9999, 101],
            "sem_turma": [103],
            "sem_responsavel": [102],
            "vazio": [],
        }
        for nome, codigos in cenarios.items():
            for ano in (2025, 2026, 2027):
                with self.subTest(cenario=nome, ano=ano):
                    linhas = turmas_service.obter_alunos_por_codigos_e_ano(
                        codigos, ano
                    )
                    self.assertEqual(
                        self._hash(linhas),
                        HASHES_TURMAS_ANTES[f"r03_{ano}_{nome}"],
                    )

    def test_r03_sem_codigos_nao_consulta(self) -> None:
        """Encerra o lote vazio sem consultar o banco."""
        with self.assertNumQueries(0):
            self.assertEqual(
                turmas_service.obter_alunos_por_codigos_e_ano([], 2026), []
            )

    def test_fatia_lotes_e_preserva_repeticao_entre_blocos(self) -> None:
        """Limita parâmetros sem perder a posição dos códigos repetidos."""
        Aluno.objects.bulk_create(
            [
                Aluno(codigo_aluno=codigo, nome="ALUNO SINTETICO")
                for codigo in range(10000, 10501)
            ]
        )
        Matricula.objects.bulk_create(
            [
                Matricula(
                    codigo_matricula=codigo,
                    aluno_id=codigo,
                    codigo_ue="000001",
                    ano_letivo=2026,
                    codigo_situacao_matricula=1,
                    situacao_matricula="Ativo",
                    origem_atual=True,
                )
                for codigo in range(10000, 10501)
            ]
        )
        MatriculaTurma.objects.bulk_create(
            [
                MatriculaTurma(
                    codigo_matricula=codigo,
                    codigo_turma=codigo,
                    sequencia=1,
                    codigo_situacao_aluno=1,
                    origem_atual=True,
                )
                for codigo in range(10000, 10501)
            ]
        )
        codigos = [*range(10000, 10501), 10000]
        for ano in (None, 2026):
            with self.subTest(ano=ano):
                with CaptureQueriesContext(connection) as capturadas:
                    linhas = (
                        turmas_service.obter_alunos_por_codigos(codigos)
                        if ano is None
                        else turmas_service.obter_alunos_por_codigos_e_ano(
                            codigos, ano
                        )
                    )
                self.assertEqual(len(capturadas), 8)
                self.assertEqual(
                    [linha["matricula"]["aluno_id"] for linha in linhas],
                    codigos,
                )

    def test_r02_lote_faz_quatro_consultas(self) -> None:
        """Não repete a consulta dos dados atuais para cada código."""
        for codigos in (
            [101],
            [106, 101, 102, 103, 104, 105],
            [101, 102, 101],
        ):
            with self.subTest(codigos=codigos):
                with CaptureQueriesContext(connection) as capturadas:
                    linhas = turmas_service.obter_alunos_por_codigos(codigos)
                self.assertEqual(len(capturadas), 4)
                self.assertTrue(linhas)

    def test_paridade_r02_com_resultado_anterior(self) -> None:
        """Mantém todas as sequências, contatos e linhas sem turma."""
        cenarios = {
            "um": [101],
            "seis": [106, 101, 102, 103, 104, 105],
            "repetido": [101, 102, 101],
            "inexistente": [9999],
            "misto": [9999, 101],
            "sem_turma": [103],
            "sem_responsavel": [102],
            "vazio": [],
        }
        for nome, codigos in cenarios.items():
            with self.subTest(cenario=nome):
                self.assertEqual(
                    self._hash(
                        turmas_service.obter_alunos_por_codigos(codigos)
                    ),
                    HASHES_TURMAS_ANTES[f"r02_{nome}"],
                )

    def test_r13_fallback_reaproveita_cadastro(self) -> None:
        """Refaz só vínculos quando a origem atual é filtrada por situação."""
        with CaptureQueriesContext(connection) as capturadas:
            linhas = turmas_service.buscar_turmas_do_aluno_com_historico(
                104, 2026, False
            )
        self.assertEqual(len(capturadas), 6)
        self.assertEqual(
            self._hash(linhas), HASHES_TURMAS_ANTES["r13_fallback"]
        )

    def test_r13_preserva_origens_e_fallback(self) -> None:
        """Mantém a resposta atual e histórica com os mesmos filtros."""
        for nome, argumentos in (
            ("r13_atual", (101, 2026, False, False, False)),
            ("r13_historico", (101, 2025, True, False, False)),
        ):
            with self.subTest(cenario=nome):
                with CaptureQueriesContext(connection) as capturadas:
                    linhas = (
                        turmas_service.buscar_turmas_do_aluno_com_historico(
                            *argumentos
                        )
                    )
                self.assertEqual(len(capturadas), 4)
                self.assertEqual(self._hash(linhas), HASHES_TURMAS_ANTES[nome])

    def test_r13_inexistente_nao_consulta_cadastro(self) -> None:
        """Dispensa o cadastro quando ambas as origens estão vazias."""
        with self.assertNumQueries(2):
            self.assertEqual(
                turmas_service.buscar_turmas_do_aluno_com_historico(
                    9999, 2026, False
                ),
                [],
            )

    def test_turmas_consultam_apenas_contatos_consumidos(self) -> None:
        """Mantém o contrato sem ler documentos e endereços dos contatos."""
        consultas = (
            (
                "r15",
                partial(
                    turmas_service.buscar_turmas_do_aluno_por_situacao_matricula,
                    101,
                    2026,
                    False,
                    False,
                ),
            ),
            ("r16", lambda: turmas_service.buscar_turmas_do_aluno(101)),
            (
                "r16",
                lambda: turmas_service.buscar_turmas_srm_regular_do_aluno(
                    101, []
                ),
            ),
        )
        for nome, consultar in consultas:
            with self.subTest(cenario=nome):
                with CaptureQueriesContext(connection) as capturadas:
                    linhas = consultar()
                self.assertEqual(len(capturadas), 4)
                self.assertEqual(self._hash(linhas), HASHES_TURMAS_ANTES[nome])
                sql = next(
                    q["sql"]
                    for q in capturadas
                    if 'FROM "responsavel_aluno"' in q["sql"]
                )
                for coluna in ("cpf", "email", "logradouro", "cep"):
                    self.assertNotIn(f'"{coluna}"', sql)

    def test_fatia_matriculas_quando_um_aluno_excede_o_limite(self) -> None:
        """Limita também o filtro de turmas para alunos com muitos vínculos."""
        Matricula.objects.bulk_create(
            [
                Matricula(
                    codigo_matricula=codigo,
                    aluno_id=101,
                    codigo_ue="000001",
                    ano_letivo=2026,
                    codigo_situacao_matricula=1,
                    situacao_matricula="Ativo",
                    origem_atual=True,
                )
                for codigo in range(10000, 10501)
            ]
        )
        MatriculaTurma.objects.bulk_create(
            [
                MatriculaTurma(
                    codigo_matricula=codigo,
                    codigo_turma=codigo,
                    sequencia=1,
                    codigo_situacao_aluno=1,
                    origem_atual=True,
                )
                for codigo in range(10000, 10501)
            ]
        )
        for ano in (None, 2026):
            with self.subTest(ano=ano):
                with CaptureQueriesContext(connection) as capturadas:
                    linhas = (
                        turmas_service.obter_alunos_por_codigos([101])
                        if ano is None
                        else turmas_service.obter_alunos_por_codigos_e_ano(
                            [101], ano
                        )
                    )
                self.assertEqual(len(capturadas), 5)
                self.assertEqual(
                    len(
                        {
                            linha["matricula"]["codigo_matricula"]
                            for linha in linhas
                        }
                    ),
                    502,
                )

    def test_lotes_preservam_ordem_das_consultas_individuais(self) -> None:
        """Preserva a ordem dos empates entre matrículas e turmas."""
        codigos = [106, 101, 102, 103, 104, 105, 101]
        for codigo in range(101, 107):
            Matricula.objects.create(
                codigo_matricula=4000 + codigo,
                aluno_id=codigo,
                codigo_ue="000001",
                ano_letivo=2026,
                codigo_situacao_matricula=1,
                situacao_matricula="Ativo",
                data_situacao_matricula=date(2026, 2, 1),
                origem_atual=True,
            )
            for matricula in (codigo, 4000 + codigo):
                for turma in (5000 + codigo, 6000 + codigo):
                    MatriculaTurma.objects.create(
                        codigo_matricula=matricula,
                        codigo_turma=turma,
                        sequencia=2,
                        codigo_situacao_aluno=1,
                        codigo_tipo_turma=1,
                        origem_atual=True,
                        data_situacao_aluno=date(2026, 2, 2),
                        data_atualizacao_tabela=datetime(
                            2026, 2, 2, tzinfo=UTC
                        ),
                    )
        for ano in (None, 2026):
            with self.subTest(ano=ano):
                referencia = [
                    linha
                    for codigo in codigos
                    for linha in (
                        turmas_service._turmas_atuais_por_aluno(codigo)
                        if ano is None
                        else turmas_service._consultar_turmas_do_aluno(
                            codigo, ano, False, False, False
                        )
                    )
                ]
                with CaptureQueriesContext(connection) as capturadas:
                    lote = (
                        turmas_service.obter_alunos_por_codigos(codigos)
                        if ano is None
                        else turmas_service.obter_alunos_por_codigos_e_ano(
                            codigos, ano
                        )
                    )
                self.assertEqual(len(capturadas), 4)
                self.assertEqual(self._hash(lote), self._hash(referencia))


# Capturados no código f5c968f, com a mesma massa sintética e serializer.
HASHES_TURMAS_ANTES = {
    "r02_um": (
        "c1b9288f7dfc5fdf26696cf37256697e" "6ab49799dcb2956468874898931abcc2"
    ),
    "r03_2025_um": (
        "04ef12217097509f5d0241036e02e275" "43cf01fa6a93e641887342a47ebfb808"
    ),
    "r03_2026_um": (
        "2cb676128082eb1760ad42c98038d118" "25ee641e8e2a1e1798704122f52fc10b"
    ),
    "r03_2027_um": (
        "4f53cda18c2baa0c0354bb5f9a3ecbe5" "ed12ab4d8e11ba873c2f11161202b945"
    ),
    "r02_seis": (
        "7b21e2c1c2ae169687d7740b223adf4a" "098c3329d027c442a95a43808ac7e9f0"
    ),
    "r03_2025_seis": (
        "786ceedf6897958f3d333ebb8a169b2e" "6fbb3093dcd90db81a57d2f7b74c1ece"
    ),
    "r03_2026_seis": (
        "9ee3e60d901930e877026ce10f2de964" "a7b08aa33a53ecd4afce3a67f82e6cce"
    ),
    "r03_2027_seis": (
        "4f53cda18c2baa0c0354bb5f9a3ecbe5" "ed12ab4d8e11ba873c2f11161202b945"
    ),
    "r02_repetido": (
        "3bc263b15a0e825778d809f35d1e928d" "85e69280aeed3de6bf4f5ae07ffd5f92"
    ),
    "r03_2025_repetido": (
        "35408f9615421d7ed44d9eeafb5ea077" "75d57b6936b60b7632596683893a3ce5"
    ),
    "r03_2026_repetido": (
        "f1d9304d03f73b7af51080862666bbfb" "d66d46325ddb46adac42c8f0dd133b6a"
    ),
    "r03_2027_repetido": (
        "4f53cda18c2baa0c0354bb5f9a3ecbe5" "ed12ab4d8e11ba873c2f11161202b945"
    ),
    "r02_inexistente": (
        "4f53cda18c2baa0c0354bb5f9a3ecbe5" "ed12ab4d8e11ba873c2f11161202b945"
    ),
    "r03_2025_inexistente": (
        "4f53cda18c2baa0c0354bb5f9a3ecbe5" "ed12ab4d8e11ba873c2f11161202b945"
    ),
    "r03_2026_inexistente": (
        "4f53cda18c2baa0c0354bb5f9a3ecbe5" "ed12ab4d8e11ba873c2f11161202b945"
    ),
    "r03_2027_inexistente": (
        "4f53cda18c2baa0c0354bb5f9a3ecbe5" "ed12ab4d8e11ba873c2f11161202b945"
    ),
    "r02_misto": (
        "c1b9288f7dfc5fdf26696cf37256697e" "6ab49799dcb2956468874898931abcc2"
    ),
    "r03_2025_misto": (
        "04ef12217097509f5d0241036e02e275" "43cf01fa6a93e641887342a47ebfb808"
    ),
    "r03_2026_misto": (
        "2cb676128082eb1760ad42c98038d118" "25ee641e8e2a1e1798704122f52fc10b"
    ),
    "r03_2027_misto": (
        "4f53cda18c2baa0c0354bb5f9a3ecbe5" "ed12ab4d8e11ba873c2f11161202b945"
    ),
    "r02_sem_turma": (
        "9dba1e965d4935bdd9a8dbd3bf4f50af" "a269ccd5a8684cb4aa66715c65dfa6e8"
    ),
    "r03_2025_sem_turma": (
        "10422123667bc5d9070450d05bd38615" "65541cd10f01a76a1e7e0faa299112fb"
    ),
    "r03_2026_sem_turma": (
        "4f53cda18c2baa0c0354bb5f9a3ecbe5" "ed12ab4d8e11ba873c2f11161202b945"
    ),
    "r03_2027_sem_turma": (
        "4f53cda18c2baa0c0354bb5f9a3ecbe5" "ed12ab4d8e11ba873c2f11161202b945"
    ),
    "r02_sem_responsavel": (
        "9e607fa7d99085d064ec045f396e4b17" "f204945e716aecaa2358c0a7f85149c0"
    ),
    "r03_2025_sem_responsavel": (
        "6e303f005fa5d202dfd33fe67a67210c" "dee4ed6715ffb5c86e1a67a7fbf67b57"
    ),
    "r03_2026_sem_responsavel": (
        "f2339e5d931c753c7036e14bf60bd73a" "446f59a0a5282ad94547cf4b96bd283f"
    ),
    "r03_2027_sem_responsavel": (
        "4f53cda18c2baa0c0354bb5f9a3ecbe5" "ed12ab4d8e11ba873c2f11161202b945"
    ),
    "r02_vazio": (
        "4f53cda18c2baa0c0354bb5f9a3ecbe5" "ed12ab4d8e11ba873c2f11161202b945"
    ),
    "r03_2025_vazio": (
        "4f53cda18c2baa0c0354bb5f9a3ecbe5" "ed12ab4d8e11ba873c2f11161202b945"
    ),
    "r03_2026_vazio": (
        "4f53cda18c2baa0c0354bb5f9a3ecbe5" "ed12ab4d8e11ba873c2f11161202b945"
    ),
    "r03_2027_vazio": (
        "4f53cda18c2baa0c0354bb5f9a3ecbe5" "ed12ab4d8e11ba873c2f11161202b945"
    ),
    "r13_fallback": (
        "4f54faeae64e8f4685c87a1c955d348d" "9357be59b251e27783a0ae66625d8431"
    ),
    "r13_atual": (
        "2cb676128082eb1760ad42c98038d118" "25ee641e8e2a1e1798704122f52fc10b"
    ),
    "r13_historico": (
        "04ef12217097509f5d0241036e02e275" "43cf01fa6a93e641887342a47ebfb808"
    ),
    "r15": (
        "2cb676128082eb1760ad42c98038d118" "25ee641e8e2a1e1798704122f52fc10b"
    ),
    "r16": (
        "2cb676128082eb1760ad42c98038d118" "25ee641e8e2a1e1798704122f52fc10b"
    ),
}
