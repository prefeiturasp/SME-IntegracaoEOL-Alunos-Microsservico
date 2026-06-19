"""Testes das funções de service do app alunos."""

from __future__ import annotations

from datetime import UTC, date, datetime
from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.alunos import services
from apps.alunos.models import Matricula, MatriculaTurma, ResponsavelAluno
from apps.alunos.tests.helpers import (
    seed_alunos,
    seed_matriculas,
    seed_necessidades,
    seed_responsaveis,
    seed_turma_data_aula,
)


class TurmasDoAlunoTestCase(TestCase):
    """Valida a busca de turmas do aluno."""

    def test_a01_retorna_lista(self) -> None:
        """Verifica os campos retornados para o aluno no ano corrente."""
        seed_matriculas()
        seed_responsaveis()
        with patch(
            "django.utils.timezone.now",
            return_value=datetime(2026, 6, 1, tzinfo=UTC),
        ):
            dados = services.buscar_turmas_do_aluno(codigo_aluno=1234567)
        self.assertEqual(len(dados), 1)
        d = dados[0]
        self.assertEqual(d.codigo_aluno, 1234567)
        self.assertEqual(d.codigo_turma, 12345)
        self.assertEqual(d.codigo_situacao_matricula, 1)
        self.assertEqual(d.nome_aluno, "JOAO DA SILVA")
        self.assertEqual(d.numero_aluno_chamada, "12")
        self.assertEqual(
            d.data_atualizacao_contato,
            datetime(2026, 1, 15, 14, 46, 50, tzinfo=UTC),
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


class A04AlunosDaUeTestCase(TestCase):
    """Valida a busca de alunos por UE/ano letivo."""

    def test_filtra_por_codigo_eol(self) -> None:
        """Verifica filtro pelo código EOL exato."""
        seed_matriculas()
        dados = services.buscar_alunos_da_ue(
            codigo_ue="100001",
            ano_letivo=2026,
            codigo_eol="1234567",
        )
        self.assertEqual(len(dados), 1)
        self.assertEqual(dados[0].codigo_aluno, 1234567)

    def test_filtra_por_nome(self) -> None:
        """Verifica filtro por substring do nome."""
        seed_matriculas()
        dados = services.buscar_alunos_da_ue(
            codigo_ue="100001",
            ano_letivo=2026,
            nome_aluno="JOAO",
        )
        self.assertTrue(all("JOAO" in d.nome_aluno for d in dados))


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
        self.assertEqual(dados[0].codigo_aluno, 7654321)

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
        self.assertEqual(dados[0].codigo_turma, 12345)

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
        self.assertEqual(dados[0].codigo_turma, 44444)
        self.assertEqual(dados[0].turma, "9B")
        self.assertEqual(dados[0].modalidade, "EM")


class A07TotalAtivosTestCase(TestCase):
    """Valida a contagem de alunos ativos por período."""

    def test_filtra_por_periodo_e_ue(self) -> None:
        """Verifica a contagem restrita a UE e intervalo de datas."""
        seed_matriculas()
        total = services.obter_total_alunos_ativos_periodo(
            ano_turma="5",
            ano_letivo=2026,
            data_inicio=date(2026, 1, 1),
            data_fim=date(2026, 12, 31),
            ue_id="100001",
        )
        self.assertEqual(total.quantidade, 2)


class A08A09AlunosTurmaTestCase(TestCase):
    """Valida a listagem de alunos ativos por turma."""

    def test_a09_retorna_alunos_da_turma(self) -> None:
        """Verifica os alunos retornados para a turma informada."""
        seed_matriculas()
        seed_responsaveis()
        seed_necessidades()
        dados = services.obter_alunos_ativos_por_turma(codigo_turma=12345)
        self.assertEqual(len(dados), 1)
        self.assertEqual(dados[0].codigo_aluno, 1234567)

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
            dados[0].descricao_necessidade_especial, "Deficiência Visual"
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
        self.assertEqual(info.nome_aluno, "JOAO DA SILVA")
        self.assertEqual(info.nis, "123456789")

    def test_a13_inexistente(self) -> None:
        """Verifica que aluno inexistente retorna None."""
        info = services.obter_informacoes_aluno(codigo_aluno=999)
        self.assertIsNone(info)

    def test_a14_lista_alunos_da_turma(self) -> None:
        """Verifica os alunos retornados para a turma informada."""
        seed_matriculas()
        dados = services.obter_informacoes_alunos_da_turma(codigo_turma=12345)
        self.assertEqual(len(dados), 1)
        self.assertEqual(dados[0].codigo_aluno, 1234567)


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
            self.assertEqual(d.ue_codigo, "100001")


class A18AcompanhamentoTestCase(TestCase):
    """Valida a consulta de dados de acompanhamento escolar."""

    def test_filtra_por_turma(self) -> None:
        """Verifica o filtro por código de turma e responsável vigente."""
        seed_matriculas()
        seed_responsaveis()
        dados = services.obter_dados_acompanhamento_escolar(
            codigo_ue="100001",
            ano_letivo=2026,
            turma_codigo="12345",
        )
        self.assertEqual(len(dados), 1)
        self.assertEqual(dados[0].codigo_eol, 1234567)
        self.assertEqual(dados[0].nome_responsavel, "Responsavel Exemplo")


class A19A20A21ResponsaveisTestCase(TestCase):
    """Valida as consultas de responsáveis (lista, completo e resumido)."""

    def test_a19_lista_responsaveis_da_ue(self) -> None:
        """Verifica a listagem de responsáveis vigentes por UE/ano."""
        seed_matriculas()
        seed_responsaveis()
        dados = services.obter_responsaveis_dre_ue_turma(
            codigo_ue="100001", ano_letivo=2026
        )
        self.assertEqual(len(dados), 1)
        self.assertEqual(dados[0].codigo_aluno, 1234567)

    def test_a20_dados_completos(self) -> None:
        """Verifica o retorno completo dos dados do responsável."""
        seed_alunos()
        seed_responsaveis()
        dados = services.obter_dados_responsavel(cpf_responsavel="12345678901")
        self.assertEqual(len(dados), 1)
        self.assertEqual(dados[0].nome, "Responsavel Exemplo")

    def test_a21_resumido(self) -> None:
        """Verifica o retorno resumido dos dados do responsável."""
        seed_alunos()
        seed_responsaveis()
        dado = services.obter_dados_responsavel_resumido(
            cpf_responsavel="12345678901"
        )
        self.assertIsNotNone(dado)
        assert dado is not None
        self.assertEqual(dado.cpf, "12345678901")
        self.assertEqual(dado.data_nascimento, date(1980, 5, 20))
        self.assertEqual(dado.nome_mae, "Mae do Responsavel")

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
        self.assertEqual(dado.id, 5501)


class A22A23EscritaTestCase(TestCase):
    """Valida as escritas de responsável (busca ativa e cadastro)."""

    def test_a22_atualiza_telefones(self) -> None:
        """Verifica a atualização de telefones pelo fluxo de busca ativa."""
        seed_alunos()
        seed_responsaveis()
        resumo = services.atualizar_dados_responsavel_busca_ativa(
            codigo_aluno=1234567,
            cpf_responsavel="12345678901",
            ddd_celular="11",
            numero_celular="999998888",
        )
        self.assertEqual(resumo.numero_celular, "999998888")

    def test_a23_atualiza_responsavel_existente(self) -> None:
        """Verifica que o cadastro atualiza um vínculo existente."""
        seed_alunos()
        seed_responsaveis()
        resumo = services.cadastrar_dados_responsavel(
            codigo_aluno=1234567,
            cpf_responsavel="12345678901",
            nome="Responsavel Atualizado",
            email="atualizado@sme.com.br",
            tipo_responsavel=2,
            ddd_celular="11",
            numero_celular="911112222",
        )
        self.assertEqual(resumo.nome, "Responsavel Atualizado")
        self.assertEqual(resumo.tipo_responsavel, 2)


class A27FiliacaoTestCase(TestCase):
    """Valida que a filiação reaproveita o shape de informações do aluno."""

    def test_retorna_mesmo_shape_de_a13(self) -> None:
        """Verifica que a filiação devolve o mesmo DTO de informações."""
        seed_alunos()
        dado = services.obter_dados_responsavel_filiacao(codigo_aluno=1234567)
        self.assertIsNotNone(dado)
        assert dado is not None
        self.assertEqual(dado.codigo_aluno, 1234567)


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
        """Verifica a consolidação de anos sem matrículas."""
        seed_matriculas()
        dados = services.obter_matriculas_anos_anteriores(
            ano_letivo=2025, ue_codigo="100001"
        )
        self.assertEqual(dados, [])

    def test_e05(self) -> None:
        """Verifica a consolidação por turma da escola informada."""
        seed_matriculas()
        dados = services.obter_quantidade_alunos_por_turma_da_escola(
            codigo_escola="100001"
        )
        self.assertEqual(len(dados), 2)


class M03M04OutOfScopeTestCase(TestCase):
    """Valida que endpoints fora de escopo retornam lista vazia."""

    def test_m03_retorna_vazio(self) -> None:
        """Verifica que o total por turno da UE retorna lista vazia."""
        self.assertEqual(
            services.obter_total_matriculas_por_turno_ue(ue_codigo="100001"),
            [],
        )

    def test_m04_retorna_vazio(self) -> None:
        """Verifica que o total por turno da DRE retorna lista vazia."""
        self.assertEqual(
            services.obter_total_matriculas_por_turno_dre(dre_codigo="100001"),
            [],
        )


class E24MatriculasAlunoEscolaTestCase(TestCase):
    """Valida a consulta de matrículas do aluno em uma escola."""

    def test_retorna_matriculas_do_aluno(self) -> None:
        """Verifica as matrículas retornadas para aluno/escola existentes."""
        seed_matriculas()
        dados = services.obter_matriculas_aluno_na_escola(
            codigo_escola="100001", codigo_aluno=1234567
        )
        self.assertEqual(len(dados), 1)
        self.assertEqual(dados[0].codigo_matricula, 998877)
        self.assertEqual(dados[0].ano_letivo, 2026)

    def test_aluno_inexistente_retorna_vazio(self) -> None:
        """Verifica que aluno sem matrículas na escola gera saída vazia."""
        dados = services.obter_matriculas_aluno_na_escola(
            codigo_escola="100001", codigo_aluno=9999999
        )
        self.assertEqual(dados, [])


class HelpersInternosTestCase(TestCase):
    """Testes para os helpers internos."""

    def test_alunos_indexados_vazio(self) -> None:
        """Verifica que entrada vazia em _alunos_indexados gera dict vazio."""
        from apps.alunos.services import _alunos_indexados

        self.assertEqual(_alunos_indexados([]), {})

    def test_matricula_turma_por_matricula_vazio(self) -> None:
        """Verifica que entrada vazia em matrícula da turma gera dict vazio."""
        from apps.alunos.services import _matricula_turma_por_matricula

        self.assertEqual(_matricula_turma_por_matricula([]), {})

    def test_matriculas_por_codigos_turma_vazio(self) -> None:
        """Verifica que entrada vazia por codigo_turma gera lista vazia."""
        from apps.alunos.services import _matriculas_por_codigos_turma

        self.assertEqual(_matriculas_por_codigos_turma([]), [])

    def test_matriculas_por_codigos_turma_sem_match(self) -> None:
        """Verifica que turmas inexistentes geram lista vazia."""
        from apps.alunos.services import _matriculas_por_codigos_turma

        self.assertEqual(_matriculas_por_codigos_turma([99999999]), [])

    def test_responsavel_principal_inexistente(self) -> None:
        """Verifica que aluno sem responsável retorna None."""
        from apps.alunos.services import _responsavel_principal

        self.assertIsNone(_responsavel_principal(99999999))


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
        self.assertEqual(dados[0].codigo_turma, 12345)

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

    @patch("apps.alunos.services._consultar_turmas_do_aluno")
    def test_default_exclui_programa_e_filtra_situacao(
        self, mock_consultar: MagicMock
    ) -> None:
        """Verifica que os defaults preservam o comportamento padrão."""
        mock_consultar.return_value = []

        services.buscar_turmas_do_aluno(codigo_aluno=1234567)

        mock_consultar.assert_called_once_with(
            codigo_aluno=1234567, tipo_turma=True, filtrar_situacao=True
        )

    @patch("apps.alunos.services._consultar_turmas_do_aluno")
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

    def test_retorna_alunos_dedup_por_aluno(self) -> None:
        """Verifica dedup por aluno e campos enriquecidos do contrato."""
        codigo_turma = seed_turma_data_aula()
        dados = services.obter_alunos_ativos_turma_por_data_aula(
            codigo_turma=codigo_turma,
            data_aula=datetime(2026, 6, 1, tzinfo=UTC),
        )
        self.assertEqual(len(dados), 2)
        por_aluno = {d.codigo_aluno: d for d in dados}
        joao = por_aluno[1234567]
        self.assertEqual(joao.nome_aluno, "JOAO DA SILVA")
        self.assertEqual(joao.codigo_turma, codigo_turma)
        self.assertEqual(joao.codigo_escola, "100001")
        self.assertEqual(joao.codigo_dre, "108800")
        self.assertEqual(joao.ano_letivo, 2026)
        self.assertEqual(joao.sequencia, 1)
        self.assertEqual(joao.numero_aluno_chamada, "12")
        self.assertEqual(
            joao.data_situacao, datetime(2026, 2, 10, 14, 0, tzinfo=UTC)
        )
        self.assertEqual(
            joao.data_matricula, datetime(2026, 2, 10, 14, 0, tzinfo=UTC)
        )
        self.assertEqual(joao.nome_responsavel, "Responsavel Data Aula")
        self.assertEqual(joao.tipo_responsavel, 1)
        self.assertEqual(joao.celular_responsavel, "11988887777")
        self.assertEqual(
            joao.data_atualizacao_contato,
            datetime(2026, 1, 15, 14, 46, 50, tzinfo=UTC),
        )

    def test_aluno_sem_responsavel_tem_campos_nulos(self) -> None:
        """Verifica que aluno sem responsável retorna campos nulos."""
        codigo_turma = seed_turma_data_aula()
        dados = services.obter_alunos_ativos_turma_por_data_aula(
            codigo_turma=codigo_turma,
            data_aula=datetime(2026, 6, 1, tzinfo=UTC),
        )
        maria = {d.codigo_aluno: d for d in dados}[7654321]
        self.assertIsNone(maria.nome_responsavel)
        self.assertIsNone(maria.tipo_responsavel)
        self.assertIsNone(maria.celular_responsavel)
        self.assertIsNone(maria.data_atualizacao_contato)

    def test_filtra_data_situacao_posterior_a_data_aula(self) -> None:
        """Verifica que matrícula posterior à data de aula é excluída."""
        codigo_turma = seed_turma_data_aula()
        dados = services.obter_alunos_ativos_turma_por_data_aula(
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

        dados = services.obter_alunos_ativos_turma_por_data_aula(
            codigo_turma=codigo_turma,
            data_aula=datetime(2026, 2, 6, 8, 0, tzinfo=UTC),
        )

        maria = {d.codigo_aluno: d for d in dados}[7654321]
        self.assertEqual(maria.codigo_matricula, 700009)

    def test_turma_inexistente_retorna_vazio(self) -> None:
        """Verifica que turma sem alunos retorna lista vazia."""
        dados = services.obter_alunos_ativos_turma_por_data_aula(
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

        dados = services.obter_alunos_ativos_turma_por_data_aula(
            codigo_turma=codigo_turma,
            data_aula=datetime(2026, 6, 1, tzinfo=UTC),
        )

        joao = {d.codigo_aluno: d for d in dados}[1234567]
        self.assertEqual(joao.codigo_matricula, 700003)
        self.assertEqual(joao.codigo_situacao_matricula, 4)

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

        dados = services.obter_alunos_ativos_turma_por_data_aula(
            codigo_turma=codigo_turma,
            data_aula=datetime(2026, 6, 1, tzinfo=UTC),
        )

        joao = {d.codigo_aluno: d for d in dados}[1234567]
        self.assertEqual(joao.codigo_matricula, 700004)
        self.assertEqual(joao.numero_aluno_chamada, "20")
        self.assertEqual(joao.codigo_situacao_matricula, 14)
        self.assertEqual(joao.situacao_matricula, "Remanejado Saída")

    def test_data_matricula_usa_alocacao_original(self) -> None:
        """Verifica data_matricula da matricula-turma original (menor data)."""
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

        dados = services.obter_alunos_ativos_turma_por_data_aula(
            codigo_turma=codigo_turma,
            data_aula=datetime(2026, 6, 1, tzinfo=UTC),
        )

        joao = {d.codigo_aluno: d for d in dados}[1234567]
        self.assertEqual(joao.codigo_situacao_matricula, 14)
        self.assertEqual(
            joao.data_situacao, datetime(2026, 4, 20, 9, 0, tzinfo=UTC)
        )
        self.assertEqual(
            joao.data_matricula, datetime(2026, 2, 10, 14, 0, tzinfo=UTC)
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

        dados = services.obter_alunos_ativos_turma_por_data_aula(
            codigo_turma=codigo_turma,
            data_aula=datetime(2026, 6, 1, tzinfo=UTC),
        )

        joao = {d.codigo_aluno: d for d in dados}[1234567]
        self.assertEqual(joao.codigo_matricula, 700005)
        self.assertEqual(joao.numero_aluno_chamada, "20")

    def test_sem_n_mais_um(self) -> None:
        """Verifica que a consulta usa um número fixo de queries."""
        codigo_turma = seed_turma_data_aula()
        with self.assertNumQueries(4):
            services.obter_alunos_ativos_turma_por_data_aula(
                codigo_turma=codigo_turma,
                data_aula=datetime(2026, 6, 1, tzinfo=UTC),
            )

    def test_responsaveis_por_aluno_vazio(self) -> None:
        """Verifica que lista de códigos vazia não consulta o banco."""
        with self.assertNumQueries(0):
            resultado = services._responsaveis_por_aluno([])
        self.assertEqual(resultado, {})
