"""Regressões de contrato e custo das consultas de autocomplete."""

from datetime import UTC, date, datetime
from unittest.mock import patch

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from apps.alunos.api.serializers import AlunoAutocompleteSerializer
from apps.alunos.models import Matricula, MatriculaTurma
from apps.alunos.services.autocomplete import (
    buscar_alunos_ativos_autocomplete,
    buscar_alunos_autocomplete,
)
from apps.alunos.tests.helpers import seed_matriculas


class AutocompleteOtimizacaoTestCase(TestCase):
    """Preserva a seleção de alunos ao reduzir o custo de leitura."""

    def setUp(self) -> None:
        seed_matriculas()
        clock = patch(
            "django.utils.timezone.now",
            return_value=datetime(2026, 9, 9, tzinfo=UTC),
        )
        clock.start()
        self.addCleanup(clock.stop)

    def test_nome_e_limite_preservam_payload(self) -> None:
        """Retorna os mesmos campos após filtrar pelo nome."""
        dados = buscar_alunos_autocomplete(
            "100001", 2026, nome_aluno="  maria  ", limite=1
        )
        self.assertEqual(
            AlunoAutocompleteSerializer(dados, many=True).data,
            [
                {
                    "codigo_aluno": 7654321,
                    "nome_aluno": "MARIA OLIVEIRA",
                    "nome_social_aluno": "MARIA SOCIAL",
                    "codigo_turma": 22222,
                    "numero_aluno_chamada": "7",
                    "turma": None,
                    "modalidade": None,
                }
            ],
        )

    def test_codigo_e_nome_sao_combinados(self) -> None:
        """Exige que código e nome correspondam ao mesmo aluno."""
        self.assertEqual(
            buscar_alunos_autocomplete(
                "100001", 2026, codigo_eol="1234567", nome_aluno="MARIA"
            ),
            [],
        )

    def test_codigo_invalido_dispensa_banco(self) -> None:
        """Evita percorrer vínculos quando o código não pode corresponder."""
        with self.assertNumQueries(0):
            dados = buscar_alunos_autocomplete(
                "100001", 2026, codigo_eol="invalido"
            )
        self.assertEqual(dados, [])

    def test_filtro_de_aluno_ocorre_na_consulta_de_vinculos(self) -> None:
        """Evita transferir vínculos de outros alunos ao buscar por código."""
        with CaptureQueriesContext(connection) as queries:
            dados = buscar_alunos_autocomplete(
                "100001", 2026, codigo_eol="7654321", limite=1
            )
        self.assertEqual(len(dados), 1)
        self.assertIn("codigo_aluno", queries[0]["sql"])
        self.assertIn("7654321", queries[0]["sql"])

    def test_somente_ativos_continua_sem_efeito(self) -> None:
        """Mantém o parâmetro de compatibilidade sem alterar a seleção."""
        Matricula.objects.filter(pk=998877).update(
            codigo_situacao_matricula=14
        )
        self.assertEqual(
            buscar_alunos_autocomplete("100001", 2026, somente_ativos=True),
            buscar_alunos_autocomplete("100001", 2026, somente_ativos=False),
        )

    def test_nome_sem_codigo_nao_amplia_varredura(self) -> None:
        """Mantém a leitura inicial restrita aos vínculos da UE."""
        with CaptureQueriesContext(connection) as queries:
            dados = buscar_alunos_autocomplete(
                "100001", 2026, nome_aluno="MARIA", limite=1
            )
        self.assertEqual(len(dados), 1)
        self.assertNotIn('"aluno"', queries[0]["sql"])
        self.assertIn("100001", queries[0]["sql"])

    def test_historico_filtra_situacao_da_matricula(self) -> None:
        """Não confunde situação histórica da matrícula com a do vínculo."""
        Matricula.objects.update(origem_atual=False)
        MatriculaTurma.objects.update(
            origem_atual=False, codigo_situacao_aluno=14
        )
        Matricula.objects.filter(pk=998877).update(
            codigo_situacao_matricula=14
        )
        dados = buscar_alunos_autocomplete("100001", 2026, eh_historico=True)
        self.assertEqual(
            [d["matricula"]["aluno_id"] for d in dados], [7654321]
        )

    def test_ano_anterior_seleciona_origem_historica(self) -> None:
        """Consulta o histórico mesmo sem sinalização explícita."""
        Matricula.objects.update(origem_atual=False)
        MatriculaTurma.objects.update(
            origem_atual=False, ano_letivo_turma=2025
        )
        self.assertEqual(len(buscar_alunos_autocomplete("100001", 2025)), 2)

    def test_ano_zero_preserva_ramos_atual_e_historico(self) -> None:
        """Reúne as duas origens usando o ano da turma."""
        Matricula.objects.filter(pk=998878).update(origem_atual=False)
        MatriculaTurma.objects.filter(codigo_matricula=998878).update(
            origem_atual=False, ano_letivo_turma=2025
        )
        dados = buscar_alunos_autocomplete("100001", 0)
        self.assertEqual(
            {d["matricula"]["aluno_id"] for d in dados},
            {1234567, 7654321},
        )

    def test_vinculos_duplicados_nao_consumem_limite(self) -> None:
        """Aplica o limite após deduplicar o par aluno e turma."""
        mt = MatriculaTurma.objects.get(codigo_matricula=998877)
        mt.pk = None
        mt.sequencia = 2
        mt.save()
        dados = buscar_alunos_autocomplete("100001", 2026, limite=2)
        self.assertEqual(len(dados), 2)
        self.assertEqual(
            {d["matricula"]["aluno_id"] for d in dados},
            {1234567, 7654321},
        )

    def test_turma_programa_habilita_turma_regular_do_aluno(self) -> None:
        """Preserva o vínculo em programa como alternativa no filtro."""
        mt = MatriculaTurma.objects.get(codigo_matricula=998877)
        mt.pk = None
        mt.codigo_turma = 99999
        mt.codigo_tipo_turma = 3
        mt.save()
        dados = buscar_alunos_autocomplete(
            "100001", 2026, codigo_turmas=[99999], limite=1
        )
        self.assertEqual(len(dados), 1)
        self.assertEqual(dados[0]["matricula_turma"]["codigo_turma"], 12345)

    def test_limite_zero_preserva_comportamento_atual(self) -> None:
        """Preserva a divergência conhecida para limite zero."""
        self.assertEqual(
            len(buscar_alunos_autocomplete("100001", 2026, limite=0)), 1
        )

    def test_ativos_carrega_nome_sem_consulta_extra_de_aluno(self) -> None:
        """Entrega nomes e turma sem a leitura extra de dados sensíveis."""
        with self.assertNumQueries(2), CaptureQueriesContext(connection) as qs:
            dados = buscar_alunos_ativos_autocomplete(
                "100001", aluno_nome="MARIA", limite=1
            )
        body = AlunoAutocompleteSerializer(dados, many=True).data
        self.assertEqual(body[0]["nome_social_aluno"], "MARIA SOCIAL")
        self.assertEqual(body[0]["turma"], "6A")
        self.assertEqual(body[0]["numero_aluno_chamada"], "07")
        for query in qs:
            self.assertNotIn('"cpf"', query["sql"])
            self.assertNotIn('"data_nascimento"', query["sql"])

    def test_ativos_preserva_data_de_referencia(self) -> None:
        """Inclui situação não ativa somente quando posterior à referência."""
        Matricula.objects.filter(pk=998877).update(
            codigo_situacao_matricula=14,
            data_situacao_matricula=date(2026, 8, 1),
        )
        for referencia, quantidade in [
            (date(2026, 7, 31), 1),
            (date(2026, 8, 1), 0),
            (None, 0),
        ]:
            with self.subTest(referencia=referencia):
                dados = buscar_alunos_ativos_autocomplete(
                    "100001", aluno_nome="JOAO", data_referencia=referencia
                )
                self.assertEqual(len(dados), quantidade)

    def test_ativos_nao_adiciona_filtro_de_ano(self) -> None:
        """Mantém vínculos elegíveis independentemente do ano letivo."""
        Matricula.objects.update(ano_letivo=2025)
        MatriculaTurma.objects.update(ano_letivo_turma=2025)
        self.assertEqual(
            len(
                buscar_alunos_ativos_autocomplete("100001", aluno_nome="JOAO")
            ),
            1,
        )
