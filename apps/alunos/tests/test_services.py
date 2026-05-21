"""Testes das funções de service do app alunos."""

from __future__ import annotations

from datetime import UTC, date, datetime
from unittest.mock import patch

from django.test import TestCase

from apps.alunos import services
from apps.alunos.tests.helpers import (
    seed_alunos,
    seed_matriculas,
    seed_necessidades,
    seed_responsaveis,
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
        seed_matriculas()
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

    def test_calcular_idade_none(self) -> None:
        """Verifica que data de nascimento None resulta em None."""
        from apps.alunos.services import _calcular_idade

        self.assertIsNone(_calcular_idade(None))

    def test_calcular_idade_aniversario_nao_completo(self) -> None:
        """Verifica que aniversário não atingido subtrai um ano."""
        from apps.alunos.services import _calcular_idade

        self.assertEqual(
            _calcular_idade(date(2010, 12, 31), referencia=date(2026, 6, 1)),
            15,
        )

    def test_calcular_idade_com_datetime(self) -> None:
        """Verifica que datetime é aceito como data de nascimento."""
        from apps.alunos.services import _calcular_idade

        self.assertEqual(
            _calcular_idade(datetime(2010, 1, 1), referencia=date(2026, 6, 1)),
            16,
        )


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
