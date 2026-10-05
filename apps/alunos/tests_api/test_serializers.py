"""Testes de campos retornados pelos serializers da API de alunos."""

from __future__ import annotations

from django.test import SimpleTestCase

from apps.alunos.api.serializers import (
    AlunoAtivoDataAulaSerializer,
    AlunoAtivoTurmaSerializer,
    AlunoAutocompleteSerializer,
    AlunoDaUeSerializer,
    AtualizarResponsavelBuscaAtivaRequestSerializer,
    CadastrarResponsavelRequestSerializer,
    ConsolidacaoMatriculaSerializer,
    DadosAcompanhamentoEscolarContratoSerializer,
    DadosAcompanhamentoEscolarSerializer,
    DadosResponsavelFiliacaoSerializer,
    DadosResponsavelResumidoSerializer,
    DadosResponsavelSerializer,
    EnderecoFiliacaoSerializer,
    InformacoesAlunoSerializer,
    InformacoesAlunoTurmaSerializer,
    MatriculaEscolaAlunoSerializer,
    NecessidadeEspecialSerializer,
    QuantidadeMatriculadosCCContratoSerializer,
    QuantidadeMatriculadosCCSerializer,
    QuantidadeMatriculadosContratoSerializer,
    QuantidadeMatriculadosSerializer,
    ResponsavelTurmaSerializer,
    TotalAlunosAtivosPeriodoSerializer,
    TurmaDoAlunoSerializer,
)


class SerializersFieldsTestCase(SimpleTestCase):
    """Valida os campos expostos por cada serializer."""

    def test_turma_do_aluno_serializer(self) -> None:
        serializer = TurmaDoAlunoSerializer()

        self.assertEqual(
            list(serializer.fields),
            [
                "codigo_aluno",
                "ano_letivo",
                "nome_aluno",
                "nome_social_aluno",
                "codigo_situacao_matricula",
                "situacao_matricula",
                "data_situacao",
                "data_nascimento",
                "documento_cpf",
                "data_matricula",
                "numero_aluno_chamada",
                "codigo_turma",
                "data_atualizacao_contato",
                "nome_responsavel",
                "tipo_responsavel",
                "ddd_celular",
                "numero_celular",
                "codigo_escola",
                "codigo_tipo_turma",
                "data_atualizacao_tabela",
            ],
        )

    def test_aluno_da_ue_serializer(self) -> None:
        serializer = AlunoDaUeSerializer()

        self.assertEqual(
            list(serializer.fields),
            [
                "codigo_aluno",
                "tipo_turno",
                "ano_letivo",
                "nome_aluno",
                "nome_social_aluno",
                "codigo_situacao_matricula",
                "situacao_matricula",
                "data_situacao",
                "data_nascimento",
                "numero_aluno_chamada",
                "codigo_turma",
                "nome_responsavel",
                "tipo_responsavel",
                "ddd_celular",
                "numero_celular",
                "data_atualizacao_contato",
                "codigo_tipo_turma",
                "turma_nome",
                "etapa_ensino",
                "ciclo_ensino",
                "desc_etapa_ensino",
                "desc_ciclo_ensino",
                "data_atualizacao_tabela",
            ],
        )

    def test_aluno_autocomplete_serializer(self) -> None:
        serializer = AlunoAutocompleteSerializer()

        self.assertEqual(
            list(serializer.fields),
            [
                "codigo_aluno",
                "nome_aluno",
                "nome_social_aluno",
                "codigo_turma",
                "numero_aluno_chamada",
                "turma",
                "modalidade",
            ],
        )

    def test_aluno_ativo_turma_serializer(self) -> None:
        serializer = AlunoAtivoTurmaSerializer()

        self.assertEqual(
            list(serializer.fields),
            [
                "codigo_aluno",
                "nome_aluno",
                "nome_social_aluno",
                "data_nascimento",
                "codigo_situacao_matricula",
                "situacao_matricula",
                "data_situacao",
                "numero_aluno_chamada",
                "possui_deficiencia",
                "codigo_matricula",
                "codigo_turma",
                "codigo_escola",
                "ano_letivo",
            ],
        )

    def test_aluno_ativo_data_aula_serializer(self) -> None:
        serializer = AlunoAtivoDataAulaSerializer()

        self.assertEqual(
            list(serializer.fields),
            [
                "codigo_aluno",
                "nome_aluno",
                "nome_social_aluno",
                "data_nascimento",
                "codigo_situacao_matricula",
                "situacao_matricula",
                "data_situacao",
                "numero_aluno_chamada",
                "possui_deficiencia",
                "codigo_matricula",
                "codigo_turma",
                "codigo_escola",
                "ano_letivo",
                "data_matricula",
                "nome_responsavel",
                "tipo_responsavel",
                "celular_responsavel",
                "data_atualizacao_contato",
                "sequencia",
                "codigo_dre",
            ],
        )

    def test_necessidade_especial_serializer(self) -> None:
        serializer = NecessidadeEspecialSerializer()

        self.assertEqual(
            list(serializer.fields),
            [
                "codigo_aluno",
                "tipo_necessidade_especial",
                "descricao_necessidade_especial",
                "tipo_recurso",
                "descricao_recurso",
            ],
        )

    def test_informacoes_aluno_serializer(self) -> None:
        serializer = InformacoesAlunoSerializer()

        self.assertEqual(
            list(serializer.fields),
            [
                "codigo_aluno",
                "nome_aluno",
                "nome_social_aluno",
                "nome_mae",
                "sexo",
                "nacionalidade",
                "raca_cor",
                "nis",
                "cpf",
                "cns",
                "endereco",
                "data_nascimento",
                "possui_deficiencia",
            ],
        )

    def test_informacoes_aluno_turma_serializer(self) -> None:
        serializer = InformacoesAlunoTurmaSerializer()

        self.assertEqual(
            list(serializer.fields),
            [
                "numero_aluno_chamada",
                "numero_chamada",
                "codigo_aluno",
                "nome_aluno",
                "nome_social_aluno",
                "sexo",
                "raca_cor",
                "raca",
                "codigo_raca",
            ],
        )

    def test_quantidade_matriculados_cc_serializer(self) -> None:
        serializer = QuantidadeMatriculadosCCSerializer()

        self.assertEqual(
            list(serializer.fields),
            [
                "codigo_turma",
                "quantidade",
                "ordem",
            ],
        )

    def test_quantidade_matriculados_serializer(self) -> None:
        serializer = QuantidadeMatriculadosSerializer()

        self.assertEqual(
            list(serializer.fields),
            [
                "quantidade",
                "ordem",
                "codigo_turma",
                "ue_codigo",
            ],
        )

    def test_dados_acompanhamento_escolar_serializer(self) -> None:
        serializer = DadosAcompanhamentoEscolarSerializer()

        self.assertEqual(
            list(serializer.fields),
            [
                "codigo_eol",
                "nome_responsavel",
                "cpf_responsavel",
                "nome",
                "nome_social",
                "codigo_escola",
                "tipo_responsavel",
                "codigo_turma",
                "situacao_matricula",
                "data_nascimento",
                "data_situacao_matricula",
                "ano_letivo",
            ],
        )

    def test_quantidade_matriculados_cc_contrato_serializer(self) -> None:
        serializer = QuantidadeMatriculadosCCContratoSerializer()

        self.assertEqual(
            list(serializer.fields),
            [
                "componente_curricular_id",
                "quantidade",
                "ordem",
                "modalidade",
                "ano",
                "turma",
            ],
        )

    def test_quantidade_matriculados_contrato_serializer(self) -> None:
        serializer = QuantidadeMatriculadosContratoSerializer()

        self.assertEqual(
            list(serializer.fields),
            [
                "quantidade",
                "ordem",
                "modalidade",
                "ano",
                "turma",
                "dre_codigo",
                "ue_codigo",
            ],
        )

    def test_dados_acompanhamento_escolar_contrato_serializer(self) -> None:
        serializer = DadosAcompanhamentoEscolarContratoSerializer()

        self.assertEqual(
            list(serializer.fields),
            [
                "codigo_eol",
                "nome_responsavel",
                "cpf_responsavel",
                "nome",
                "nome_social",
                "codigo_escola",
                "codigo_dre",
                "escola",
                "tipo_responsavel",
                "codigo_tipo_escola",
                "descricao_tipo_escola",
                "sigla_dre",
                "codigo_turma",
                "turma",
                "situacao_matricula",
                "data_nascimento",
                "data_situacao_matricula",
                "codigo_ciclo_ensino",
                "codigo_etapa_ensino",
                "serie_resumida",
            ],
        )

    def test_responsavel_turma_serializer(self) -> None:
        serializer = ResponsavelTurmaSerializer()

        self.assertEqual(
            list(serializer.fields),
            [
                "codigo_dre",
                "dre",
                "codigo_ue",
                "ue",
                "codigo_turma",
                "turma",
                "cpf_responsavel",
                "codigo_aluno",
                "codigo_tipo_escola",
                "codigo_etapa_ensino",
                "codigo_ciclo_ensino",
                "serie_resumida",
                "codigo_modalidade_turma",
                "tem_app_instalado",
            ],
        )

    def test_dados_responsavel_serializer(self) -> None:
        serializer = DadosResponsavelSerializer()

        self.assertEqual(
            list(serializer.fields),
            [
                "codigo_responsavel",
                "cpf",
                "email",
                "nome",
                "tipo_responsavel",
                "nome_aluno",
                "nome_social_aluno",
                "data_nascimento_aluno",
                "codigo_aluno",
                "ddd_celular",
                "numero_celular",
                "autoriza_sms",
                "logradouro",
                "cep",
                "data_fim_vinculo",
            ],
        )

    def test_dados_responsavel_resumido_serializer(self) -> None:
        serializer = DadosResponsavelResumidoSerializer()

        self.assertEqual(
            list(serializer.fields),
            [
                "id",
                "cpf",
                "email",
                "nome",
                "tipo_responsavel",
                "data_nascimento",
                "data_atualizacao",
                "nome_mae",
                "ddd_celular",
                "numero_celular",
                "codigo_aluno",
            ],
        )

    def test_endereco_filiacao_serializer(self) -> None:
        serializer = EnderecoFiliacaoSerializer()

        self.assertEqual(
            list(serializer.fields),
            [
                "id",
                "nro",
                "complemento",
                "bairro",
                "cep",
                "nome_municipio",
                "sigla_uf",
                "tipo_logradouro",
                "logradouro",
            ],
        )

    def test_dados_responsavel_filiacao_serializer(self) -> None:
        serializer = DadosResponsavelFiliacaoSerializer()

        self.assertEqual(
            list(serializer.fields),
            [
                "nome_responsavel",
                "cpf",
                "email",
                "ddd_celular",
                "numero_celular",
                "ddd_residencial",
                "numero_residencial",
                "ddd_comercial",
                "numero_comercial",
                "tipo_responsavel",
                "endereco",
            ],
        )

    def test_total_alunos_ativos_periodo_serializer(self) -> None:
        serializer = TotalAlunosAtivosPeriodoSerializer()

        self.assertEqual(
            list(serializer.fields),
            [
                "quantidade",
            ],
        )

    def test_consolidacao_matricula_serializer(self) -> None:
        serializer = ConsolidacaoMatriculaSerializer()

        self.assertEqual(
            list(serializer.fields),
            [
                "turma_codigo",
                "quantidade",
            ],
        )

    def test_matricula_escola_aluno_serializer(self) -> None:
        serializer = MatriculaEscolaAlunoSerializer()

        self.assertEqual(
            list(serializer.fields),
            [
                "codigo_aluno",
                "nome_aluno",
                "nome_social_aluno",
                "codigo_situacao_matricula",
                "situacao_matricula",
                "data_situacao",
                "codigo_turma",
                "codigo_matricula",
                "ano_letivo",
            ],
        )

    def test_atualizar_responsavel_busca_ativa_request_serializer(
        self,
    ) -> None:
        serializer = AtualizarResponsavelBuscaAtivaRequestSerializer()

        self.assertEqual(
            list(serializer.fields),
            [
                "codigo_aluno",
                "cpf",
                "email",
                "ddd_celular",
                "numero_celular",
                "ddd_residencial",
                "numero_residencial",
                "ddd_comercial",
                "numero_comercial",
            ],
        )

    def test_cadastrar_responsavel_request_serializer(self) -> None:
        serializer = CadastrarResponsavelRequestSerializer()

        self.assertEqual(
            list(serializer.fields),
            [
                "cpf",
                "email",
                "nome",
                "tipo_responsavel",
                "ddd_celular",
                "numero_celular",
                "codigo_aluno",
            ],
        )
