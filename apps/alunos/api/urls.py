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
    BuscaTurmasDoAlunoPorSituacaoMatriculaView,
    BuscaTurmasDoAlunoView,
    BuscarAlunosDaUeView,
    DadosAcompanhamentoEscolarView,
    DadosResponsavelResumidoView,
    DadosResponsavelView,
    FiliacaoAlunoView,
    InformacoesAlunoView,
    InformacoesAlunosTurmaView,
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
        "alunos/<str:codigoAluno>/turmas/",
        BuscaTurmasDoAlunoView.as_view(),
        name="busca-turmas-do-aluno",
    ),
    # A02
    path(
        "alunos/<str:codigoAluno>/turmas/anosLetivos/<str:anoLetivo>/"
        "historico/<str:historico>/filtrar-situacao/<str:filtrarSituacao>/"
        "tipo-turma/<str:tipoTurma>",
        BuscaTurmasDoAlunoView.as_view(),
        name="busca-turmas-do-aluno-com-filtros",
    ),
    # A03
    path(
        "alunos/<str:codigoAluno>/turmas/anosLetivos/<str:anoLetivo>/"
        "matriculaTurma/<str:filtrarSituacaoMatricula>/"
        "tipoTurma/<str:tipoTurma>",
        BuscaTurmasDoAlunoPorSituacaoMatriculaView.as_view(),
        name="busca-turmas-do-aluno-por-situacao-matricula",
    ),
    # A04
    path(
        "alunos/ues/<str:codigoUe>/anosLetivos/<str:anoLetivo>",
        BuscarAlunosDaUeView.as_view(),
        name="buscar-alunos-da-ue",
    ),
    # A05
    path(
        "alunos/ues/<str:codigoUe>/anosLetivos/<str:anoLetivo>/autocomplete",
        AutocompleteAlunosUeView.as_view(),
        name="autocomplete-alunos-ue",
    ),
    # A06
    path(
        "alunos/ues/<str:ueCodigo>/autocomplete/ativos",
        AutocompleteAlunosAtivosView.as_view(),
        name="autocomplete-alunos-ativos",
    ),
    # A07
    path(
        "alunos/ativos/anos/<str:anoTurma>/anos-letivos/<str:anoLetivo>/"
        "inicio/<str:dataInicio>/fim/<str:dataFim>",
        TotalAlunosAtivosPorPeriodoView.as_view(),
        name="total-alunos-ativos-por-periodo",
    ),
    # A08
    path(
        "alunos/turmas/<str:codigoTurma>/ativos/<str:dataReferenciaFim>",
        AlunosAtivosPeriodoTurmaView.as_view(),
        name="alunos-ativos-periodo-turma",
    ),
    # A09
    path(
        "alunos/turmas/<str:codigoTurma>/ativos",
        AlunosAtivosTurmaView.as_view(),
        name="alunos-ativos-turma",
    ),
    # A10
    path(
        "alunos/<str:codigoAluno>/necessidades-especiais",
        NecessidadesEspeciaisAlunoView.as_view(),
        name="necessidades-especiais-aluno",
    ),
    # A11
    path(
        "alunos/anoLetivo/<str:anoLetivo>/alunos",
        AlunosPorCodigosEAnoView.as_view(),
        name="alunos-por-codigos-e-ano",
    ),
    # A12
    path(
        "alunos/alunos",
        AlunosPorCodigosView.as_view(),
        name="alunos-por-codigos",
    ),
    # A13
    path(
        "alunos/<str:codigoAluno>/informacoes",
        InformacoesAlunoView.as_view(),
        name="informacoes-aluno",
    ),
    # A14
    path(
        "alunos/<str:codigoTurma>/turma/informacoes",
        InformacoesAlunosTurmaView.as_view(),
        name="informacoes-alunos-turma",
    ),
    # A15
    path(
        "alunos/ano-letivo/<str:anoLetivo>/matriculados",
        QuantidadeMatriculadosPorAnoCCView.as_view(),
        name="quantidade-matriculados-cc",
    ),
    # A16
    path(
        "alunos/ano-letivo/<str:anoLetivo>/matriculados/quantidade",
        QuantidadeMatriculadosView.as_view(),
        name="quantidade-matriculados",
    ),
    # A18
    path(
        "alunos/dados-acompanhamento-escolar",
        DadosAcompanhamentoEscolarView.as_view(),
        name="dados-acompanhamento-escolar",
    ),
    # A19
    path(
        "alunos/responsaveis",
        ResponsaveisDreUeTurmaView.as_view(),
        name="responsaveis-dre-ue-turma",
    ),
    # A20
    path(
        "alunos/responsaveis/<str:cpfResponsavel>",
        DadosResponsavelView.as_view(),
        name="dados-responsavel",
    ),
    # A21
    path(
        "alunos/responsaveis/<str:cpfResponsavel>/resumido",
        DadosResponsavelResumidoView.as_view(),
        name="dados-responsavel-resumido",
    ),
    # A27 — deve vir antes de A22/A23 para não ser capturado pelo <str:cpfResponsavel>
    path(
        "alunos/<str:codigoAluno>/responsaveis/filiacao",
        FiliacaoAlunoView.as_view(),
        name="filiacao-aluno",
    ),
    # A22 (PUT) e A23 (POST) — mesmo path, métodos diferentes
    path(
        "alunos/<str:codigoAluno>/responsaveis/<str:cpfResponsavel>",
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
        "matriculas/escolas/<str:ueCodigo>/quantidades",
        TotalMatriculasPorTurnoUeView.as_view(),
        name="matriculas-quantidades-ue",
    ),
    # M04
    path(
        "matriculas/escolas/dre/<str:dreCodigo>/quantidades",
        TotalMatriculasPorTurnoDreView.as_view(),
        name="matriculas-quantidades-dre",
    ),
    # ------------------------------------------------------------------
    # EscolaController (E05/E24) do legado → /api/escolas/...
    # ------------------------------------------------------------------
    # E05
    path(
        "escolas/<str:codigoEscola>/alunos/quantidade",
        QuantidadeAlunosPorTurmaEscolaView.as_view(),
        name="quantidade-alunos-por-turma-escola",
    ),
    # E24
    path(
        "escolas/<str:codigoEscola>/aluno/<str:codigoAluno>/matriculas",
        MatriculasAlunoEscolaView.as_view(),
        name="matriculas-aluno-escola",
    ),
]
