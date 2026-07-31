"""Testes das funções de service do app alunos."""

from __future__ import annotations

from datetime import UTC, date, datetime
from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.alunos import services
from apps.alunos.models import (
    Matricula,
    MatriculaTurma,
    ResponsavelAluno,
)
from apps.alunos.tests.helpers import (
    DESCRICAO_ETAPA_ENSINO_FUNDAMENTAL,
    RESULTADO_ESPERADO_M04_DRE_108100,
    RESULTADO_ESPERADO_M04_DRE_108100_UMA_TURMA,
    seed_alunos,
    seed_matricula_duas_turmas_dre_108100,
    seed_matricula_uma_turma_dre_108100,
    seed_matriculas,
    seed_matriculas_ano_anterior,
    seed_matriculas_com_responsaveis,
    seed_necessidades,
    seed_responsaveis,
    seed_turma_data_aula,
)


class TurmasDoAlunoTestCase(TestCase):
    """Valida a busca de turmas do aluno."""

    def test_a01_retorna_lista(self) -> None:
        """Verifica os campos retornados para o aluno no ano corrente."""
        seed_matriculas_com_responsaveis()
        with patch(
            "django.utils.timezone.now",
            return_value=datetime(2026, 6, 1, tzinfo=UTC),
        ):
            dados = services.buscar_turmas_do_aluno(codigo_aluno=1234567)
        self.assertEqual(len(dados), 1)
        d = dados[0]
        self.assertEqual(d["matricula"]["aluno_id"], 1234567)
        self.assertEqual(d["matricula_turma"]["codigo_turma"], 12345)
        self.assertEqual(d["codigo_situacao"], 1)
        self.assertEqual(d["aluno"]["nome"], "JOAO DA SILVA")
        self.assertEqual(d["matricula_turma"]["numero_chamada"], "12")
        # DataAtualizacaoContato espelha o legado: vem do responsável
        # (data_atualizacao_tabela), não do aluno.
        self.assertEqual(
            d["responsavel"]["data_atualizacao_tabela"],
            datetime(2026, 1, 10, 3, 0, tzinfo=UTC),
        )

    def test_a01_aluno_inexistente_retorna_lista_vazia(self) -> None:
        """Verifica que aluno sem matrículas recebe lista vazia."""
        with patch(
            "django.utils.timezone.now",
            return_value=datetime(2026, 6, 1, tzinfo=UTC),
        ):
            dados = services.buscar_turmas_do_aluno(codigo_aluno=9999999)
        self.assertEqual(dados, [])

    def test_a03_calcula_historico_por_ano(self) -> None:
        """Verifica que ano diferente do corrente é tratado como histórico."""
        seed_matriculas(origem_atual=False)
        with patch(
            "django.utils.timezone.now",
            return_value=datetime(2027, 6, 1, tzinfo=UTC),
        ):
            dados = services.buscar_turmas_do_aluno_por_situacao_matricula(
                codigo_aluno=1234567,
                ano_letivo=2026,
                filtrar_situacao_matricula=True,
            )
        self.assertEqual(len(dados), 1)

    def test_a03_retorna_turmas_ativas_da_mesma_matricula(self) -> None:
        """Verifica que vínculos ativos distintos não são sobrescritos."""
        seed_alunos()
        Matricula.objects.create(
            codigo_matricula=998879,
            aluno_id=1234567,
            codigo_ue="100001",
            ano_letivo=2026,
            codigo_situacao_matricula=1,
            situacao_matricula="Ativo",
            data_situacao_matricula=date(2026, 2, 1),
        )
        MatriculaTurma.objects.create(
            codigo_matricula=998879,
            codigo_turma=12345,
            numero_chamada="24",
            data_situacao_aluno=date(2026, 2, 25),
            data_situacao_aluno_data_hora=datetime(
                2026, 2, 25, 23, 35, 24, tzinfo=UTC
            ),
            codigo_situacao_aluno=1,
            codigo_tipo_turma=2,
            sequencia=1,
            origem_atual=True,
        )
        MatriculaTurma.objects.create(
            codigo_matricula=998879,
            codigo_turma=23456,
            numero_chamada="09",
            data_situacao_aluno=date(2026, 2, 3),
            data_situacao_aluno_data_hora=datetime(
                2026, 2, 3, 14, 24, 34, tzinfo=UTC
            ),
            codigo_situacao_aluno=1,
            codigo_tipo_turma=1,
            sequencia=1,
            origem_atual=True,
        )
        MatriculaTurma.objects.create(
            codigo_matricula=998879,
            codigo_turma=34567,
            numero_chamada="12",
            data_situacao_aluno=date(2026, 2, 3),
            data_situacao_aluno_data_hora=datetime(
                2026, 2, 3, 14, 24, 35, tzinfo=UTC
            ),
            codigo_situacao_aluno=14,
            codigo_tipo_turma=1,
            sequencia=1,
            origem_atual=True,
        )
        MatriculaTurma.objects.create(
            codigo_matricula=998879,
            codigo_turma=34567,
            numero_chamada="12",
            data_situacao_aluno=date(2025, 11, 3),
            data_situacao_aluno_data_hora=datetime(
                2025, 11, 3, 13, 3, 55, tzinfo=UTC
            ),
            codigo_situacao_aluno=1,
            codigo_tipo_turma=1,
            sequencia=2,
            origem_atual=True,
        )
        MatriculaTurma.objects.create(
            codigo_matricula=998879,
            codigo_turma=45678,
            numero_chamada="01",
            data_situacao_aluno=date(2026, 2, 3),
            codigo_situacao_aluno=1,
            codigo_tipo_turma=3,
            sequencia=1,
            origem_atual=True,
        )

        with patch(
            "django.utils.timezone.now",
            return_value=datetime(2026, 6, 1, tzinfo=UTC),
        ):
            dados = services.buscar_turmas_do_aluno_por_situacao_matricula(
                codigo_aluno=1234567,
                ano_letivo=2026,
                filtrar_situacao_matricula=True,
                tipo_turma=True,
            )

        self.assertEqual(
            [d["matricula_turma"]["codigo_turma"] for d in dados],
            [12345, 23456],
        )
        self.assertEqual([d["codigo_situacao"] for d in dados], [1, 1])


class A04AlunosDaUeTestCase(TestCase):
    """Valida a busca de alunos por UE/ano letivo."""

    def _buscar_aluno_joao(self) -> list[dict[str, object]]:
        """Busca aluno João (1234567) na UE 100001 em 2026."""
        return services.buscar_alunos_da_ue(
            codigo_ue="100001",
            ano_letivo=2026,
            codigo_eol="1234567",
        )

    def test_filtra_por_codigo_eol(self) -> None:
        """Verifica filtro por substring do código EOL."""
        seed_matriculas()
        dados = services.buscar_alunos_da_ue(
            codigo_ue="100001",
            ano_letivo=2026,
            codigo_eol="234",
        )
        self.assertEqual(len(dados), 1)
        self.assertEqual(dados[0]["matricula"]["aluno_id"], 1234567)

    def test_filtra_por_nome(self) -> None:
        """Verifica filtro por substring do nome."""
        seed_matriculas()
        dados = services.buscar_alunos_da_ue(
            codigo_ue="100001",
            ano_letivo=2026,
            nome_aluno="JOAO",
        )
        self.assertTrue(all("JOAO" in d["aluno"]["nome"] for d in dados))

    def test_retorna_campos_do_contrato_da_listagem(self) -> None:
        """Verifica os campos complementares da listagem da UE."""
        seed_matriculas()
        dados = self._buscar_aluno_joao()

        self.assertEqual(len(dados), 1)
        aluno = dados[0]
        turma = aluno["matricula_turma"]
        self.assertEqual(turma["tipo_turno"], 2)
        self.assertEqual(turma["nome_turma"], "5A")
        self.assertEqual(turma["codigo_etapa_ensino"], 5)
        self.assertEqual(turma["codigo_ciclo_ensino"], 2)
        self.assertEqual(turma["descricao_etapa_ensino"], "Ensino Fundamental")
        self.assertEqual(
            turma["descricao_ciclo_ensino"], "Ciclo Interdisciplinar"
        )
        self.assertEqual(turma["numero_chamada"], "12")
        self.assertEqual(turma["codigo_situacao_aluno"], 1)

    def test_nao_filtra_situacao_da_matricula(self) -> None:
        """Verifica que a situação considerada vem da matrícula-turma."""
        seed_alunos()
        Matricula.objects.create(
            codigo_matricula=998900,
            aluno_id=1234567,
            codigo_ue="100001",
            ano_letivo=2026,
            codigo_situacao_matricula=2,
            situacao_matricula="Desistente",
            data_situacao_matricula=date(2026, 2, 1),
            origem_atual=True,
        )
        MatriculaTurma.objects.create(
            codigo_matricula=998900,
            codigo_turma=33333,
            numero_chamada=None,
            data_situacao_aluno=date(2026, 3, 1),
            codigo_situacao_aluno=14,
            codigo_tipo_turma=1,
            tipo_turno=2,
            nome_turma="7A",
            codigo_ue_turma="100001",
            codigo_etapa_ensino=5,
            codigo_ciclo_ensino=2,
            descricao_etapa_ensino="Ensino Fundamental",
            descricao_ciclo_ensino="Ciclo Interdisciplinar",
            sequencia=1,
            origem_atual=True,
            ano_letivo_turma=2026,
        )

        dados = services.buscar_alunos_da_ue(
            codigo_ue="100001",
            ano_letivo=2026,
            codigo_eol="1234567",
        )

        self.assertEqual(len(dados), 1)
        self.assertEqual(
            dados[0]["matricula_turma"]["codigo_situacao_aluno"], 14
        )
        self.assertIsNone(dados[0]["matricula_turma"]["numero_chamada"])

    def test_filtra_pela_ue_da_turma(self) -> None:
        """Verifica que a UE considerada vem da turma."""
        seed_alunos()
        Matricula.objects.create(
            codigo_matricula=998901,
            aluno_id=1234567,
            codigo_ue="999999",
            ano_letivo=2026,
            codigo_situacao_matricula=1,
            situacao_matricula="Ativo",
            data_situacao_matricula=date(2026, 2, 1),
            origem_atual=True,
        )
        MatriculaTurma.objects.create(
            codigo_matricula=998901,
            codigo_turma=44444,
            numero_chamada="09",
            data_situacao_aluno=date(2026, 2, 1),
            codigo_situacao_aluno=1,
            codigo_tipo_turma=1,
            tipo_turno=2,
            nome_turma="8A",
            codigo_ue_turma="100001",
            codigo_etapa_ensino=5,
            codigo_ciclo_ensino=2,
            descricao_etapa_ensino="Ensino Fundamental",
            descricao_ciclo_ensino="Ciclo Interdisciplinar",
            sequencia=1,
            origem_atual=True,
            ano_letivo_turma=2026,
        )

        dados = self._buscar_aluno_joao()

        self.assertEqual(len(dados), 1)
        self.assertEqual(dados[0]["matricula_turma"]["codigo_turma"], 44444)

    def test_retorna_um_item_por_vinculo_de_turma(self) -> None:
        """Verifica que vínculos distintos da turma não são deduplicados."""
        seed_matriculas()
        MatriculaTurma.objects.create(
            codigo_matricula=998877,
            codigo_turma=33333,
            numero_chamada="15",
            data_situacao_aluno=date(2026, 4, 1),
            codigo_situacao_aluno=1,
            codigo_tipo_turma=1,
            tipo_turno=4,
            nome_turma="5B",
            codigo_ue_turma="100001",
            codigo_etapa_ensino=5,
            codigo_ciclo_ensino=2,
            descricao_etapa_ensino="Ensino Fundamental",
            descricao_ciclo_ensino="Ciclo Interdisciplinar",
            sequencia=1,
            origem_atual=True,
            ano_letivo_turma=2026,
        )

        dados = self._buscar_aluno_joao()

        self.assertEqual(len(dados), 2)
        self.assertEqual(
            {d["matricula_turma"]["codigo_turma"] for d in dados},
            {12345, 33333},
        )


class A05A06AutocompleteTestCase(TestCase):
    """Valida o autocomplete de alunos por UE/ano e por ativos."""

    def test_a05_filtra_por_nome(self) -> None:
        """Verifica filtro do autocomplete pelo nome do aluno."""
        seed_matriculas()
        dados = services.buscar_alunos_autocomplete(
            codigo_ue="100001",
            ano_letivo=2026,
            nome_aluno="MARIA",
            limite=10,
        )
        self.assertEqual(len(dados), 1)
        self.assertEqual(dados[0]["matricula"]["aluno_id"], 7654321)

    def test_a06_alunos_ativos(self) -> None:
        """Verifica o autocomplete restrito a alunos ativos."""
        seed_matriculas()
        dados = services.buscar_alunos_ativos_autocomplete(
            ue_codigo="100001",
            aluno_nome="JOAO",
            limite=10,
        )
        self.assertEqual(len(dados), 1)

    def test_a06_alunos_ativos_ignora_turma_programa(self) -> None:
        """Verifica que turmas tipo programa nao entram no autocomplete."""
        seed_matriculas()
        Matricula.objects.create(
            codigo_matricula=998879,
            aluno_id=1234567,
            codigo_ue="100001",
            ano_letivo=2026,
            codigo_situacao_matricula=1,
            situacao_matricula="Ativo",
            data_situacao_matricula=date(2026, 3, 1),
            origem_atual=True,
        )
        MatriculaTurma.objects.create(
            codigo_matricula=998879,
            codigo_turma=33333,
            numero_chamada="01",
            data_situacao_aluno=date(2026, 3, 1),
            codigo_situacao_aluno=1,
            codigo_tipo_turma=3,
            sequencia=1,
        )

        dados = services.buscar_alunos_ativos_autocomplete(
            ue_codigo="100001",
            aluno_nome="JOAO",
            data_referencia=datetime(2026, 6, 3, tzinfo=UTC),
            limite=10,
        )

        self.assertEqual(len(dados), 1)
        self.assertEqual(dados[0]["matricula_turma"]["codigo_turma"], 12345)

    def test_a06_turma_e_modalidade_vem_da_matricula_turma(self) -> None:
        """Verifica turma/modalidade da matrícula-turma sem acompanhamento.

        Espelha o legado: aluno ativo aparece mesmo sem registro na tabela
        de acompanhamento escolar, com turma e modalidade derivadas da
        própria matrícula-turma.
        """
        seed_alunos()
        Matricula.objects.create(
            codigo_matricula=998900,
            aluno_id=1234567,
            codigo_ue="100001",
            ano_letivo=2026,
            codigo_situacao_matricula=1,
            situacao_matricula="Ativo",
            data_situacao_matricula=date(2026, 2, 1),
            origem_atual=True,
        )
        MatriculaTurma.objects.create(
            codigo_matricula=998900,
            codigo_turma=44444,
            numero_chamada="09",
            data_situacao_aluno=date(2026, 2, 1),
            codigo_situacao_aluno=1,
            codigo_tipo_turma=1,
            nome_turma="9B",
            codigo_etapa_ensino=6,
            sequencia=1,
        )

        dados = services.buscar_alunos_ativos_autocomplete(
            ue_codigo="100001",
            aluno_nome="JOAO",
            limite=10,
        )

        self.assertEqual(len(dados), 1)
        self.assertEqual(dados[0]["matricula_turma"]["codigo_turma"], 44444)
        self.assertEqual(dados[0]["matricula_turma"]["nome_turma"], "9B")
        self.assertEqual(dados[0]["matricula_turma"]["codigo_etapa_ensino"], 6)


class A07TotalAtivosTestCase(TestCase):
    """Valida a contagem de alunos ativos por período."""

    def test_filtra_por_periodo_e_ue(self) -> None:
        """Verifica a contagem restrita a UE, série e modalidade."""
        seed_matriculas()
        total = services.obter_total_alunos_ativos_periodo(
            ano_turma="5",
            ano_letivo=2026,
            data_inicio=date(2026, 1, 1),
            data_fim=date(2026, 12, 31),
            ue_id="100001",
            modalidades=[5],
        )
        self.assertEqual(total["quantidade"], 2)

    def test_serie_diferente_nao_conta(self) -> None:
        """Verifica que série diferente da turma não é contabilizada."""
        seed_matriculas()
        total = services.obter_total_alunos_ativos_periodo(
            ano_turma="9",
            ano_letivo=2026,
            data_inicio=date(2026, 1, 1),
            data_fim=date(2026, 12, 31),
            modalidades=[5],
        )
        self.assertEqual(total["quantidade"], 0)

    def test_modalidade_diferente_nao_conta(self) -> None:
        """Verifica que modalidade fora da lista não é contabilizada."""
        seed_matriculas()
        total = services.obter_total_alunos_ativos_periodo(
            ano_turma="5",
            ano_letivo=2026,
            data_inicio=date(2026, 1, 1),
            data_fim=date(2026, 12, 31),
            modalidades=[6],
        )
        self.assertEqual(total["quantidade"], 0)


class A08A09AlunosTurmaTestCase(TestCase):
    """Valida a listagem de alunos ativos por turma."""

    def test_a09_retorna_alunos_da_turma(self) -> None:
        """Verifica os alunos retornados para a turma informada."""
        seed_matriculas_com_responsaveis()
        seed_necessidades()
        dados = services.obter_alunos_ativos_por_turma(codigo_turma=12345)
        self.assertEqual(len(dados), 1)
        self.assertEqual(dados[0]["linha"]["aluno_id"], 1234567)

    def test_a08_filtra_por_data(self) -> None:
        """Verifica o filtro por data de referência na turma."""
        seed_matriculas()
        dados = services.obter_alunos_ativos_por_periodo_e_turma(
            codigo_turma=12345,
            data_referencia_fim=date(2026, 12, 31),
        )
        self.assertEqual(len(dados), 1)


class A10NecessidadesTestCase(TestCase):
    """Valida a listagem de necessidades especiais do aluno."""

    def test_lista_necessidades_do_aluno(self) -> None:
        """Verifica as necessidades retornadas para o aluno informado."""
        seed_alunos()
        seed_necessidades(codigo_aluno=1234567)
        dados = services.obter_necessidades_especiais_por_aluno(
            codigo_aluno=1234567
        )
        self.assertEqual(len(dados), 1)
        self.assertEqual(
            dados[0]["descricao_necessidade_especial"], "Deficiência Visual"
        )


class A11A12CodigosTestCase(TestCase):
    """Valida a consulta de turmas para listas de códigos de aluno."""

    def test_a11_filtra_por_ano(self) -> None:
        """Verifica a consulta por códigos restrita ao ano letivo."""
        seed_matriculas()
        with patch(
            "django.utils.timezone.now",
            return_value=datetime(2026, 6, 1, tzinfo=UTC),
        ):
            dados = services.obter_alunos_por_codigos_e_ano(
                codigos_aluno=[1234567, 7654321], ano_letivo=2026
            )
        self.assertEqual(len(dados), 2)


class A13A14InformacoesTestCase(TestCase):
    """Valida as consultas de informações do aluno e dos alunos da turma."""

    def test_a13_retorna_aluno(self) -> None:
        """Verifica os campos retornados para um aluno existente."""
        seed_alunos()
        info = services.obter_informacoes_aluno(codigo_aluno=1234567)
        self.assertIsNotNone(info)
        assert info is not None
        self.assertEqual(info["aluno"].nome, "JOAO DA SILVA")
        self.assertEqual(info["aluno"].nis, "123456789")

    def test_a13_inexistente(self) -> None:
        """Verifica que aluno inexistente retorna None."""
        info = services.obter_informacoes_aluno(codigo_aluno=999)
        self.assertIsNone(info)

    def test_a14_lista_alunos_da_turma(self) -> None:
        """Verifica os alunos retornados para a turma informada."""
        seed_matriculas()
        dados = services.obter_informacoes_alunos_da_turma(codigo_turma=12345)
        self.assertEqual(len(dados), 1)
        self.assertEqual(dados[0]["row"]["aluno_id"], 1234567)


class A15A16QuantidadeTestCase(TestCase):
    """Valida as agregações de quantidade de matriculados."""

    def test_a15_agrupa_por_turma(self) -> None:
        """Verifica o agrupamento de matrículas por turma no ano letivo."""
        seed_matriculas()
        dados = services.obter_quantidade_matriculados_por_ano_e_cc(
            ano_letivo=2026
        )
        self.assertEqual(len(dados), 2)

    def test_a16_agrega_por_ue_turma(self) -> None:
        """Verifica o agrupamento de matrículas por UE e turma."""
        seed_matriculas()
        dados = services.obter_quantidade_matriculados(
            ano_letivo=2026, ue_codigo="100001"
        )
        self.assertEqual(len(dados), 2)
        for d in dados:
            self.assertEqual(d["ue_codigo"], "100001")


class A18AcompanhamentoTestCase(TestCase):
    """Valida a consulta de dados de acompanhamento escolar."""

    def test_filtra_por_turma(self) -> None:
        """Verifica o filtro por código de turma e responsável vigente."""
        seed_matriculas_com_responsaveis()
        dados = services.obter_dados_acompanhamento_escolar(
            codigo_ue="100001",
            ano_letivo=2026,
            turma_codigo="12345",
        )
        self.assertEqual(len(dados), 1)
        self.assertEqual(dados[0]["codigo_eol"], 1234567)
        self.assertEqual(dados[0]["nome_responsavel"], "Responsavel Exemplo")


class A19A20A21ResponsaveisTestCase(TestCase):
    """Valida as consultas de responsáveis (lista, completo e resumido)."""

    def test_a19_lista_responsaveis_da_ue(self) -> None:
        """Verifica a listagem de responsáveis vigentes por UE/ano."""
        seed_matriculas_com_responsaveis()
        dados = services.obter_responsaveis_dre_ue_turma(
            codigo_ue="100001", ano_letivo=2026
        )
        self.assertEqual(len(dados), 1)
        self.assertEqual(dados[0]["codigo_aluno"], 1234567)
        self.assertEqual(dados[0]["cpf_responsavel"], 12345678901)
        self.assertFalse(dados[0]["tem_app_instalado"])

    def test_a20_dados_completos(self) -> None:
        """Verifica o retorno completo dos dados do responsável."""
        seed_alunos()
        seed_responsaveis()
        dados = services.obter_dados_responsavel(cpf_responsavel="12345678901")
        self.assertEqual(len(dados), 1)
        self.assertEqual(
            dados[0]["responsavel"]["nome"], "Responsavel Exemplo"
        )

    def test_contrato_retorna_campos_legados_do_vinculo_e_aluno(self) -> None:
        """Verifica o contrato completo para vínculo elegível."""
        seed_matriculas_com_responsaveis()

        with patch(
            "apps.alunos.services.responsaveis.timezone.now",
            return_value=datetime(2026, 6, 1, tzinfo=UTC),
        ):
            dados = services.obter_dados_responsavel_contrato(
                cpf_responsavel="12345678901"
            )

        self.assertEqual(len(dados), 1)
        self.assertEqual(dados[0]["id"], 5501)
        self.assertEqual(dados[0]["codigo_aluno"], "1234567")
        self.assertEqual(dados[0]["tipo_sigilo"], 0)
        self.assertEqual(dados[0]["digito_rg"], "4   ")
        self.assertEqual(dados[0]["ddd_telefone_fixo"], "11")

    def test_contrato_exclui_vinculo_encerrado(self) -> None:
        """Verifica que vínculos encerrados não são retornados."""
        seed_matriculas()
        responsavel = seed_responsaveis()
        responsavel.data_fim_vinculo = date(2026, 1, 1)
        responsavel.save(update_fields=["data_fim_vinculo"])

        with patch(
            "apps.alunos.services.responsaveis.timezone.now",
            return_value=datetime(2026, 6, 1, tzinfo=UTC),
        ):
            dados = services.obter_dados_responsavel_contrato(
                cpf_responsavel="12345678901"
            )

        self.assertEqual(dados, [])

    def test_contrato_aceita_escola_especial_sem_serie(self) -> None:
        """Verifica a exceção para escolas dos tipos 22 e 23."""
        seed_matriculas_com_responsaveis()
        Matricula.objects.filter(codigo_matricula=998877).update(
            codigo_serie_ensino=None,
            codigo_tipo_escola=22,
        )

        with patch(
            "apps.alunos.services.responsaveis.timezone.now",
            return_value=datetime(2026, 6, 1, tzinfo=UTC),
        ):
            escola_especial = services.obter_dados_responsavel_contrato(
                cpf_responsavel="12345678901"
            )
            Matricula.objects.filter(codigo_matricula=998877).update(
                codigo_tipo_escola=1
            )
            sem_serie = services.obter_dados_responsavel_contrato(
                cpf_responsavel="12345678901"
            )

        self.assertEqual(len(escola_especial), 1)
        self.assertEqual(sem_serie, [])

    def test_contrato_preserva_uma_linha_por_matricula_turma(self) -> None:
        """Verifica a multiplicidade produzida pelos joins do legado."""
        seed_matriculas_com_responsaveis()
        MatriculaTurma.objects.create(
            codigo_matricula=998877,
            codigo_turma=54321,
            codigo_situacao_aluno=6,
            codigo_tipo_turma=1,
            sequencia=2,
            origem_atual=True,
            ano_letivo_turma=2026,
        )

        with patch(
            "apps.alunos.services.responsaveis.timezone.now",
            return_value=datetime(2026, 6, 1, tzinfo=UTC),
        ):
            dados = services.obter_dados_responsavel_contrato(
                cpf_responsavel="12345678901"
            )

        self.assertEqual(len(dados), 2)
        self.assertEqual({dado["id"] for dado in dados}, {5501})

    def test_a21_resumido(self) -> None:
        """Verifica o retorno resumido dos dados do responsável."""
        seed_alunos()
        seed_responsaveis()
        dado = services.obter_dados_responsavel_resumido(
            cpf_responsavel="12345678901"
        )
        self.assertIsNotNone(dado)
        assert dado is not None
        self.assertEqual(dado["responsavel"]["cpf"], "12345678901")
        self.assertEqual(
            dado["responsavel"]["data_nascimento"], date(1980, 5, 20)
        )
        self.assertEqual(dado["responsavel"]["nome_mae"], "Mae do Responsavel")

    def test_a21_resumido_ignora_vinculo_encerrado_mais_recente(
        self,
    ) -> None:
        """Verifica que o resumido segue o filtro legado de vínculo ativo."""
        seed_alunos()
        seed_responsaveis()
        ResponsavelAluno.objects.create(
            codigo_responsavel=5502,
            aluno_id=7654321,
            tipo_responsavel=1,
            nome="Responsavel Exemplo",
            cpf="12345678901",
            email="contato.exemplo@sme.com.br",
            data_atualizacao_tabela=datetime(2026, 2, 10, tzinfo=UTC),
            data_fim_vinculo=date(2026, 2, 10),
        )

        dado = services.obter_dados_responsavel_resumido(
            cpf_responsavel="12345678901"
        )

        self.assertIsNotNone(dado)
        assert dado is not None
        self.assertEqual(dado["responsavel"]["codigo_responsavel"], 5501)


class A22A23EscritaTestCase(TestCase):
    """Valida as escritas de responsável (busca ativa e cadastro)."""

    def test_a22_atualiza_telefones(self) -> None:
        """Verifica a atualização de telefones pelo fluxo de busca ativa."""
        seed_alunos()
        seed_responsaveis()
        atualizado = services.atualizar_dados_responsavel_busca_ativa(
            codigo_aluno=1234567,
            cpf_responsavel="12345678901",
            ddd_celular="11",
            numero_celular="999998888",
            ddd_residencial="11",
            numero_residencial="33330000",
            ddd_comercial="11",
            numero_comercial="44440000",
        )
        responsavel = ResponsavelAluno.objects.get(codigo_responsavel=5501)
        self.assertTrue(atualizado)
        self.assertEqual(responsavel.numero_celular, "999998888")
        self.assertEqual(responsavel.nr_telefone_fixo, "33330000")
        self.assertEqual(responsavel.nr_telefone_comercial, "44440000")

    def test_a23_atualiza_responsavel_com_campos_fixos(self) -> None:
        """Verifica a atualização cadastral e os indicadores fixos."""
        seed_alunos()
        seed_responsaveis()
        atualizado = services.atualizar_dados_responsavel(
            codigo_aluno=1234567,
            cpf_responsavel="12345678901",
            email="atualizado@sme.com.br",
            data_nascimento=datetime(1981, 6, 21, tzinfo=UTC),
            nome_mae="Mae Atualizada",
            ddd_celular="11",
            numero_celular="911112222",
        )
        responsavel = ResponsavelAluno.objects.get(codigo_responsavel=5501)
        self.assertTrue(atualizado)
        self.assertEqual(responsavel.email, "atualizado@sme.com.br")
        self.assertEqual(responsavel.data_nascimento, date(1981, 6, 21))
        self.assertEqual(responsavel.nome_mae, "Mae Atualizada")
        self.assertEqual(responsavel.cpf_confere, "S")
        self.assertEqual(responsavel.autoriza_sms, "S")
        self.assertEqual(responsavel.tipo_turno_celular, 1)

    def test_escritas_retornam_falso_para_vinculo_inexistente(self) -> None:
        """Verifica o retorno falso sem criar um novo vínculo."""
        seed_alunos()

        post = services.atualizar_dados_responsavel(
            codigo_aluno=1234567,
            cpf_responsavel="00000000000",
        )
        put = services.atualizar_dados_responsavel_busca_ativa(
            codigo_aluno=1234567,
            cpf_responsavel="00000000000",
        )

        self.assertFalse(post)
        self.assertFalse(put)
        self.assertFalse(
            ResponsavelAluno.objects.filter(cpf="00000000000").exists()
        )


class ObterNomesAlunosServiceTestCase(TestCase):
    """Valida nomes e vínculos de matrícula-turma."""

    def test_retorna_uma_linha_por_turma_sem_filtrar_situacao(self) -> None:
        """Verifica que situações ativas e inativas são retornadas."""
        seed_matriculas()
        Matricula.objects.filter(codigo_matricula=998877).update(
            data_situacao_matricula_data_hora=datetime(
                2025, 11, 4, 19, 48, 56, 123000, tzinfo=UTC
            )
        )
        MatriculaTurma.objects.create(
            codigo_matricula=998877,
            codigo_turma=54321,
            codigo_situacao_aluno=14,
            codigo_tipo_turma=1,
            sequencia=2,
            origem_atual=True,
            ano_letivo_turma=2026,
        )

        dados = services.obter_nomes_alunos(
            codigos_alunos=[1234567],
            ano_letivo=2026,
        )

        self.assertEqual(len(dados), 2)
        self.assertEqual(
            {dado["codigo_situacao_matricula"] for dado in dados},
            {1, 14},
        )
        self.assertEqual(dados[1]["situacao_matricula"], "Remanejado Saída")
        self.assertEqual(dados[0]["codigo_escola"], "100001")

    def test_lista_vazia_retorna_vazia(self) -> None:
        """Verifica a ausência de resultados sem códigos."""
        self.assertEqual(services.obter_nomes_alunos([]), [])


class A27FiliacaoTestCase(TestCase):
    """Valida os dados de filiação do aluno."""

    def test_retorna_responsaveis_com_endereco(self) -> None:
        """Verifica os dados de filiação e endereço retornados."""
        seed_alunos()
        seed_responsaveis()

        dados = services.obter_dados_responsavel_filiacao(codigo_aluno=1234567)

        self.assertEqual(len(dados), 1)
        responsavel = dados[0]
        self.assertEqual(
            responsavel["responsavel"]["nome"], "Responsavel Exemplo"
        )
        self.assertEqual(responsavel["responsavel"]["ddd_telefone_fixo"], "11")
        self.assertEqual(
            responsavel["responsavel"]["nr_telefone_comercial"], "55556666"
        )
        self.assertEqual(responsavel["responsavel"]["endereco_id"], 123)
        self.assertEqual(responsavel["responsavel"]["numero_endereco"], "100")

    def test_retorna_lista_vazia_sem_responsaveis_de_filiacao(self) -> None:
        """Verifica que aluno sem filiação retorna lista vazia."""
        seed_alunos()

        dados = services.obter_dados_responsavel_filiacao(codigo_aluno=1234567)

        self.assertEqual(dados, [])


class A12AlunosPorCodigosTestCase(TestCase):
    """Valida cenários de entrada da consulta por códigos de aluno."""

    def test_lista_vazia_retorna_vazia(self) -> None:
        """Verifica que lista vazia gera saída vazia."""
        dados = services.obter_alunos_por_codigos(codigos_aluno=[])
        self.assertEqual(dados, [])

    def test_codigo_invalido_busca_ue_retorna_vazio(self) -> None:
        """Verifica que código EOL não numérico gera saída vazia."""
        dados = services.buscar_alunos_da_ue(
            codigo_ue="100001", ano_letivo=2026, codigo_eol="nao-e-numero"
        )
        self.assertEqual(dados, [])

    def test_ue_sem_matriculas_retorna_vazio(self) -> None:
        """Verifica que UE sem matrículas gera saída vazia."""
        dados = services.buscar_alunos_da_ue(
            codigo_ue="999999", ano_letivo=2026
        )
        self.assertEqual(dados, [])

    def test_nome_sem_match_retorna_vazio(self) -> None:
        """Verifica que filtro de nome sem match gera saída vazia."""
        seed_matriculas()
        dados = services.buscar_alunos_da_ue(
            codigo_ue="100001", ano_letivo=2026, nome_aluno="XXXXXXXXXX"
        )
        self.assertEqual(dados, [])


class M01M02E05ConsolidacaoTestCase(TestCase):
    """Valida a consolidação de matrículas por turma."""

    def test_m01(self) -> None:
        """Verifica a consolidação do ano atual por UE."""
        seed_matriculas()
        dados = services.obter_matriculas_ano_atual(
            ano_letivo=2026, ue_codigo="100001"
        )
        self.assertEqual(len(dados), 2)

    def test_m02_anos_anteriores(self) -> None:
        """Verifica a leitura da consolidação histórica materializada."""
        seed_matriculas_ano_anterior()
        dados = services.obter_matriculas_anos_anteriores(
            ano_letivo=2025, ue_codigo="100001"
        )
        self.assertEqual(len(dados), 1)
        self.assertEqual(str(dados[0]["codigo_turma"]), "54321")
        self.assertEqual(dados[0]["quantidade"], 27)

    def test_e05(self) -> None:
        """Verifica a consolidação por turma da escola informada."""
        seed_matriculas()
        dados = services.obter_quantidade_alunos_por_turma_da_escola(
            codigo_escola="100001"
        )
        self.assertEqual(len(dados), 2)


class M03M04AgregacoesTestCase(TestCase):
    """Valida agregações por turno de M03 e M04."""

    def test_m03_retorna_agregado_por_turno(self) -> None:
        """Verifica que M03 retorna objeto agregado por turno."""
        seed_matriculas()
        self.assertEqual(
            services.obter_total_matriculas_por_turno_ue(ue_codigo="100001"),
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

    def test_m04_retorna_agregado_por_escola(self) -> None:
        """Verifica que M04 retorna lista agregada por escola."""
        seed_matricula_uma_turma_dre_108100()
        dados = services.obter_total_matriculas_por_turno_dre(dre_codigo="108100")
        self.assertEqual(dados, RESULTADO_ESPERADO_M04_DRE_108100_UMA_TURMA)

    def test_m04_usa_escola_da_ultima_alocacao_da_turma(self) -> None:
        """Verifica que M04 agrega pela UE da última alocação da turma."""
        seed_matricula_duas_turmas_dre_108100()
        dados = services.obter_total_matriculas_por_turno_dre(dre_codigo="108100")
        self.assertEqual(dados, RESULTADO_ESPERADO_M04_DRE_108100)


class E24MatriculasAlunoEscolaTestCase(TestCase):
    """Valida a consulta de matrículas do aluno em uma escola."""

    def test_retorna_matriculas_do_aluno(self) -> None:
        """Verifica as matrículas retornadas para aluno/escola existentes."""
        seed_matriculas()
        dados = services.obter_matriculas_aluno_na_escola(
            codigo_escola="100001", codigo_aluno=1234567
        )
        self.assertEqual(len(dados), 1)
        self.assertEqual(dados[0]["matricula"]["codigo_matricula"], 998877)
        self.assertEqual(dados[0]["matricula"]["ano_letivo"], 2026)

    def test_aluno_inexistente_retorna_vazio(self) -> None:
        """Verifica que aluno sem matrículas na escola gera saída vazia."""
        dados = services.obter_matriculas_aluno_na_escola(
            codigo_escola="100001", codigo_aluno=9999999
        )
        self.assertEqual(dados, [])

    def test_data_situacao_matricula_sem_hora(self) -> None:
        """Verifica matrícula com data_situacao sem hora (apenas date)."""
        from apps.alunos.tests.helpers import criar_matricula_simples

        seed_alunos()
        criar_matricula_simples(
            codigo_matricula=888001,
            aluno_id=1234567,
            codigo_ue="100002",
            data_situacao_matricula_data_hora=None,
        )

        dados = services.obter_matriculas_aluno_na_escola(
            codigo_escola="100002", codigo_aluno=1234567
        )
        self.assertEqual(len(dados), 1)
        self.assertEqual(dados[0]["matricula"]["codigo_matricula"], 888001)
        self.assertIsNotNone(dados[0]["matricula"]["data_situacao_matricula"])


class HelpersInternosTestCase(TestCase):
    """Testes para os helpers internos."""

    def test_alunos_indexados_vazio(self) -> None:
        """Verifica que entrada vazia em alunos_indexados gera dict vazio."""
        from apps.alunos.repositories import alunos_indexados

        self.assertEqual(alunos_indexados([]), {})

    def test_matricula_turma_por_matricula_vazio(self) -> None:
        """Verifica que entrada vazia em matrícula da turma gera dict vazio."""
        from apps.alunos.repositories import (
            matricula_turma_por_matricula,
        )

        self.assertEqual(matricula_turma_por_matricula([]), {})

    def test_matriculas_por_codigos_turma_vazio(self) -> None:
        """Verifica que entrada vazia por codigo_turma gera lista vazia."""
        from apps.alunos.repositories import matriculas_por_codigos_turma

        self.assertEqual(matriculas_por_codigos_turma([]), [])

    def test_matriculas_por_codigos_turma_sem_match(self) -> None:
        """Verifica que turmas inexistentes geram lista vazia."""
        from apps.alunos.repositories import matriculas_por_codigos_turma

        self.assertEqual(matriculas_por_codigos_turma([99999999]), [])

    def test_responsavel_principal_inexistente(self) -> None:
        """Verifica que aluno sem responsável retorna None."""
        from apps.alunos.services.responsaveis import responsavel_principal

        self.assertIsNone(responsavel_principal(99999999))


class AutocompleteCenariosServiceTestCase(TestCase):
    """Valida cenários de borda do autocomplete de alunos."""

    def test_codigo_eol_invalido_retorna_vazio(self) -> None:
        """Verifica que código EOL não numérico gera saída vazia."""
        dados = services.buscar_alunos_autocomplete(
            codigo_ue="100001",
            ano_letivo=2026,
            codigo_eol="abc",
            limite=10,
        )
        self.assertEqual(dados, [])

    def test_ue_sem_matricula_retorna_vazio(self) -> None:
        """Verifica que UE sem matrículas gera saída vazia."""
        dados = services.buscar_alunos_autocomplete(
            codigo_ue="999999",
            ano_letivo=2026,
            limite=10,
        )
        self.assertEqual(dados, [])

    def test_filtro_por_codigo_turma(self) -> None:
        """Verifica o filtro do autocomplete por código de turma."""
        seed_matriculas()
        dados = services.buscar_alunos_autocomplete(
            codigo_ue="100001",
            ano_letivo=2026,
            codigo_turmas=[12345],
            limite=10,
        )
        self.assertEqual(len(dados), 1)
        self.assertEqual(dados[0]["matricula_turma"]["codigo_turma"], 12345)

    def test_limite_um(self) -> None:
        """Verifica que limite=1 corta o resultado em um único item."""
        seed_matriculas()
        dados = services.buscar_alunos_autocomplete(
            codigo_ue="100001",
            ano_letivo=2026,
            limite=1,
        )
        self.assertEqual(len(dados), 1)


class BuscarTurmasDoAlunoFiltrosTestCase(TestCase):
    """Valida o repasse de filtros em buscar_turmas_do_aluno."""

    @patch("apps.alunos.services.turmas._consultar_turmas_do_aluno")
    def test_default_exclui_programa_e_filtra_situacao(
        self, mock_consultar: MagicMock
    ) -> None:
        """Verifica que os defaults preservam o comportamento padrão."""
        mock_consultar.return_value = []

        services.buscar_turmas_do_aluno(codigo_aluno=1234567)

        mock_consultar.assert_called_once_with(
            codigo_aluno=1234567, tipo_turma=True, filtrar_situacao=True
        )

    @patch("apps.alunos.services.turmas._consultar_turmas_do_aluno")
    def test_repassa_tipo_turma_e_filtrar_situacao(
        self, mock_consultar: MagicMock
    ) -> None:
        """Verifica que os filtros informados chegam à consulta."""
        mock_consultar.return_value = []

        services.buscar_turmas_do_aluno(
            codigo_aluno=1234567,
            tipo_turma=False,
            filtrar_situacao=False,
        )

        mock_consultar.assert_called_once_with(
            codigo_aluno=1234567, tipo_turma=False, filtrar_situacao=False
        )


class AlunosAtivosDataAulaTicksServiceTestCase(TestCase):
    """Valida a consulta de alunos ativos na turma por data de aula."""

    def _obter_alunos_turma_junho(
        self, codigo_turma: int
    ) -> list[dict[str, object]]:
        """Busca alunos da turma na data 2026-06-01."""
        return services.obter_alunos_turma(
            codigo_turma=codigo_turma,
            data_aula=datetime(2026, 6, 1, tzinfo=UTC),
        )

    def test_retorna_alunos_dedup_por_aluno(self) -> None:
        """Verifica dedup por aluno e campos enriquecidos do contrato."""
        codigo_turma = seed_turma_data_aula()
        dados = self._obter_alunos_turma_junho(codigo_turma)
        self.assertEqual(len(dados), 2)
        por_aluno = {d["linha"]["aluno_id"]: d for d in dados}
        joao = por_aluno[1234567]
        self.assertEqual(joao["aluno"]["nome"], "JOAO DA SILVA")
        self.assertEqual(joao["linha"]["codigo_turma"], codigo_turma)
        self.assertEqual(joao["linha"]["codigo_ue"], "100001")
        self.assertEqual(joao["linha"]["codigo_dre"], "108800")
        self.assertEqual(joao["linha"]["ano_letivo"], 2026)
        self.assertEqual(joao["linha"]["sequencia"], 1)
        self.assertEqual(joao["linha"]["numero_chamada"], "12")
        self.assertEqual(
            joao["linha"]["data_situacao_aluno_data_hora"],
            datetime(2026, 2, 10, 14, 0, tzinfo=UTC),
        )
        self.assertEqual(
            joao["primeira_alocacao"],
            datetime(2026, 2, 10, 14, 0, tzinfo=UTC),
        )
        self.assertEqual(joao["responsavel"]["nome"], "Responsavel Data Aula")
        self.assertEqual(joao["responsavel"]["tipo_responsavel"], 1)
        self.assertEqual(joao["responsavel"]["ddd_celular"], "11")
        self.assertEqual(joao["responsavel"]["numero_celular"], "988887777")
        self.assertEqual(
            joao["aluno"]["data_atualizacao_contato"],
            datetime(2026, 1, 15, 14, 46, 50, tzinfo=UTC),
        )

    def test_aluno_sem_responsavel_tem_campos_nulos(self) -> None:
        """Verifica que aluno sem responsável retorna campos nulos."""
        codigo_turma = seed_turma_data_aula()
        dados = self._obter_alunos_turma_junho(codigo_turma)
        maria = {d["linha"]["aluno_id"]: d for d in dados}[7654321]
        self.assertEqual(maria["responsavel"], {})
        self.assertIsNone(maria["aluno"]["data_atualizacao_contato"])

    def test_ignora_responsavel_com_vinculo_encerrado(self) -> None:
        """Verifica que responsável sem vínculo ativo é descartado."""
        codigo_turma = seed_turma_data_aula()
        ResponsavelAluno.objects.create(
            codigo_responsavel=6602,
            aluno_id=1234567,
            tipo_responsavel=2,
            nome="Responsavel Encerrado",
            ddd_celular="11",
            numero_celular="993786998",
            data_fim_vinculo=date(2026, 3, 1),
            data_atualizacao_tabela=datetime(2026, 5, 1, 11, 48, tzinfo=UTC),
        )

        dados = self._obter_alunos_turma_junho(codigo_turma)

        joao = {d["linha"]["aluno_id"]: d for d in dados}[1234567]
        self.assertEqual(joao["responsavel"]["nome"], "Responsavel Data Aula")
        self.assertEqual(joao["responsavel"]["ddd_celular"], "11")
        self.assertEqual(joao["responsavel"]["numero_celular"], "988887777")

    def test_data_matricula_e_a_da_alocacao_mais_antiga(self) -> None:
        """Verifica data_matricula vinda da alocação mais antiga."""
        codigo_turma = seed_turma_data_aula()
        MatriculaTurma.objects.create(
            codigo_matricula=700001,
            codigo_turma=codigo_turma,
            numero_chamada="12",
            data_situacao_aluno=date(2024, 11, 1),
            data_situacao_aluno_data_hora=datetime(
                2024, 11, 1, 13, 34, 37, tzinfo=UTC
            ),
            codigo_situacao_aluno=14,
            codigo_tipo_turma=1,
            sequencia=0,
        )

        dados = self._obter_alunos_turma_junho(codigo_turma)

        joao = {d["linha"]["aluno_id"]: d for d in dados}[1234567]
        self.assertEqual(
            joao["primeira_alocacao"],
            datetime(2024, 11, 1, 13, 34, 37, tzinfo=UTC),
        )

    def test_filtra_data_situacao_posterior_a_data_aula(self) -> None:
        """Verifica que matrícula posterior à data de aula é excluída."""
        codigo_turma = seed_turma_data_aula()
        dados = services.obter_alunos_turma(
            codigo_turma=codigo_turma,
            data_aula=datetime(2026, 1, 1, tzinfo=UTC),
        )
        self.assertEqual(dados, [])

    def test_inclui_matricula_no_mesmo_dia_apos_a_hora_da_aula(self) -> None:
        """Verifica o ajuste de fim do dia conforme legado."""
        codigo_turma = seed_turma_data_aula()
        Matricula.objects.create(
            codigo_matricula=700009,
            aluno_id=7654321,
            codigo_ue="100001",
            codigo_dre="108800",
            ano_letivo=2026,
            codigo_situacao_matricula=1,
            situacao_matricula="Ativo",
            data_situacao_matricula=date(2026, 2, 6),
            data_situacao_matricula_data_hora=datetime(
                2026, 2, 6, 15, 0, tzinfo=UTC
            ),
        )
        MatriculaTurma.objects.create(
            codigo_matricula=700009,
            codigo_turma=codigo_turma,
            numero_chamada="30",
            data_situacao_aluno=date(2026, 2, 6),
            data_situacao_aluno_data_hora=datetime(
                2026, 2, 6, 15, 0, tzinfo=UTC
            ),
            codigo_situacao_aluno=1,
            codigo_tipo_turma=1,
            sequencia=0,
        )

        dados = services.obter_alunos_turma(
            codigo_turma=codigo_turma,
            data_aula=datetime(2026, 2, 6, 8, 0, tzinfo=UTC),
        )

        maria = {d["linha"]["aluno_id"]: d for d in dados}[7654321]
        self.assertEqual(maria["linha"]["codigo_matricula"], 700009)

    def test_turma_inexistente_retorna_vazio(self) -> None:
        """Verifica que turma sem alunos retorna lista vazia."""
        dados = services.obter_alunos_turma(
            codigo_turma=999999,
            data_aula=datetime(2026, 6, 1, tzinfo=UTC),
        )
        self.assertEqual(dados, [])

    def test_nao_descarta_vinculo_indevido(self) -> None:
        """Verifica que vínculo indevido não é filtrado, como no legado."""
        codigo_turma = seed_turma_data_aula()
        Matricula.objects.create(
            codigo_matricula=700003,
            aluno_id=1234567,
            codigo_ue="100001",
            codigo_dre="108800",
            ano_letivo=2026,
            codigo_situacao_matricula=4,
            situacao_matricula="Vínculo Indevido",
            data_situacao_matricula=date(2026, 5, 1),
            data_situacao_matricula_data_hora=datetime(
                2026, 5, 1, 8, 0, tzinfo=UTC
            ),
        )
        MatriculaTurma.objects.create(
            codigo_matricula=700003,
            codigo_turma=codigo_turma,
            numero_chamada="99",
            data_situacao_aluno=date(2026, 5, 1),
            data_situacao_aluno_data_hora=datetime(
                2026, 5, 1, 8, 0, tzinfo=UTC
            ),
            codigo_situacao_aluno=4,
            codigo_tipo_turma=1,
            sequencia=0,
        )

        dados = services.obter_alunos_turma(
            codigo_turma=codigo_turma,
            data_aula=datetime(2026, 6, 1, tzinfo=UTC),
            considerar_inativos=True,
        )

        joao = {d["linha"]["aluno_id"]: d for d in dados}[1234567]
        self.assertEqual(joao["linha"]["codigo_matricula"], 700003)
        self.assertEqual(joao["linha"]["codigo_situacao_aluno"], 4)

    def test_dedup_mantem_maior_data_situacao(self) -> None:
        """Verifica a linha de maior data de situação na turma."""
        codigo_turma = seed_turma_data_aula()
        Matricula.objects.create(
            codigo_matricula=700004,
            aluno_id=1234567,
            codigo_ue="100001",
            codigo_dre="108800",
            ano_letivo=2026,
            codigo_situacao_matricula=2,
            situacao_matricula="Desistente",
            data_situacao_matricula=date(2026, 5, 10),
            data_situacao_matricula_data_hora=datetime(
                2026, 5, 10, 8, 0, tzinfo=UTC
            ),
        )
        MatriculaTurma.objects.create(
            codigo_matricula=700004,
            codigo_turma=codigo_turma,
            numero_chamada="20",
            data_situacao_aluno=date(2026, 5, 10),
            data_situacao_aluno_data_hora=datetime(
                2026, 5, 10, 8, 0, tzinfo=UTC
            ),
            codigo_situacao_aluno=14,
            codigo_tipo_turma=1,
            sequencia=4,
        )

        dados = services.obter_alunos_turma(
            codigo_turma=codigo_turma,
            data_aula=datetime(2026, 6, 1, tzinfo=UTC),
            considerar_inativos=True,
        )

        joao = {d["linha"]["aluno_id"]: d for d in dados}[1234567]
        self.assertEqual(joao["linha"]["codigo_matricula"], 700004)
        self.assertEqual(joao["linha"]["numero_chamada"], "20")
        self.assertEqual(joao["linha"]["codigo_situacao_aluno"], 14)

    def test_data_matricula_independe_da_alocacao_vencedora(self) -> None:
        """Verifica data_matricula fixa da matrícula, mesmo com dedup."""
        codigo_turma = seed_turma_data_aula()
        MatriculaTurma.objects.create(
            codigo_matricula=700001,
            codigo_turma=codigo_turma,
            numero_chamada="12",
            data_situacao_aluno=date(2026, 4, 20),
            data_situacao_aluno_data_hora=datetime(
                2026, 4, 20, 9, 0, tzinfo=UTC
            ),
            codigo_situacao_aluno=14,
            codigo_tipo_turma=1,
            sequencia=2,
        )

        dados = services.obter_alunos_turma(
            codigo_turma=codigo_turma,
            data_aula=datetime(2026, 6, 1, tzinfo=UTC),
            considerar_inativos=True,
        )

        joao = {d["linha"]["aluno_id"]: d for d in dados}[1234567]
        self.assertEqual(joao["linha"]["codigo_situacao_aluno"], 14)
        self.assertEqual(
            joao["linha"]["data_situacao_aluno_data_hora"],
            datetime(2026, 4, 20, 9, 0, tzinfo=UTC),
        )
        # A alocação vencedora é a de 20/04; a data de matrícula continua
        # sendo a da alocação mais antiga.
        self.assertEqual(
            joao["primeira_alocacao"],
            datetime(2026, 2, 10, 14, 0, tzinfo=UTC),
        )

    def test_dedup_desempata_por_data_situacao(self) -> None:
        """Verifica desempate por data de situação na mesma sequência."""
        codigo_turma = seed_turma_data_aula()
        Matricula.objects.create(
            codigo_matricula=700005,
            aluno_id=1234567,
            codigo_ue="100001",
            codigo_dre="108800",
            ano_letivo=2026,
            codigo_situacao_matricula=1,
            situacao_matricula="Ativo",
            data_situacao_matricula=date(2026, 5, 10),
            data_situacao_matricula_data_hora=datetime(
                2026, 5, 10, 8, 0, tzinfo=UTC
            ),
        )
        MatriculaTurma.objects.create(
            codigo_matricula=700005,
            codigo_turma=codigo_turma,
            numero_chamada="20",
            data_situacao_aluno=date(2026, 5, 10),
            data_situacao_aluno_data_hora=datetime(
                2026, 5, 10, 8, 0, tzinfo=UTC
            ),
            codigo_situacao_aluno=1,
            codigo_tipo_turma=1,
            sequencia=1,
        )

        dados = services.obter_alunos_turma(
            codigo_turma=codigo_turma,
            data_aula=datetime(2026, 6, 1, tzinfo=UTC),
        )

        joao = {d["linha"]["aluno_id"]: d for d in dados}[1234567]
        self.assertEqual(joao["linha"]["codigo_matricula"], 700005)
        self.assertEqual(joao["linha"]["numero_chamada"], "20")

    def test_data_aula_nula_e_primeira_sequencia_ordena_chamada(self) -> None:
        """Verifica ordenação por chamada com ticks zero e sequência 1."""
        codigo_turma = seed_turma_data_aula()
        MatriculaTurma.objects.filter(codigo_matricula=700002).update(
            sequencia=1
        )
        dados = services.obter_alunos_turma(
            codigo_turma=codigo_turma,
            data_aula=None,
            sequencia=1,
        )
        self.assertEqual(
            [d["linha"]["numero_chamada"] for d in dados], ["07", "12"]
        )

    def test_data_aula_nula_sem_primeira_sequencia_nao_ordena(self) -> None:
        """Verifica que sem sequência 1 a ordenação por chamada não ocorre."""
        codigo_turma = seed_turma_data_aula()
        dados = services.obter_alunos_turma(
            codigo_turma=codigo_turma,
            data_aula=None,
        )
        self.assertEqual(
            {d["linha"]["aluno_id"] for d in dados}, {1234567, 7654321}
        )

    def test_sem_parametro_default_false_restringe_situacoes(self) -> None:
        """Verifica que o default (False) restringe as situações inativas."""
        codigo_turma = seed_turma_data_aula()
        MatriculaTurma.objects.filter(codigo_matricula=700002).update(
            codigo_situacao_aluno=14
        )

        dados = services.obter_alunos_turma(
            codigo_turma=codigo_turma,
            data_aula=datetime(2026, 6, 1, tzinfo=UTC),
        )

        self.assertEqual([d["linha"]["aluno_id"] for d in dados], [1234567])

    def test_considerar_inativos_false_filtra_situacoes(self) -> None:
        """Verifica que situações fora do conjunto são excluídas com False."""
        codigo_turma = seed_turma_data_aula()
        MatriculaTurma.objects.filter(codigo_matricula=700002).update(
            codigo_situacao_aluno=14
        )

        dados = services.obter_alunos_turma(
            codigo_turma=codigo_turma,
            data_aula=datetime(2026, 6, 1, tzinfo=UTC),
            considerar_inativos=False,
        )

        self.assertEqual([d["linha"]["aluno_id"] for d in dados], [1234567])

    def test_considerar_inativos_false_dedup_antes_do_filtro(self) -> None:
        """Verifica que a dedup ocorre antes do filtro de situação.

        Aluno com duas sequências na turma: a de maior ``data_situacao``
        tem situação inativa. Pelo legado, a dedup elege essa linha e o
        filtro de situação a descarta, removendo o aluno por completo —
        sem cair para a outra sequência ativa.
        """
        codigo_turma = seed_turma_data_aula()
        MatriculaTurma.objects.create(
            codigo_matricula=700001,
            codigo_turma=codigo_turma,
            numero_chamada="12",
            data_situacao_aluno=date(2026, 3, 1),
            data_situacao_aluno_data_hora=datetime(
                2026, 3, 1, 14, 0, tzinfo=UTC
            ),
            codigo_situacao_aluno=14,
            codigo_tipo_turma=1,
            nome_turma="5A",
            codigo_etapa_ensino=5,
            sequencia=2,
        )

        dados = services.obter_alunos_turma(
            codigo_turma=codigo_turma,
            data_aula=None,
            codigo_aluno=1234567,
            considerar_inativos=False,
        )

        self.assertEqual(dados, [])

    def test_considerar_inativos_true_traz_todas_situacoes(self) -> None:
        """Verifica que situações fora do conjunto entram quando True."""
        codigo_turma = seed_turma_data_aula()
        MatriculaTurma.objects.filter(codigo_matricula=700002).update(
            codigo_situacao_aluno=14
        )

        dados = services.obter_alunos_turma(
            codigo_turma=codigo_turma,
            data_aula=datetime(2026, 6, 1, tzinfo=UTC),
            considerar_inativos=True,
        )

        self.assertEqual(
            {d["linha"]["aluno_id"] for d in dados}, {1234567, 7654321}
        )

    def test_sequencia_filtra_matricula_turma(self) -> None:
        """Verifica que o filtro de sequência restringe a matrícula-turma."""
        codigo_turma = seed_turma_data_aula()
        dados = services.obter_alunos_turma(
            codigo_turma=codigo_turma,
            data_aula=datetime(2026, 6, 1, tzinfo=UTC),
            sequencia=1,
        )
        self.assertEqual([d["linha"]["aluno_id"] for d in dados], [1234567])

    def test_sequencia_ausente_traz_todas(self) -> None:
        """Verifica que sem sequência todas as alocações são consideradas."""
        codigo_turma = seed_turma_data_aula()
        dados = services.obter_alunos_turma(
            codigo_turma=codigo_turma,
            data_aula=datetime(2026, 6, 1, tzinfo=UTC),
        )
        self.assertEqual(
            {d["linha"]["aluno_id"] for d in dados}, {1234567, 7654321}
        )

    def test_contar_matriculas_turmas_periodo_conta_alocacoes(self) -> None:
        """Conta alocações válidas, não alunos distintos."""
        codigo_turma = seed_turma_data_aula()
        # Segunda alocação válida da mesma matrícula 700001.
        MatriculaTurma.objects.create(
            codigo_matricula=700001,
            codigo_turma=codigo_turma,
            numero_chamada="12",
            data_situacao_aluno=date(2026, 3, 1),
            data_situacao_aluno_data_hora=datetime(
                2026, 3, 1, 10, 0, tzinfo=UTC
            ),
            codigo_situacao_aluno=1,
            codigo_tipo_turma=1,
            sequencia=5,
        )

        total = services.contar_matriculas_turmas_periodo(
            codigos_turmas=[codigo_turma],
            data_fim=datetime(2026, 12, 31, tzinfo=UTC),
        )

        # 700001 (2 alocações) + 700002 (1) = 3.
        self.assertEqual(total, 3)

    def test_contar_matriculas_turmas_periodo_exclui_situacao(self) -> None:
        """Alocações fora do conjunto válido não entram na contagem."""
        codigo_turma = seed_turma_data_aula()
        MatriculaTurma.objects.filter(codigo_matricula=700002).update(
            codigo_situacao_aluno=2
        )

        total = services.contar_matriculas_turmas_periodo(
            codigos_turmas=[codigo_turma],
            data_fim=datetime(2026, 12, 31, tzinfo=UTC),
        )

        self.assertEqual(total, 1)

    def test_contar_matriculas_turmas_periodo_filtra_data(self) -> None:
        """Matrícula cuja primeira alocação é posterior à data não conta."""
        codigo_turma = seed_turma_data_aula()

        total = services.contar_matriculas_turmas_periodo(
            codigos_turmas=[codigo_turma],
            data_fim=datetime(2026, 1, 1, tzinfo=UTC),
        )

        self.assertEqual(total, 0)

    def test_contar_matriculas_turmas_periodo_sem_turmas(self) -> None:
        """Lista de turmas vazia devolve zero."""
        total = services.contar_matriculas_turmas_periodo(
            codigos_turmas=[],
            data_fim=datetime(2026, 12, 31, tzinfo=UTC),
        )
        self.assertEqual(total, 0)

    def test_acompanhamento_escolar_traz_aluno_com_responsavel(self) -> None:
        """Retorna o aluno com responsável vigente e seus dados de contato."""
        codigo_turma = seed_turma_data_aula()
        seed_responsaveis()

        dados = services.obter_acompanhamento_escolar_turma(codigo_turma)

        self.assertEqual(len(dados), 1)
        d = dados[0]
        self.assertEqual(d["codigo_eol_aluno"], 1234567)
        self.assertEqual(d["cpf"], 12345678901)
        self.assertEqual(d["nome_responsavel"], "Responsavel Exemplo")
        self.assertEqual(d["tipo_responsavel"], 1)
        self.assertEqual(d["ddd_fixo"], "11")
        self.assertEqual(d["telefone_fixo"], "33334444")

    def test_acompanhamento_escolar_exclui_aluno_sem_responsavel(
        self,
    ) -> None:
        """Aluno sem responsável vigente não aparece (junção interna)."""
        codigo_turma = seed_turma_data_aula()
        seed_responsaveis()

        dados = services.obter_acompanhamento_escolar_turma(codigo_turma)

        codigos = {d["codigo_eol_aluno"] for d in dados}
        self.assertNotIn(7654321, codigos)

    def test_acompanhamento_escolar_exclui_responsavel_encerrado(
        self,
    ) -> None:
        """Responsável com vínculo encerrado não habilita o aluno."""
        codigo_turma = seed_turma_data_aula()
        seed_responsaveis()
        ResponsavelAluno.objects.filter(aluno_id=1234567).update(
            data_fim_vinculo=date(2026, 3, 1)
        )

        dados = services.obter_acompanhamento_escolar_turma(codigo_turma)

        self.assertEqual(dados, [])

    def test_acompanhamento_escolar_cpf_ausente_vira_zero(self) -> None:
        """CPF nulo no responsável é publicado como zero."""
        codigo_turma = seed_turma_data_aula()
        seed_responsaveis()
        ResponsavelAluno.objects.filter(codigo_responsavel=5501).update(
            cpf=None
        )

        dados = services.obter_acompanhamento_escolar_turma(codigo_turma)

        self.assertEqual(dados[0]["cpf"], 0)

    def test_acompanhamento_escolar_numero_chamada_vazio_vira_none(
        self,
    ) -> None:
        """Número de chamada ausente vira ``None``, não ``'000'``."""
        codigo_turma = seed_turma_data_aula()
        seed_responsaveis()
        MatriculaTurma.objects.filter(codigo_matricula=700001).update(
            numero_chamada=""
        )

        dados = services.obter_acompanhamento_escolar_turma(codigo_turma)

        self.assertIsNone(dados[0]["numero_chamada"])

    def test_acompanhamento_escolar_so_tipo_turma_um(self) -> None:
        """Turma de tipo diferente de acompanhamento não retorna alunos."""
        codigo_turma = seed_turma_data_aula()
        seed_responsaveis()
        MatriculaTurma.objects.filter(codigo_turma=codigo_turma).update(
            codigo_tipo_turma=3
        )

        dados = services.obter_acompanhamento_escolar_turma(codigo_turma)

        self.assertEqual(dados, [])

    def test_acompanhamento_escolar_dedup_situacao_mais_recente(self) -> None:
        """Cada aluno rende a linha de situação mais recente."""
        codigo_turma = seed_turma_data_aula()
        seed_responsaveis()
        MatriculaTurma.objects.create(
            codigo_matricula=700001,
            codigo_turma=codigo_turma,
            numero_chamada="15",
            data_situacao_aluno=date(2026, 6, 1),
            data_situacao_aluno_data_hora=datetime(
                2026, 6, 1, 10, 0, tzinfo=UTC
            ),
            codigo_situacao_aluno=3,
            codigo_tipo_turma=1,
            sequencia=9,
        )

        dados = services.obter_acompanhamento_escolar_turma(codigo_turma)

        self.assertEqual(len(dados), 1)
        self.assertEqual(dados[0]["situacao_aluno"], 3)
        self.assertEqual(dados[0]["numero_chamada"], "15")

    def _alocacao(
        self,
        codigo_turma: int,
        situacao: int,
        dia: int,
        sequencia: int,
        numero_chamada: str,
        codigo_matricula: int = 700001,
    ) -> None:
        """Cria uma alocação extra da matrícula na turma."""
        MatriculaTurma.objects.create(
            codigo_matricula=codigo_matricula,
            codigo_turma=codigo_turma,
            numero_chamada=numero_chamada,
            data_situacao_aluno=date(2026, 3, dia),
            data_situacao_aluno_data_hora=datetime(
                2026, 3, dia, 10, 0, tzinfo=UTC
            ),
            codigo_situacao_aluno=situacao,
            codigo_tipo_turma=1,
            sequencia=sequencia,
        )

    def test_todos_alunos_turma_atualiza_linha_sem_remanejamento(
        self,
    ) -> None:
        """Alocação seguinte atualiza a linha corrente da matrícula."""
        codigo_turma = seed_turma_data_aula()
        self._alocacao(
            codigo_turma, situacao=3, dia=5, sequencia=5, numero_chamada="88"
        )

        dados = [
            d
            for d in services.obter_todos_alunos_turma(codigo_turma)
            if d["linha"]["codigo_matricula"] == 700001
        ]

        self.assertEqual(len(dados), 1)
        self.assertEqual(dados[0]["linha"]["codigo_situacao_aluno"], 3)
        self.assertEqual(dados[0]["linha"]["numero_chamada"], "88")
        # A data de matrícula continua sendo a da alocação que abriu a linha.
        self.assertEqual(
            dados[0]["primeira_alocacao"],
            datetime(2026, 2, 10, 14, 0, tzinfo=UTC),
        )

    def test_todos_alunos_turma_remanejamento_abre_linha_nova(self) -> None:
        """Remanejamento de saída faz a matrícula aparecer duas vezes."""
        codigo_turma = seed_turma_data_aula()
        MatriculaTurma.objects.filter(
            codigo_matricula=700001, sequencia=1
        ).update(codigo_situacao_aluno=14)
        self._alocacao(
            codigo_turma, situacao=1, dia=5, sequencia=5, numero_chamada="88"
        )

        dados = [
            d
            for d in services.obter_todos_alunos_turma(codigo_turma)
            if d["linha"]["codigo_matricula"] == 700001
        ]

        self.assertEqual(len(dados), 2)
        self.assertEqual(dados[0]["linha"]["codigo_situacao_aluno"], 14)
        self.assertEqual(dados[1]["linha"]["codigo_situacao_aluno"], 1)
        # Cada linha carrega a data da alocação que a abriu.
        self.assertEqual(
            dados[0]["primeira_alocacao"],
            datetime(2026, 2, 10, 14, 0, tzinfo=UTC),
        )
        self.assertEqual(
            dados[1]["primeira_alocacao"],
            datetime(2026, 3, 5, 10, 0, tzinfo=UTC),
        )

    def test_todos_alunos_turma_remanejamento_seguido_atualiza(self) -> None:
        """Após reabrir a linha, a alocação seguinte volta a atualizar."""
        codigo_turma = seed_turma_data_aula()
        MatriculaTurma.objects.filter(
            codigo_matricula=700001, sequencia=1
        ).update(codigo_situacao_aluno=14)
        self._alocacao(
            codigo_turma, situacao=1, dia=5, sequencia=5, numero_chamada="88"
        )
        self._alocacao(
            codigo_turma, situacao=5, dia=9, sequencia=6, numero_chamada="77"
        )

        dados = [
            d
            for d in services.obter_todos_alunos_turma(codigo_turma)
            if d["linha"]["codigo_matricula"] == 700001
        ]

        self.assertEqual(len(dados), 2)
        self.assertEqual(dados[1]["linha"]["codigo_situacao_aluno"], 5)
        self.assertEqual(dados[1]["linha"]["numero_chamada"], "77")

    def test_todos_alunos_turma_empate_de_data_usa_sequencia(self) -> None:
        """Empate na data de situação é resolvido pela sequência.

        Cenário real do banco: a mesma matrícula tem duas alocações na turma
        com a mesma data, a sequência 1 com remanejamento de saída e a
        seguinte com o vínculo ativo. A ordem de percurso decide se sai uma
        linha ou duas, então precisa ser estável.
        """
        codigo_turma = seed_turma_data_aula()
        MatriculaTurma.objects.filter(
            codigo_matricula=700001, sequencia=1
        ).update(codigo_situacao_aluno=14)
        # Mesma data da alocação de sequência 1, situação ativa.
        MatriculaTurma.objects.create(
            codigo_matricula=700001,
            codigo_turma=codigo_turma,
            numero_chamada="12",
            data_situacao_aluno=date(2026, 2, 10),
            data_situacao_aluno_data_hora=datetime(
                2026, 2, 10, 14, 0, tzinfo=UTC
            ),
            codigo_situacao_aluno=1,
            codigo_tipo_turma=1,
            sequencia=2,
        )

        dados = [
            d
            for d in services.obter_todos_alunos_turma(codigo_turma)
            if d["linha"]["codigo_matricula"] == 700001
        ]

        self.assertEqual(len(dados), 2)
        self.assertEqual(dados[0]["linha"]["codigo_situacao_aluno"], 14)
        self.assertEqual(dados[1]["linha"]["codigo_situacao_aluno"], 1)

    def test_todos_alunos_turma_nao_filtra_situacao(self) -> None:
        """Situações inativas permanecem no resultado."""
        codigo_turma = seed_turma_data_aula()
        MatriculaTurma.objects.filter(codigo_matricula=700002).update(
            codigo_situacao_aluno=8
        )

        dados = services.obter_todos_alunos_turma(codigo_turma)

        situacoes = {
            d["linha"]["codigo_matricula"]: d["linha"]["codigo_situacao_aluno"]
            for d in dados
        }
        self.assertEqual(situacoes[700002], 8)

    def test_todos_alunos_turma_filtra_por_aluno(self) -> None:
        """O filtro por aluno restringe o resultado."""
        codigo_turma = seed_turma_data_aula()

        dados = services.obter_todos_alunos_turma(
            codigo_turma, codigo_aluno=1234567
        )

        self.assertEqual({d["linha"]["aluno_id"] for d in dados}, {1234567})

    def test_todos_alunos_turma_sem_vinculo(self) -> None:
        """Turma sem vínculo devolve lista vazia."""
        seed_turma_data_aula()

        self.assertEqual(services.obter_todos_alunos_turma(9999999), [])

    def test_matriculas_turmas_aluno_uma_linha_por_matricula(self) -> None:
        """Verifica que cada matrícula do aluno rende uma única linha."""
        seed_turma_data_aula()
        MatriculaTurma.objects.filter(codigo_matricula=700001).update(
            codigo_turma=3015604
        )

        dados = services.obter_matriculas_turmas_aluno(codigo_aluno=1234567)

        self.assertEqual(
            [d["linha"]["codigo_matricula"] for d in dados], [700001]
        )
        self.assertEqual(dados[0]["linha"]["codigo_ue"], "100001")
        self.assertEqual(dados[0]["linha"]["codigo_dre"], "108800")
        self.assertEqual(dados[0]["linha"]["ano_letivo"], 2026)

    def test_matriculas_turmas_aluno_alocacao_mais_recente(self) -> None:
        """Verifica que a alocação mais recente da matrícula prevalece."""
        codigo_turma = seed_turma_data_aula()
        MatriculaTurma.objects.create(
            codigo_matricula=700001,
            codigo_turma=codigo_turma,
            numero_chamada="99",
            data_situacao_aluno=date(2026, 6, 1),
            data_situacao_aluno_data_hora=datetime(
                2026, 6, 1, 10, 0, tzinfo=UTC
            ),
            codigo_situacao_aluno=3,
            codigo_tipo_turma=1,
            sequencia=9,
        )

        dados = services.obter_matriculas_turmas_aluno(codigo_aluno=1234567)

        self.assertEqual(len(dados), 1)
        self.assertEqual(dados[0]["linha"]["numero_chamada"], "99")
        self.assertEqual(dados[0]["linha"]["codigo_situacao_aluno"], 3)

    def test_matriculas_turmas_aluno_data_aula_restringe(self) -> None:
        """Verifica o filtro por data de situação da alocação."""
        seed_turma_data_aula()

        dados = services.obter_matriculas_turmas_aluno(
            codigo_aluno=1234567,
            data_aula=datetime(2026, 1, 1, tzinfo=UTC),
        )

        self.assertEqual(dados, [])

    def test_matriculas_turmas_aluno_ano_letivo_restringe(self) -> None:
        """Verifica o filtro por ano letivo da turma."""
        seed_turma_data_aula()
        MatriculaTurma.objects.filter(codigo_matricula=700001).update(
            ano_letivo_turma=2026
        )

        dados = services.obter_matriculas_turmas_aluno(
            codigo_aluno=1234567, ano_letivo=2025
        )

        self.assertEqual(dados, [])

    def test_matriculas_turmas_aluno_sem_matricula(self) -> None:
        """Verifica retorno vazio para aluno sem matrícula."""
        seed_turma_data_aula()

        dados = services.obter_matriculas_turmas_aluno(codigo_aluno=999999)

        self.assertEqual(dados, [])

    def test_ano_letivo_filtra_alocacoes_da_turma(self) -> None:
        """Verifica que o ano letivo restringe as alocações consideradas."""
        codigo_turma = seed_turma_data_aula()
        MatriculaTurma.objects.filter(codigo_matricula=700001).update(
            ano_letivo_turma=2026
        )
        MatriculaTurma.objects.filter(codigo_matricula=700002).update(
            ano_letivo_turma=2025
        )

        dados = services.obter_alunos_turma(
            codigo_turma=codigo_turma,
            data_aula=None,
            considerar_inativos=True,
            ano_letivo=2026,
        )

        self.assertEqual([d["linha"]["aluno_id"] for d in dados], [1234567])

    def test_ano_letivo_ausente_traz_todos_os_anos(self) -> None:
        """Verifica que sem ano letivo todas as alocações são consideradas."""
        codigo_turma = seed_turma_data_aula()
        MatriculaTurma.objects.filter(codigo_matricula=700001).update(
            ano_letivo_turma=2026
        )
        MatriculaTurma.objects.filter(codigo_matricula=700002).update(
            ano_letivo_turma=2025
        )

        dados = services.obter_alunos_turma(
            codigo_turma=codigo_turma,
            data_aula=None,
            considerar_inativos=True,
        )

        self.assertEqual(
            {d["linha"]["aluno_id"] for d in dados}, {1234567, 7654321}
        )

    def test_ano_letivo_sem_correspondencia_retorna_vazio(self) -> None:
        """Verifica ano letivo sem alocação correspondente na turma."""
        codigo_turma = seed_turma_data_aula()
        MatriculaTurma.objects.filter(codigo_turma=codigo_turma).update(
            ano_letivo_turma=2026
        )

        dados = services.obter_alunos_turma(
            codigo_turma=codigo_turma,
            data_aula=None,
            considerar_inativos=True,
            ano_letivo=2024,
        )

        self.assertEqual(dados, [])

    def test_considera_inativos_false_sem_data_filtra_situacoes(self) -> None:
        """Reproduz o legado considera-inativos=false (sem filtro de data)."""
        codigo_turma = seed_turma_data_aula()
        MatriculaTurma.objects.filter(codigo_matricula=700002).update(
            codigo_situacao_aluno=14
        )
        dados = services.obter_alunos_turma(
            codigo_turma=codigo_turma,
            data_aula=None,
            considerar_inativos=False,
        )
        self.assertEqual([d["linha"]["aluno_id"] for d in dados], [1234567])

    def test_considera_inativos_true_sem_data_traz_todas(self) -> None:
        """Reproduz o legado considera-inativos=true (sem filtro de data)."""
        codigo_turma = seed_turma_data_aula()
        MatriculaTurma.objects.filter(codigo_matricula=700002).update(
            codigo_situacao_aluno=14
        )
        dados = services.obter_alunos_turma(
            codigo_turma=codigo_turma,
            data_aula=None,
            considerar_inativos=True,
        )
        self.assertEqual(
            {d["linha"]["aluno_id"] for d in dados}, {1234567, 7654321}
        )

    def test_codigo_aluno_com_considera_inativos(self) -> None:
        """Reproduz o legado aluno/{codigo}/considera-inativos."""
        codigo_turma = seed_turma_data_aula()
        dados = services.obter_alunos_turma(
            codigo_turma=codigo_turma,
            data_aula=None,
            codigo_aluno=1234567,
            considerar_inativos=False,
        )
        self.assertEqual([d["linha"]["aluno_id"] for d in dados], [1234567])

    def test_filtra_por_codigo_aluno(self) -> None:
        """Verifica que codigo_aluno restringe o resultado ao aluno."""
        codigo_turma = seed_turma_data_aula()
        dados = services.obter_alunos_turma(
            codigo_turma=codigo_turma,
            data_aula=None,
            codigo_aluno=7654321,
        )
        self.assertEqual([d["linha"]["aluno_id"] for d in dados], [7654321])

    def test_codigo_aluno_ausente_na_turma_retorna_vazio(self) -> None:
        """Verifica que aluno fora da turma retorna lista vazia."""
        codigo_turma = seed_turma_data_aula()
        dados = services.obter_alunos_turma(
            codigo_turma=codigo_turma,
            data_aula=None,
            codigo_aluno=999999,
        )
        self.assertEqual(dados, [])

    def test_data_matricula_ordena_por_nome(self) -> None:
        """Verifica ordenação por nome do aluno na variante por matrícula."""
        codigo_turma = seed_turma_data_aula()
        dados = services.obter_alunos_turma(
            codigo_turma=codigo_turma,
            data_aula=None,
            data_matricula=datetime(2026, 6, 1, tzinfo=UTC),
        )
        nomes = [d["aluno"]["nome"] for d in dados]
        self.assertEqual(nomes, sorted(nomes))

    def test_data_matricula_descarta_vinculo_indevido(self) -> None:
        """Verifica que Vínculo Indevido sai na variante por matrícula."""
        codigo_turma = seed_turma_data_aula()
        MatriculaTurma.objects.filter(codigo_matricula=700002).update(
            codigo_situacao_aluno=4
        )
        dados = services.obter_alunos_turma(
            codigo_turma=codigo_turma,
            data_aula=None,
            data_matricula=datetime(2026, 6, 1, tzinfo=UTC),
        )
        self.assertEqual([d["linha"]["aluno_id"] for d in dados], [1234567])

    def test_data_matricula_condicao_por_situacao(self) -> None:
        """Verifica a condição composta por data de situação/matrícula."""
        codigo_turma = seed_turma_data_aula()
        Matricula.objects.filter(codigo_matricula=700002).update(
            data_situacao_matricula_data_hora=datetime(
                2026, 5, 1, 9, 0, tzinfo=UTC
            )
        )
        MatriculaTurma.objects.filter(codigo_matricula=700002).update(
            codigo_situacao_aluno=1
        )
        dados = services.obter_alunos_turma(
            codigo_turma=codigo_turma,
            data_aula=None,
            data_matricula=datetime(2026, 2, 5, tzinfo=UTC),
        )
        self.assertEqual([d["linha"]["aluno_id"] for d in dados], [1234567])

    def test_data_aula_e_data_matricula_aplicam_ambos(self) -> None:
        """Verifica que os dois filtros de data convivem (AND)."""
        codigo_turma = seed_turma_data_aula()
        dados = services.obter_alunos_turma(
            codigo_turma=codigo_turma,
            data_aula=datetime(2026, 6, 1, tzinfo=UTC),
            data_matricula=datetime(2026, 6, 1, tzinfo=UTC),
        )
        self.assertEqual(
            {d["linha"]["aluno_id"] for d in dados}, {1234567, 7654321}
        )

    def test_sem_n_mais_um(self) -> None:
        """Verifica que a consulta usa um número fixo de queries."""
        codigo_turma = seed_turma_data_aula()
        with self.assertNumQueries(5):
            services.obter_alunos_turma(
                codigo_turma=codigo_turma,
                data_aula=datetime(2026, 6, 1, tzinfo=UTC),
            )

    def test_responsaveis_por_aluno_vazio(self) -> None:
        """Verifica que lista de códigos vazia não consulta o banco."""
        from apps.alunos.services.responsaveis import responsaveis_por_aluno

        with self.assertNumQueries(0):
            resultado = responsaveis_por_aluno([])
        self.assertEqual(resultado, {})


class MapeamentosInternosTestCase(TestCase):
    """Valida os mapeamentos puros de modalidade e raça/cor."""

    def test_modalidade_por_etapa_cobre_faixas(self) -> None:
        """Verifica a sigla legada de cada faixa de etapa de ensino."""
        from apps.alunos.constants import MODALIDADE_POR_ETAPA

        self.assertEqual(MODALIDADE_POR_ETAPA.get(1), "EI")
        self.assertEqual(MODALIDADE_POR_ETAPA.get(2), "EJA")
        self.assertEqual(MODALIDADE_POR_ETAPA.get(4), "EF")
        self.assertEqual(MODALIDADE_POR_ETAPA.get(6), "EM")

    def test_modalidade_por_etapa_desconhecida(self) -> None:
        """Verifica que etapa fora do mapa retorna None."""
        from apps.alunos.constants import MODALIDADE_POR_ETAPA

        self.assertIsNone(MODALIDADE_POR_ETAPA.get(99))
        self.assertIsNone(MODALIDADE_POR_ETAPA.get(None))

    def test_codigo_raca_vazia_retorna_none(self) -> None:
        """Verifica que raça/cor ausente ou vazia retorna None."""
        from apps.alunos.constants import codigo_raca

        self.assertIsNone(codigo_raca(None))
        self.assertIsNone(codigo_raca(""))


class AlunosAtivosPorPeriodoTurmaTestCase(TestCase):
    """Valida o filtro de janela de datas em alunos ativos por turma."""

    def test_matricula_ativa_anterior_ao_inicio_e_incluida(self) -> None:
        """Verifica inclusão de matrícula ativa anterior à data inicial."""
        seed_matriculas()
        dados = services.obter_alunos_ativos_por_periodo_e_turma(
            codigo_turma=12345,
            data_referencia_inicio=date(2026, 3, 1),
            data_referencia_fim=date(2026, 12, 31),
        )
        self.assertEqual(len(dados), 1)
        self.assertEqual(dados[0]["linha"]["aluno_id"], 1234567)

    def test_matricula_posterior_ao_fim_e_excluida(self) -> None:
        """Verifica exclusão de matrícula após a data final."""
        seed_matriculas()
        dados = services.obter_alunos_ativos_por_periodo_e_turma(
            codigo_turma=12345,
            data_referencia_inicio=date(2026, 1, 1),
            data_referencia_fim=date(2026, 1, 31),
        )
        self.assertEqual(dados, [])

    def test_matricula_dentro_da_janela_e_incluida(self) -> None:
        """Verifica que matrícula dentro do intervalo é retornada."""
        seed_matriculas()
        dados = services.obter_alunos_ativos_por_periodo_e_turma(
            codigo_turma=12345,
            data_referencia_inicio=date(2026, 1, 1),
            data_referencia_fim=date(2026, 12, 31),
        )
        self.assertEqual(len(dados), 1)

    def test_turma_de_ano_anterior_e_retornada(self) -> None:
        """Verifica que o ano letivo é escopado pela turma, não pelo atual."""
        seed_alunos()
        Matricula.objects.create(
            codigo_matricula=20230001,
            aluno_id=1234567,
            codigo_ue="100001",
            ano_letivo=2023,
            codigo_situacao_matricula=1,
            situacao_matricula="Ativo",
            data_situacao_matricula=date(2023, 2, 1),
            origem_atual=True,
        )
        MatriculaTurma.objects.create(
            codigo_matricula=20230001,
            codigo_turma=98765,
            numero_chamada="05",
            data_situacao_aluno=date(2023, 2, 1),
            codigo_situacao_aluno=1,
            codigo_tipo_turma=1,
            tipo_turno=2,
            nome_turma="3A",
            codigo_ue_turma="100001",
            codigo_etapa_ensino=5,
            codigo_ciclo_ensino=2,
            descricao_etapa_ensino=DESCRICAO_ETAPA_ENSINO_FUNDAMENTAL,
            descricao_ciclo_ensino="Ciclo Interdisciplinar",
            sequencia=1,
            origem_atual=True,
            ano_letivo_turma=2023,
        )
        dados = services.obter_alunos_ativos_por_periodo_e_turma(
            codigo_turma=98765,
            data_referencia_fim=date(2023, 12, 31),
        )
        self.assertEqual(len(dados), 1)
        self.assertEqual(dados[0]["linha"]["aluno_id"], 1234567)
        self.assertEqual(dados[0]["linha"]["ano_letivo"], 2023)


class AcompanhamentoEscolarFiltroTurmaTestCase(TestCase):
    """Valida o filtro por turma no acompanhamento escolar."""

    def test_turma_codigo_invalido_retorna_vazio(self) -> None:
        """Verifica que turma não numérica gera saída vazia."""
        seed_matriculas()
        dados = services.obter_dados_acompanhamento_escolar(turma_codigo="abc")
        self.assertEqual(dados, [])

    def test_turma_codigo_sem_match_retorna_vazio(self) -> None:
        """Verifica que turma sem matrícula vinculada gera saída vazia."""
        seed_matriculas()
        dados = services.obter_dados_acompanhamento_escolar(
            turma_codigo="99999999"
        )
        self.assertEqual(dados, [])

    def test_turma_codigo_com_match_retorna_dados(self) -> None:
        """Verifica que turma vinculada retorna o aluno correspondente."""
        seed_matriculas()
        dados = services.obter_dados_acompanhamento_escolar(
            turma_codigo="12345"
        )
        self.assertEqual(len(dados), 1)


class CodigosTurmasRegularesAlunoTestCase(TestCase):
    """Valida obter_codigos_turmas_regulares_aluno (endpoints 3/4)."""

    def _matricula(
        self,
        codigo_matricula: int,
        situacao: int = 1,
        origem_atual: bool = True,
        origem_historica: bool | None = None,
    ) -> None:
        # Matrícula vinda só da fonte histórica sempre está presente nela;
        # a flag explícita cobre o caso de matrícula nas duas fontes.
        if origem_historica is None:
            origem_historica = not origem_atual
        Matricula.objects.create(
            codigo_matricula=codigo_matricula,
            aluno_id=1234567,
            codigo_ue="100001",
            ano_letivo=2026,
            codigo_situacao_matricula=situacao,
            situacao_matricula="Ativo",
            data_situacao_matricula=date(2026, 2, 1),
            origem_atual=origem_atual,
            origem_historica=origem_historica,
        )

    def _vinculo(
        self,
        codigo_matricula: int,
        codigo_turma: int,
        situacao: int,
        data: date,
        sequencia: int = 1,
        origem_atual: bool = True,
        ano_letivo_turma: int = 2026,
    ) -> None:
        MatriculaTurma.objects.create(
            codigo_matricula=codigo_matricula,
            codigo_turma=codigo_turma,
            data_situacao_aluno=data,
            data_situacao_aluno_data_hora=datetime(
                data.year, data.month, data.day, 12, 0, tzinfo=UTC
            ),
            codigo_situacao_aluno=situacao,
            codigo_tipo_turma=1,
            sequencia=sequencia,
            origem_atual=origem_atual,
            ano_letivo_turma=ano_letivo_turma,
        )

    def _obter(self, **kwargs):  # type: ignore[no-untyped-def]
        with patch(
            "django.utils.timezone.now",
            return_value=datetime(2026, 6, 1, tzinfo=UTC),
        ):
            return services.obter_codigos_turmas_regulares_aluno(
                codigo_aluno=1234567, ano_letivo=2026, **kwargs
            )

    def test_retorna_turmas_ativas_ordenadas_por_data_desc(self) -> None:
        """Turmas ativas saem ordenadas por data da situação decrescente."""
        seed_alunos()
        self._matricula(998877)
        self._vinculo(998877, 12345, 1, date(2026, 2, 1))
        self._vinculo(998877, 23456, 1, date(2026, 3, 10))
        self.assertEqual(self._obter(), [23456, 12345])

    def test_exclui_vinculo_indevido(self) -> None:
        """Vínculo indevido é excluído mesmo passando no filtro de data."""
        seed_alunos()
        self._matricula(998877)
        self._vinculo(998877, 12345, 1, date(2026, 2, 1))
        self._vinculo(998877, 99999, 4, date(2026, 12, 1))
        self.assertEqual(self._obter(), [12345])

    def test_mantem_turma_com_vinculo_indevido_historico_cross_origem(
        self,
    ) -> None:
        """Mantém turma com vínculo ativo corrente + VI histórico.

        Caso real do aluno 69277 vs. legado de PRODUÇÃO: a mesma
        matrícula+turma tem um vínculo ativo corrente (situação 1) e um
        Vínculo Indevido histórico (situação 4) na mesma DATA, porém em
        HORA diferente. O legado compara ``dt_situacao_aluno`` (data+hora),
        não casa o VI e mantém a turma — o transition deve fazer o mesmo,
        sem excluir por Vínculo Indevido do ramo oposto.
        """
        seed_alunos()
        self._matricula(998877, origem_atual=True)
        self._vinculo(998877, 12345, 1, date(2026, 4, 27), origem_atual=True)
        self._vinculo(
            998877,
            12345,
            4,
            date(2026, 4, 27),
            sequencia=2,
            origem_atual=False,
        )
        self._vinculo(998877, 23456, 1, date(2026, 3, 10))
        self.assertEqual(self._obter(), [12345, 23456])

    def test_inativa_incluida_quando_saiu_apos_data_referencia(self) -> None:
        """Situação inativa após a data de referência é considerada."""
        seed_alunos()
        self._matricula(998877)
        self._vinculo(998877, 12345, 2, date(2026, 8, 1))
        self.assertEqual(self._obter(), [12345])

    def test_inativa_excluida_quando_saiu_antes_da_data(self) -> None:
        """Situação inativa anterior à data de referência é descartada."""
        seed_alunos()
        self._matricula(998877)
        self._vinculo(998877, 12345, 2, date(2026, 3, 1))
        self.assertEqual(self._obter(), [])

    def test_deduplica_turma_entre_matriculas(self) -> None:
        """Mesma turma em matrículas distintas aparece uma única vez."""
        seed_alunos()
        self._matricula(998877)
        self._matricula(998878)
        self._vinculo(998877, 12345, 1, date(2026, 2, 1))
        self._vinculo(998878, 12345, 1, date(2026, 4, 1))
        self.assertEqual(self._obter(), [12345])

    def test_considera_ramo_historico(self) -> None:
        """Vínculos históricos (origem_atual=False) também são resolvidos."""
        seed_alunos()
        self._matricula(998877, origem_atual=False)
        self._vinculo(998877, 12345, 1, date(2026, 2, 1), origem_atual=False)
        self.assertEqual(self._obter(), [12345])

    def test_matricula_nas_duas_fontes_considera_vinculo_historico(
        self,
    ) -> None:
        """Matrícula das duas fontes resolve o vínculo histórico ativo.

        A matrícula materializada como corrente (origem_atual=True) mas
        também presente na fonte histórica deve ter o vínculo histórico
        ativo considerado, mesmo com o vínculo corrente inativo.
        """
        seed_alunos()
        self._matricula(998877, origem_historica=True)
        self._vinculo(998877, 12345, 3, date(2026, 2, 27))
        self._vinculo(
            998877,
            12345,
            1,
            date(2025, 12, 15),
            sequencia=2,
            origem_atual=False,
        )
        self.assertEqual(self._obter(), [12345])

    def test_matricula_fora_da_fonte_historica_ignora_vinculo_historico(
        self,
    ) -> None:
        """Sem presença na fonte histórica, o vínculo histórico não conta."""
        seed_alunos()
        self._matricula(998877)
        self._vinculo(998877, 12345, 14, date(2026, 2, 9))
        self._vinculo(
            998877,
            12345,
            1,
            date(2025, 12, 15),
            sequencia=2,
            origem_atual=False,
        )
        self.assertEqual(self._obter(), [])

    def test_ignora_turma_de_outro_ano_letivo(self) -> None:
        """Turma de ano letivo diferente não entra no resultado."""
        seed_alunos()
        self._matricula(998877)
        self._vinculo(
            998877, 12345, 1, date(2026, 2, 1), ano_letivo_turma=2025
        )
        self.assertEqual(self._obter(), [])

    def test_data_referencia_customizada(self) -> None:
        """A data de referência informada altera o filtro ativa/inativa."""
        seed_alunos()
        self._matricula(998877)
        self._vinculo(998877, 12345, 2, date(2026, 5, 1))
        self.assertEqual(
            self._obter(data_referencia=date(2026, 4, 1)), [12345]
        )
        self.assertEqual(self._obter(data_referencia=date(2026, 6, 1)), [])

    def test_resolve_ultima_situacao_pela_data_com_data_hora_nula(
        self,
    ) -> None:
        """A última situação é a de maior data, mesmo com data_hora nula.

        Regressão: a linha mais recente por data (transferência) tem
        data_hora nula e a linha antiga (ativa) tem data_hora preenchida.
        A resolução deve eleger a transferência (inativa, no passado) e
        excluir a turma — antes, a ordenação por data_hora elegia a linha
        antiga ativa e incluía a turma indevidamente.
        """
        seed_alunos()
        self._matricula(998877)
        MatriculaTurma.objects.create(
            codigo_matricula=998877,
            codigo_turma=5555,
            data_situacao_aluno=date(2026, 5, 1),
            data_situacao_aluno_data_hora=None,
            codigo_situacao_aluno=3,
            codigo_tipo_turma=1,
            sequencia=2,
            origem_atual=True,
            ano_letivo_turma=2026,
        )
        MatriculaTurma.objects.create(
            codigo_matricula=998877,
            codigo_turma=5555,
            data_situacao_aluno=date(2026, 2, 1),
            data_situacao_aluno_data_hora=datetime(
                2026, 2, 1, 10, 0, tzinfo=UTC
            ),
            codigo_situacao_aluno=1,
            codigo_tipo_turma=1,
            sequencia=1,
            origem_atual=True,
            ano_letivo_turma=2026,
        )
        self.assertEqual(self._obter(), [])

    def test_aluno_sem_matriculas_retorna_vazio(self) -> None:
        """Aluno sem matrículas recebe lista vazia."""
        seed_alunos()
        self.assertEqual(self._obter(), [])
