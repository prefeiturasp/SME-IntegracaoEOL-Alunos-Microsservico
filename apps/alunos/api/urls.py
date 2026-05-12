"""Rotas da API do domínio Alunos.

Os paths replicam os contratos dos endpoints legados do
SME-Pedagogico-API:

    AlunoController         → /api/alunos/...
    MatriculaController     → /api/matriculas/...
    EscolaController (E05/E24) → /api/escolas/...
"""

from django.urls import path

from apps.alunos.api.views import (
    AlunosAtivosPeriodoTurmaView,
    AlunosAtivosTurmaView,
    AlunosPorCodigosEAnoView,
    AlunosPorCodigosView,
    AutocompleteAlunosAtivosView,
    AutocompleteAlunosUeView,
    BuscarAlunosDaUeView,
    BuscaTurmasDoAlunoPorSituacaoMatriculaView,
    BuscaTurmasDoAlunoView,
    DadosAcompanhamentoEscolarView,
    DadosResponsavelResumidoView,
    DadosResponsavelView,
    FiliacaoAlunoView,
    InformacoesAlunosTurmaView,
    InformacoesAlunoView,
    MatriculasAlunoEscolaView,
    MatriculasAnoAtualView,
    MatriculasAnosAnterioresView,
    NecessidadesEspeciaisAlunoView,
    QuantidadeAlunosPorTurmaEscolaView,
    QuantidadeMatriculadosPorAnoCCView,
    QuantidadeMatriculadosView,
    ResponsaveisDreUeTurmaView,
    ResponsavelAlunoView,
    TotalAlunosAtivosPorPeriodoView,
    TotalMatriculasPorTurnoDreView,
    TotalMatriculasPorTurnoUeView,
)

urlpatterns = [
    # ------------------------------------------------------------------
    # AlunoController do legado → /api/alunos/...
    # ------------------------------------------------------------------
    # A01
    path(
        "<str:codigo_aluno>/turmas/",
        BuscaTurmasDoAlunoView.as_view(),
        name="busca-turmas-do-aluno",
    ),
    # A02
    path(
        "<str:codigo_aluno>/turmas/anos_letivos/<str:ano_letivo>/"
        "historico/<str:historico>/filtrar-situacao/<str:filtrar_situacao>/"
        "tipo-turma/<str:tipo_turma>",
        BuscaTurmasDoAlunoView.as_view(),
        name="busca-turmas-do-aluno-com-filtros",
    ),
    # A03
    path(
        "<str:codigo_aluno>/turmas/anos_letivos/<str:ano_letivo>/"
        "matricula_turma/<str:filtrar_situacao_matricula>/"
        "tipo_turma/<str:tipo_turma>",
        BuscaTurmasDoAlunoPorSituacaoMatriculaView.as_view(),
        name="busca-turmas-do-aluno-por-situacao-matricula",
    ),
    # A04
    path(
        "ues/<str:codigo_ue>/anos_letivos/<str:ano_letivo>",
        BuscarAlunosDaUeView.as_view(),
        name="buscar-alunos-da-ue",
    ),
    # A05
    path(
        "ues/<str:codigo_ue>/anos_letivos/<str:ano_letivo>/autocomplete",
        AutocompleteAlunosUeView.as_view(),
        name="autocomplete-alunos-ue",
    ),
    # A06
    path(
        "ues/<str:ue_codigo>/autocomplete/ativos",
        AutocompleteAlunosAtivosView.as_view(),
        name="autocomplete-alunos-ativos",
    ),
    # A07
    path(
        "ativos/anos/<str:ano_turma>/anos-letivos/<str:ano_letivo>/"
        "inicio/<str:data_inicio>/fim/<str:data_fim>",
        TotalAlunosAtivosPorPeriodoView.as_view(),
        name="total-alunos-ativos-por-periodo",
    ),
    # A08
    path(
        "turmas/<str:codigo_turma>/ativos/<str:data_referencia_fim>",
        AlunosAtivosPeriodoTurmaView.as_view(),
        name="alunos-ativos-periodo-turma",
    ),
    # A09
    path(
        "turmas/<str:codigo_turma>/ativos",
        AlunosAtivosTurmaView.as_view(),
        name="alunos-ativos-turma",
    ),
    # A10
    path(
        "<str:codigo_aluno>/necessidades-especiais",
        NecessidadesEspeciaisAlunoView.as_view(),
        name="necessidades-especiais-aluno",
    ),
    # A11
    path(
        "ano_letivo/<str:ano_letivo>/alunos",
        AlunosPorCodigosEAnoView.as_view(),
        name="alunos-por-codigos-e-ano",
    ),
    # A12
    path(
        "alunos",
        AlunosPorCodigosView.as_view(),
        name="alunos-por-codigos",
    ),
    # A13
    path(
        "<str:codigo_aluno>/informacoes",
        InformacoesAlunoView.as_view(),
        name="informacoes-aluno",
    ),
    # A14
    path(
        "<str:codigo_turma>/turma/informacoes",
        InformacoesAlunosTurmaView.as_view(),
        name="informacoes-alunos-turma",
    ),
    # A15
    path(
        "ano-letivo/<str:ano_letivo>/matriculados",
        QuantidadeMatriculadosPorAnoCCView.as_view(),
        name="quantidade-matriculados-cc",
    ),
    # A16
    path(
        "ano-letivo/<str:ano_letivo>/matriculados/quantidade",
        QuantidadeMatriculadosView.as_view(),
        name="quantidade-matriculados",
    ),
    # A18
    path(
        "dados-acompanhamento-escolar",
        DadosAcompanhamentoEscolarView.as_view(),
        name="dados-acompanhamento-escolar",
    ),
    # A19
    path(
        "responsaveis",
        ResponsaveisDreUeTurmaView.as_view(),
        name="responsaveis-dre-ue-turma",
    ),
    # A20
    path(
        "responsaveis/<str:cpf_responsavel>",
        DadosResponsavelView.as_view(),
        name="dados-responsavel",
    ),
    # A21
    path(
        "responsaveis/<str:cpf_responsavel>/resumido",
        DadosResponsavelResumidoView.as_view(),
        name="dados-responsavel-resumido",
    ),
    # A27 — deve vir antes de A22/A23 para não ser
    # capturado pelo <str:cpf_responsavel>
    path(
        "<str:codigo_aluno>/responsaveis/filiacao",
        FiliacaoAlunoView.as_view(),
        name="filiacao-aluno",
    ),
    # A22 (PUT) e A23 (POST) — mesmo path, métodos diferentes
    path(
        "<str:codigo_aluno>/responsaveis/<str:cpf_responsavel>",
        ResponsavelAlunoView.as_view(),
        name="responsavel-aluno",
    ),
    # ------------------------------------------------------------------
    # MatriculaController do legado → /api/matriculas/...
    # ------------------------------------------------------------------
    # M01
    path(
        "matriculas",
        MatriculasAnoAtualView.as_view(),
        name="matriculas-ano-atual",
    ),
    # M02
    path(
        "matriculas/anos-anteriores",
        MatriculasAnosAnterioresView.as_view(),
        name="matriculas-anos-anteriores",
    ),
    # M03
    path(
        "matriculas/escolas/<str:ue_codigo>/quantidades",
        TotalMatriculasPorTurnoUeView.as_view(),
        name="matriculas-quantidades-ue",
    ),
    # M04
    path(
        "matriculas/escolas/dre/<str:dre_codigo>/quantidades",
        TotalMatriculasPorTurnoDreView.as_view(),
        name="matriculas-quantidades-dre",
    ),
    # ------------------------------------------------------------------
    # EscolaController (E05/E24) do legado → /api/escolas/...
    # ------------------------------------------------------------------
    # E05
    path(
        "escolas/<str:codigo_escola>/alunos/quantidade",
        QuantidadeAlunosPorTurmaEscolaView.as_view(),
        name="quantidade-alunos-por-turma-escola",
    ),
    # E24
    path(
        "escolas/<str:codigo_escola>/aluno/<str:codigo_aluno>/matriculas",
        MatriculasAlunoEscolaView.as_view(),
        name="matriculas-aluno-escola",
    ),
]
