"""Views do domínio Alunos (A01-A27, M01-M04, E05, E24).

Substituem os endpoints legados do Pedagogico-API
(AlunoController/MatriculaController + os endpoints E05/E24 do
EscolaController) que hoje consultam EOL/Elastic. Os dados vêm de
alunos_db, populado pelo SME-IntegracaoEOL-MS-ETL.
"""

from datetime import datetime
from typing import Any

from django.http import HttpResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.alunos import services
from apps.alunos.api.serializers import (
    AlunoAtivoTurmaSerializer,
    AlunoAutocompleteSerializer,
    AtualizarResponsavelBuscaAtivaRequestSerializer,
    CadastrarResponsavelRequestSerializer,
    ConsolidacaoMatriculaSerializer,
    DadosAcompanhamentoEscolarSerializer,
    DadosResponsavelResumidoSerializer,
    DadosResponsavelSerializer,
    InformacoesAlunoSerializer,
    InformacoesAlunoTurmaSerializer,
    MatriculaEscolaAlunoSerializer,
    NecessidadeEspecialSerializer,
    QuantidadeMatriculadosCCSerializer,
    QuantidadeMatriculadosSerializer,
    ResponsavelTurmaSerializer,
    TotalAlunosAtivosPeriodoSerializer,
    TurmaDoAlunoSerializer,
)

_TAG_ALUNO = ["Alunos"]
_TAG_RESPONSAVEL = ["Alunos — Responsáveis"]
_TAG_MATRICULA = ["Matrículas"]
_TAG_ESCOLA = ["Escolas"]

ALUNO_SEM_TURMA = "Não foram encontradas turmas para o aluno."
CODIGO_UE_E_ANO_LETIVO_OBRIGATORIOS = (
    "Código da UE e ano letivo são obrigatórios."
)

# ---------------------------------------------------------------------------
# Helpers de parsing
# ---------------------------------------------------------------------------


def _to_int(valor: str, nome_param: str) -> int:
    try:
        return int(valor)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Parâmetro '{nome_param}' deve ser um inteiro válido: "
            f"recebido {valor!r}."
        ) from exc


def _to_bool(valor: str, nome_param: str) -> bool:
    if valor is None:
        raise ValueError(f"Parâmetro '{nome_param}' obrigatório.")
    val = str(valor).strip().lower()
    if val in ("true", "1", "t", "yes", "sim"):
        return True
    if val in ("false", "0", "f", "no", "nao", "não"):
        return False
    raise ValueError(
        f"Parâmetro '{nome_param}' deve ser booleano: recebido {valor!r}."
    )


def _to_datetime(valor: str, nome_param: str) -> datetime:
    try:
        if "T" in valor or " " in valor:
            return datetime.fromisoformat(valor.replace("Z", "+00:00"))
        return datetime.strptime(valor, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError(
            f"Parâmetro '{nome_param}' deve ser uma data ISO 8601 válida:"
            f" recebido {valor!r}."
        ) from exc


def _query_int_list(request: Request, nome: str) -> list[int]:
    raw = request.query_params.getlist(nome)
    saida: list[int] = []
    for v in raw:
        if v == "":
            continue
        try:
            saida.append(int(v))
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Parâmetro '{nome}' deve conter inteiros: recebido {v!r}."
            ) from exc
    return saida


def _erro_400(detalhe: str) -> Response:
    return Response({"detail": detalhe}, status=status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# A01 / A02 — Turmas do aluno
# ---------------------------------------------------------------------------
class BuscaTurmasDoAlunoView(APIView):
    """A01/A02 — Turmas do aluno (com filtros opcionais via rota)."""

    @extend_schema(
        tags=_TAG_ALUNO,
        summary="A01/A02 | Turmas do aluno",
        parameters=[
            OpenApiParameter("codigoAluno", int, OpenApiParameter.PATH),
            OpenApiParameter(
                "anoLetivo", int, OpenApiParameter.PATH, required=False
            ),
            OpenApiParameter(
                "historico", bool, OpenApiParameter.PATH, required=False
            ),
            OpenApiParameter(
                "filtrarSituacao",
                bool,
                OpenApiParameter.PATH,
                required=False,
            ),
            OpenApiParameter(
                "tipoTurma", bool, OpenApiParameter.PATH, required=False
            ),
        ],
        responses={200: TurmaDoAlunoSerializer(many=True)},
    )
    def get(
        self,
        request: Request,
        codigoAluno: str,
        anoLetivo: str | None = None,
        historico: str | None = None,
        filtrarSituacao: str | None = None,
        tipoTurma: str | None = None,
    ) -> Response:
        try:
            codigo = _to_int(codigoAluno, "codigoAluno")
            ano = _to_int(anoLetivo, "anoLetivo") if anoLetivo else None
            hist = (
                _to_bool(historico, "historico")
                if historico is not None
                else False
            )
            filtra = (
                _to_bool(filtrarSituacao, "filtrarSituacao")
                if filtrarSituacao is not None
                else True
            )
            if tipoTurma is not None:
                _to_bool(tipoTurma, "tipoTurma")
        except ValueError as exc:
            return _erro_400(str(exc))

        if codigo <= 0:
            return _erro_400("Código do aluno obrigatório.")

        dados = services.buscar_turmas_do_aluno(
            codigo_aluno=codigo,
            ano_letivo=ano,
            historico=hist,
            filtrar_situacao=filtra,
        )
        if not dados:
            return Response(
                {"detail": ALUNO_SEM_TURMA},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(TurmaDoAlunoSerializer(dados, many=True).data)


# ---------------------------------------------------------------------------
# A03 — Turmas filtradas por situação de matrícula
# ---------------------------------------------------------------------------
class BuscaTurmasDoAlunoPorSituacaoMatriculaView(APIView):
    """A03 — Turmas do aluno com filtro de situação de matrícula."""

    @extend_schema(
        tags=_TAG_ALUNO,
        summary="A03 | Turmas filtradas por situação de matrícula",
        parameters=[
            OpenApiParameter("codigoAluno", int, OpenApiParameter.PATH),
            OpenApiParameter("anoLetivo", int, OpenApiParameter.PATH),
            OpenApiParameter(
                "filtrarSituacaoMatricula", bool, OpenApiParameter.PATH
            ),
            OpenApiParameter("tipoTurma", bool, OpenApiParameter.PATH),
        ],
        responses={200: TurmaDoAlunoSerializer(many=True)},
    )
    def get(
        self,
        request: Request,
        codigoAluno: str,
        anoLetivo: str,
        filtrarSituacaoMatricula: str,
        tipoTurma: str,
    ) -> Response:
        try:
            codigo = _to_int(codigoAluno, "codigoAluno")
            ano = _to_int(anoLetivo, "anoLetivo")
            filtra = _to_bool(
                filtrarSituacaoMatricula, "filtrarSituacaoMatricula"
            )
            _to_bool(tipoTurma, "tipoTurma")
        except ValueError as exc:
            return _erro_400(str(exc))

        if codigo <= 0:
            return _erro_400("Código do aluno obrigatório.")

        dados = services.buscar_turmas_do_aluno_por_situacao_matricula(
            codigo_aluno=codigo,
            ano_letivo=ano,
            filtrar_situacao_matricula=filtra,
        )
        if not dados:
            return Response(
                {"detail": ALUNO_SEM_TURMA},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(TurmaDoAlunoSerializer(dados, many=True).data)


# ---------------------------------------------------------------------------
# A04 — Alunos da UE/ano (busca por nome ou código)
# ---------------------------------------------------------------------------
class BuscarAlunosDaUeView(APIView):
    """A04 — Alunos de uma UE no ano letivo."""

    @extend_schema(
        tags=_TAG_ALUNO,
        summary="A04 | Alunos de uma UE por ano letivo",
        parameters=[
            OpenApiParameter("codigoUe", str, OpenApiParameter.PATH),
            OpenApiParameter("anoLetivo", int, OpenApiParameter.PATH),
            OpenApiParameter("nomeAluno", str, OpenApiParameter.QUERY),
            OpenApiParameter("codigoEol", str, OpenApiParameter.QUERY),
        ],
        responses={200: TurmaDoAlunoSerializer(many=True)},
    )
    def get(self, request: Request, codigoUe: str, anoLetivo: str) -> Response:
        if not codigoUe or not anoLetivo:
            return _erro_400(CODIGO_UE_E_ANO_LETIVO_OBRIGATORIOS)
        try:
            ano = _to_int(anoLetivo, "anoLetivo")
        except ValueError as exc:
            return _erro_400(str(exc))

        dados = services.buscar_alunos_da_ue(
            codigo_ue=codigoUe,
            ano_letivo=ano,
            nome_aluno=request.query_params.get("nomeAluno"),
            codigo_eol=request.query_params.get("codigoEol"),
        )
        if not dados:
            return Response(
                {"detail": ALUNO_SEM_TURMA},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(TurmaDoAlunoSerializer(dados, many=True).data)


# ---------------------------------------------------------------------------
# A05 — Autocomplete de alunos da UE/ano
# ---------------------------------------------------------------------------
class AutocompleteAlunosUeView(APIView):
    """A05 — Autocomplete de alunos da UE/ano."""

    @extend_schema(
        tags=_TAG_ALUNO,
        summary="A05 | Autocomplete de alunos da UE/ano",
        parameters=[
            OpenApiParameter("codigoUe", str, OpenApiParameter.PATH),
            OpenApiParameter("anoLetivo", int, OpenApiParameter.PATH),
            OpenApiParameter(
                "codigoTurmas", int, OpenApiParameter.QUERY, many=True
            ),
            OpenApiParameter("nomeAluno", str, OpenApiParameter.QUERY),
            OpenApiParameter("codigoEol", str, OpenApiParameter.QUERY),
            OpenApiParameter("somenteAtivos", bool, OpenApiParameter.QUERY),
            OpenApiParameter("ehHistorico", bool, OpenApiParameter.QUERY),
            OpenApiParameter("limite", int, OpenApiParameter.QUERY),
        ],
        responses={200: AlunoAutocompleteSerializer(many=True)},
    )
    def get(self, request: Request, codigoUe: str, anoLetivo: str) -> Response:
        if not codigoUe:
            return _erro_400(CODIGO_UE_E_ANO_LETIVO_OBRIGATORIOS)
        try:
            ano = _to_int(anoLetivo, "anoLetivo")
            codigos_turmas = _query_int_list(request, "codigoTurmas")
            limite = int(request.query_params.get("limite", "10"))
        except ValueError as exc:
            return _erro_400(str(exc))

        somente_ativos = request.query_params.get(
            "somenteAtivos", ""
        ).lower() in ("true", "1")
        eh_historico = request.query_params.get("ehHistorico", "").lower() in (
            "true",
            "1",
        )

        dados = services.buscar_alunos_autocomplete(
            codigo_ue=codigoUe,
            ano_letivo=ano,
            codigo_turmas=codigos_turmas,
            nome_aluno=request.query_params.get("nomeAluno"),
            codigo_eol=request.query_params.get("codigoEol"),
            somente_ativos=somente_ativos,
            eh_historico=eh_historico,
            limite=limite,
        )
        if not dados:
            return Response(
                {"detail": ALUNO_SEM_TURMA},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(AlunoAutocompleteSerializer(dados, many=True).data)


# ---------------------------------------------------------------------------
# A06 — Autocomplete de alunos ativos por data de referência
# ---------------------------------------------------------------------------
class AutocompleteAlunosAtivosView(APIView):
    """A06 — Autocomplete de alunos ativos por data de referência."""

    @extend_schema(
        tags=_TAG_ALUNO,
        summary="A06 | Autocomplete de alunos ativos por referência",
        parameters=[
            OpenApiParameter("ueCodigo", str, OpenApiParameter.PATH),
            OpenApiParameter("alunoNome", str, OpenApiParameter.QUERY),
            OpenApiParameter("dataReferencia", str, OpenApiParameter.QUERY),
            OpenApiParameter("alunoCodigo", int, OpenApiParameter.QUERY),
            OpenApiParameter("limite", int, OpenApiParameter.QUERY),
        ],
        responses={200: AlunoAutocompleteSerializer(many=True)},
    )
    def get(self, request: Request, ueCodigo: str) -> Response:
        if not ueCodigo:
            return _erro_400(CODIGO_UE_E_ANO_LETIVO_OBRIGATORIOS)

        aluno_nome = request.query_params.get("alunoNome")
        try:
            aluno_codigo = int(request.query_params.get("alunoCodigo", "0"))
            limite = int(request.query_params.get("limite", "10"))
            data_ref = request.query_params.get("dataReferencia")
            data_ref_dt = (
                _to_datetime(data_ref, "dataReferencia") if data_ref else None
            )
        except ValueError as exc:
            return _erro_400(str(exc))

        if aluno_codigo == 0 and (not aluno_nome or len(aluno_nome) < 3):
            return _erro_400("O Nome deve conter no mínimo 3 caracteres.")

        dados = services.buscar_alunos_ativos_autocomplete(
            ue_codigo=ueCodigo,
            aluno_nome=aluno_nome,
            data_referencia=data_ref_dt,
            aluno_codigo=aluno_codigo,
            limite=limite,
        )
        if not dados:
            return Response(
                {"detail": ALUNO_SEM_TURMA},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(AlunoAutocompleteSerializer(dados, many=True).data)


# ---------------------------------------------------------------------------
# A07 — Total de alunos ativos por período/ano/modalidade
# ---------------------------------------------------------------------------
class TotalAlunosAtivosPorPeriodoView(APIView):
    """A07 — Total de alunos ativos por período."""

    @extend_schema(
        tags=_TAG_ALUNO,
        summary="A07 | Total de alunos ativos por período",
        parameters=[
            OpenApiParameter("anoTurma", str, OpenApiParameter.PATH),
            OpenApiParameter("anoLetivo", int, OpenApiParameter.PATH),
            OpenApiParameter("dataInicio", str, OpenApiParameter.PATH),
            OpenApiParameter("dataFim", str, OpenApiParameter.PATH),
            OpenApiParameter("ueId", str, OpenApiParameter.QUERY),
            OpenApiParameter("dreId", str, OpenApiParameter.QUERY),
            OpenApiParameter(
                "modalidades", int, OpenApiParameter.QUERY, many=True
            ),
        ],
        responses={200: TotalAlunosAtivosPeriodoSerializer},
    )
    def get(
        self,
        request: Request,
        anoTurma: str,
        anoLetivo: str,
        dataInicio: str,
        dataFim: str,
    ) -> Response:
        try:
            ano = _to_int(anoLetivo, "anoLetivo")
            inicio = _to_datetime(dataInicio, "dataInicio")
            fim = _to_datetime(dataFim, "dataFim")
            modalidades = _query_int_list(request, "modalidades")
        except ValueError as exc:
            return _erro_400(str(exc))

        dados = services.obter_total_alunos_ativos_periodo(
            ano_turma=anoTurma,
            ano_letivo=ano,
            data_inicio=inicio,
            data_fim=fim,
            ue_id=request.query_params.get("ueId"),
            dre_id=request.query_params.get("dreId"),
            modalidades=modalidades,
        )
        return Response(TotalAlunosAtivosPeriodoSerializer(dados).data)


# ---------------------------------------------------------------------------
# A08 — Alunos ativos em uma turma com período
# ---------------------------------------------------------------------------
class AlunosAtivosPeriodoTurmaView(APIView):
    """A08 — Alunos ativos em uma turma por período."""

    @extend_schema(
        tags=_TAG_ALUNO,
        summary="A08 | Alunos ativos em turma por período",
        parameters=[
            OpenApiParameter("codigoTurma", int, OpenApiParameter.PATH),
            OpenApiParameter("dataReferenciaFim", str, OpenApiParameter.PATH),
            OpenApiParameter(
                "dataReferenciaInicio", str, OpenApiParameter.QUERY
            ),
        ],
        responses={200: AlunoAtivoTurmaSerializer(many=True)},
    )
    def get(
        self,
        request: Request,
        codigoTurma: str,
        dataReferenciaFim: str,
    ) -> Response:
        try:
            codigo = _to_int(codigoTurma, "codigoTurma")
            fim = _to_datetime(dataReferenciaFim, "dataReferenciaFim")
            inicio_raw = request.query_params.get("dataReferenciaInicio")
            inicio = (
                _to_datetime(inicio_raw, "dataReferenciaInicio")
                if inicio_raw
                else None
            )
        except ValueError as exc:
            return _erro_400(str(exc))

        dados = services.obter_alunos_ativos_por_periodo_e_turma(
            codigo_turma=codigo,
            data_referencia_fim=fim,
            data_referencia_inicio=inicio,
        )
        return Response(AlunoAtivoTurmaSerializer(dados, many=True).data)


# ---------------------------------------------------------------------------
# A09 — Alunos ativos em uma turma
# ---------------------------------------------------------------------------
class AlunosAtivosTurmaView(APIView):
    """A09 — Alunos ativos em uma turma."""

    @extend_schema(
        tags=_TAG_ALUNO,
        summary="A09 | Alunos ativos em turma",
        parameters=[
            OpenApiParameter("codigoTurma", int, OpenApiParameter.PATH)
        ],
        responses={200: AlunoAtivoTurmaSerializer(many=True)},
    )
    def get(self, request: Request, codigoTurma: str) -> Response:
        try:
            codigo = _to_int(codigoTurma, "codigoTurma")
        except ValueError as exc:
            return _erro_400(str(exc))

        dados = services.obter_alunos_ativos_por_turma(codigo_turma=codigo)
        return Response(AlunoAtivoTurmaSerializer(dados, many=True).data)


# ---------------------------------------------------------------------------
# A10 — Necessidades especiais do aluno
# ---------------------------------------------------------------------------
class NecessidadesEspeciaisAlunoView(APIView):
    """A10 — Necessidades especiais do aluno."""

    @extend_schema(
        tags=_TAG_ALUNO,
        summary="A10 | Necessidades especiais do aluno",
        parameters=[
            OpenApiParameter("codigoAluno", int, OpenApiParameter.PATH)
        ],
        responses={200: NecessidadeEspecialSerializer(many=True)},
    )
    def get(self, request: Request, codigoAluno: str) -> Response:
        try:
            codigo = _to_int(codigoAluno, "codigoAluno")
        except ValueError as exc:
            return _erro_400(str(exc))

        dados = services.obter_necessidades_especiais_por_aluno(
            codigo_aluno=codigo
        )
        return Response(NecessidadeEspecialSerializer(dados, many=True).data)


# ---------------------------------------------------------------------------
# A11 — Alunos por lista de códigos e ano letivo
# ---------------------------------------------------------------------------
class AlunosPorCodigosEAnoView(APIView):
    """A11 — Alunos por lista de códigos e ano letivo."""

    @extend_schema(
        tags=_TAG_ALUNO,
        summary="A11 | Alunos por lista de códigos e ano letivo",
        parameters=[
            OpenApiParameter("anoLetivo", int, OpenApiParameter.PATH),
            OpenApiParameter(
                "codigosAluno",
                int,
                OpenApiParameter.QUERY,
                many=True,
                required=True,
            ),
        ],
        responses={200: TurmaDoAlunoSerializer(many=True)},
    )
    def get(self, request: Request, anoLetivo: str) -> Response:
        try:
            ano = _to_int(anoLetivo, "anoLetivo")
            codigos = _query_int_list(request, "codigosAluno")
        except ValueError as exc:
            return _erro_400(str(exc))

        dados = services.obter_alunos_por_codigos_e_ano(
            codigos_aluno=codigos, ano_letivo=ano
        )
        return Response(TurmaDoAlunoSerializer(dados, many=True).data)


# ---------------------------------------------------------------------------
# A12 — Alunos por lista de códigos
# ---------------------------------------------------------------------------
class AlunosPorCodigosView(APIView):
    """A12 — Alunos por lista de códigos."""

    @extend_schema(
        tags=_TAG_ALUNO,
        summary="A12 | Alunos por lista de códigos",
        parameters=[
            OpenApiParameter(
                "codigosAluno",
                int,
                OpenApiParameter.QUERY,
                many=True,
                required=True,
            )
        ],
        responses={200: TurmaDoAlunoSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        try:
            codigos = _query_int_list(request, "codigosAluno")
        except ValueError as exc:
            return _erro_400(str(exc))

        dados = services.obter_alunos_por_codigos(codigos_aluno=codigos)
        return Response(TurmaDoAlunoSerializer(dados, many=True).data)


# ---------------------------------------------------------------------------
# A13 — Informações completas do aluno
# ---------------------------------------------------------------------------
class InformacoesAlunoView(APIView):
    """A13 — Informações completas do aluno."""

    @extend_schema(
        tags=_TAG_ALUNO,
        summary="A13 | Informações completas do aluno",
        parameters=[
            OpenApiParameter("codigoAluno", int, OpenApiParameter.PATH)
        ],
        responses={200: InformacoesAlunoSerializer},
    )
    def get(self, request: Request, codigoAluno: str) -> Response:
        try:
            codigo = _to_int(codigoAluno, "codigoAluno")
        except ValueError as exc:
            return _erro_400(str(exc))

        dado = services.obter_informacoes_aluno(codigo_aluno=codigo)
        if dado is None:
            return Response(
                {"detail": "Aluno não encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(InformacoesAlunoSerializer(dado).data)


# ---------------------------------------------------------------------------
# A14 — Informações dos alunos de uma turma
# ---------------------------------------------------------------------------
class InformacoesAlunosTurmaView(APIView):
    """A14 — Informações dos alunos de uma turma."""

    @extend_schema(
        tags=_TAG_ALUNO,
        summary="A14 | Informações dos alunos da turma",
        parameters=[
            OpenApiParameter("codigoTurma", int, OpenApiParameter.PATH)
        ],
        responses={200: InformacoesAlunoTurmaSerializer(many=True)},
    )
    def get(self, request: Request, codigoTurma: str) -> Response:
        try:
            codigo = _to_int(codigoTurma, "codigoTurma")
        except ValueError as exc:
            return _erro_400(str(exc))

        dados = services.obter_informacoes_alunos_da_turma(codigo_turma=codigo)
        return Response(InformacoesAlunoTurmaSerializer(dados, many=True).data)


# ---------------------------------------------------------------------------
# A15 — Quantidade de matriculados por componente curricular e ano
# ---------------------------------------------------------------------------
class QuantidadeMatriculadosPorAnoCCView(APIView):
    """A15 — Quantidade de matriculados por componente curricular e ano."""

    @extend_schema(
        tags=_TAG_ALUNO,
        summary="A15 | Quantidade de matriculados por CC e ano",
        parameters=[
            OpenApiParameter("anoLetivo", int, OpenApiParameter.PATH),
            OpenApiParameter("dreId", str, OpenApiParameter.QUERY),
            OpenApiParameter("ueId", str, OpenApiParameter.QUERY),
            OpenApiParameter(
                "componentesCurriculares",
                int,
                OpenApiParameter.QUERY,
                many=True,
                required=True,
            ),
        ],
        responses={200: QuantidadeMatriculadosCCSerializer(many=True)},
    )
    def get(self, request: Request, anoLetivo: str) -> Response:
        try:
            ano = _to_int(anoLetivo, "anoLetivo")
            componentes = _query_int_list(request, "componentesCurriculares")
        except ValueError as exc:
            return _erro_400(str(exc))
        if not componentes:
            return _erro_400("componentesCurriculares é obrigatório.")

        payload = services.obter_quantidade_matriculados_por_ano_e_cc_json(
            ano_letivo=ano,
            componentes_curriculares=componentes,
            dre_id=request.query_params.get("dreId"),
            ue_id=request.query_params.get("ueId"),
        )
        return HttpResponse(payload, content_type="application/json")


# ---------------------------------------------------------------------------
# A16 — Quantidade de matriculados (filtros DRE/UE/modalidade/ano/turma)
# ---------------------------------------------------------------------------
class QuantidadeMatriculadosView(APIView):
    """A16 — Quantidade de matriculados com múltiplos filtros."""

    @extend_schema(
        tags=_TAG_ALUNO,
        summary="A16 | Quantidade de matriculados (filtros)",
        parameters=[
            OpenApiParameter("anoLetivo", int, OpenApiParameter.PATH),
            OpenApiParameter("dreCodigo", str, OpenApiParameter.QUERY),
            OpenApiParameter("ueCodigo", str, OpenApiParameter.QUERY),
            OpenApiParameter(
                "modalidade", int, OpenApiParameter.QUERY, many=True
            ),
            OpenApiParameter("ano", int, OpenApiParameter.QUERY, many=True),
            OpenApiParameter("turma", str, OpenApiParameter.QUERY, many=True),
        ],
        responses={200: QuantidadeMatriculadosSerializer(many=True)},
    )
    def get(self, request: Request, anoLetivo: str) -> Response:
        try:
            ano = _to_int(anoLetivo, "anoLetivo")
            modalidade = _query_int_list(request, "modalidade")
            ano_lst = _query_int_list(request, "ano")
        except ValueError as exc:
            return _erro_400(str(exc))

        turma = request.query_params.getlist("turma")
        payload = services.obter_quantidade_matriculados_json(
            ano_letivo=ano,
            dre_codigo=request.query_params.get("dreCodigo", ""),
            ue_codigo=request.query_params.get("ueCodigo", ""),
            modalidade=modalidade,
            ano=ano_lst,
            turma=turma,
        )
        return HttpResponse(payload, content_type="application/json")


# ---------------------------------------------------------------------------
# A18 — Dados de acompanhamento escolar
# ---------------------------------------------------------------------------
class DadosAcompanhamentoEscolarView(APIView):
    """A18 — Dados de acompanhamento escolar."""

    @extend_schema(
        tags=_TAG_ALUNO,
        summary="A18 | Dados de acompanhamento escolar",
        parameters=[
            OpenApiParameter("codigoAluno", int, OpenApiParameter.QUERY),
            OpenApiParameter("codigoDre", str, OpenApiParameter.QUERY),
            OpenApiParameter("codigoUe", str, OpenApiParameter.QUERY),
            OpenApiParameter("cpfResponsavel", str, OpenApiParameter.QUERY),
            OpenApiParameter("anoLetivo", int, OpenApiParameter.QUERY),
            OpenApiParameter("modalidade", int, OpenApiParameter.QUERY),
            OpenApiParameter("semestre", int, OpenApiParameter.QUERY),
            OpenApiParameter("turmaCodigo", str, OpenApiParameter.QUERY),
        ],
        responses={200: DadosAcompanhamentoEscolarSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        codigo_aluno_raw = request.query_params.get("codigoAluno")
        codigo_dre = request.query_params.get("codigoDre")
        codigo_ue = request.query_params.get("codigoUe")
        cpf_responsavel = request.query_params.get("cpfResponsavel")
        if not any((codigo_aluno_raw, codigo_dre, codigo_ue, cpf_responsavel)):
            return _erro_400(
                "Nenhum filtro foi especificado para busca de dados "
                "dos alunos para acompanhamento do estudante"
            )
        try:
            codigo_aluno = (
                _to_int(codigo_aluno_raw, "codigoAluno")
                if codigo_aluno_raw
                else None
            )
            ano = (
                int(request.query_params["anoLetivo"])
                if "anoLetivo" in request.query_params
                else None
            )
            modalidade = (
                int(request.query_params["modalidade"])
                if "modalidade" in request.query_params
                else None
            )
            semestre = (
                int(request.query_params["semestre"])
                if "semestre" in request.query_params
                else None
            )
        except (TypeError, ValueError) as exc:
            return _erro_400(str(exc))

        payload = services.obter_dados_acompanhamento_escolar_json(
            codigo_aluno=codigo_aluno,
            codigo_dre=codigo_dre,
            codigo_ue=codigo_ue,
            cpf_responsavel=cpf_responsavel,
            ano_letivo=ano,
            modalidade=modalidade,
            semestre=semestre,
            turma_codigo=request.query_params.get("turmaCodigo"),
        )
        return HttpResponse(payload, content_type="application/json")


# ---------------------------------------------------------------------------
# A19 — Responsáveis por DRE/UE/turma
# ---------------------------------------------------------------------------
class ResponsaveisDreUeTurmaView(APIView):
    """A19 — Responsáveis por DRE/UE/turma.

    ``codigoDre`` é obrigatório por contrato — exigência declarativa,
    pois o domínio Alunos não armazena DRE e o filtro não é aplicado
    internamente. ``codigoUe`` é o único filtro que efetivamente recorta
    os dados; quando omitido, a query varre todas as matrículas ativas.
    """

    @extend_schema(
        tags=_TAG_RESPONSAVEL,
        summary="A19 | Responsáveis por DRE/UE/turma",
        parameters=[
            OpenApiParameter(
                "codigoDre", str, OpenApiParameter.QUERY, required=True
            ),
            OpenApiParameter("codigoUe", str, OpenApiParameter.QUERY),
            OpenApiParameter("anoLetivo", int, OpenApiParameter.QUERY),
        ],
        responses={200: ResponsavelTurmaSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        codigo_dre = request.query_params.get("codigoDre")
        if not codigo_dre:
            return _erro_400("codigoDre é obrigatório.")
        try:
            ano = (
                int(request.query_params["anoLetivo"])
                if "anoLetivo" in request.query_params
                else None
            )
        except (TypeError, ValueError) as exc:
            return _erro_400(str(exc))

        payload = services.obter_responsaveis_dre_ue_turma_json(
            codigo_dre=codigo_dre,
            codigo_ue=request.query_params.get("codigoUe"),
            ano_letivo=ano,
        )
        if payload == b"[]":
            return Response(status=status.HTTP_204_NO_CONTENT)
        return HttpResponse(payload, content_type="application/json")


# ---------------------------------------------------------------------------
# A20 — Dados completos do responsável
# ---------------------------------------------------------------------------
class DadosResponsavelView(APIView):
    """A20 — Dados completos do responsável."""

    @extend_schema(
        tags=_TAG_RESPONSAVEL,
        summary="A20 | Dados completos do responsável",
        parameters=[
            OpenApiParameter("cpfResponsavel", str, OpenApiParameter.PATH)
        ],
        responses={200: DadosResponsavelSerializer(many=True)},
    )
    def get(self, request: Request, cpfResponsavel: str) -> Response:
        dados = services.obter_dados_responsavel(
            cpf_responsavel=cpfResponsavel
        )
        return Response(DadosResponsavelSerializer(dados, many=True).data)


# ---------------------------------------------------------------------------
# A21 — Dados resumidos do responsável
# ---------------------------------------------------------------------------
class DadosResponsavelResumidoView(APIView):
    """A21 — Dados resumidos do responsável."""

    @extend_schema(
        tags=_TAG_RESPONSAVEL,
        summary="A21 | Dados resumidos do responsável",
        parameters=[
            OpenApiParameter("cpfResponsavel", str, OpenApiParameter.PATH)
        ],
        responses={200: DadosResponsavelResumidoSerializer},
    )
    def get(self, request: Request, cpfResponsavel: str) -> Response:
        dado = services.obter_dados_responsavel_resumido(
            cpf_responsavel=cpfResponsavel
        )
        if dado is None:
            return Response(
                {"detail": "Responsável não encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(DadosResponsavelResumidoSerializer(dado).data)


# ---------------------------------------------------------------------------
# A22 (PUT) e A23 (POST) — Atualizar/cadastrar responsável do aluno
# ---------------------------------------------------------------------------
class ResponsavelAlunoView(APIView):
    """A22/A23 — PUT atualiza (busca ativa) e POST cadastra responsável."""

    @extend_schema(
        tags=_TAG_RESPONSAVEL,
        summary="A22 | Atualizar dados do responsável (busca ativa)",
        parameters=[
            OpenApiParameter("codigoAluno", int, OpenApiParameter.PATH),
            OpenApiParameter("cpfResponsavel", str, OpenApiParameter.PATH),
        ],
        request=AtualizarResponsavelBuscaAtivaRequestSerializer,
        responses={200: DadosResponsavelResumidoSerializer},
    )
    def put(
        self, request: Request, codigoAluno: str, cpfResponsavel: str
    ) -> Response:
        try:
            codigo = _to_int(codigoAluno, "codigoAluno")
        except ValueError as exc:
            return _erro_400(str(exc))

        serializer = AtualizarResponsavelBuscaAtivaRequestSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)
        body: dict[str, Any] = serializer.validated_data

        resumo = services.atualizar_dados_responsavel_busca_ativa(
            codigo_aluno=codigo,
            cpf_responsavel=cpfResponsavel,
            email=body.get("email"),
            ddd_celular=body.get("ddd_celular"),
            numero_celular=body.get("numero_celular"),
        )
        return Response(DadosResponsavelResumidoSerializer(resumo).data)

    @extend_schema(
        tags=_TAG_RESPONSAVEL,
        summary="A23 | Cadastrar dados do responsável do aluno",
        parameters=[
            OpenApiParameter("codigoAluno", int, OpenApiParameter.PATH),
            OpenApiParameter("cpfResponsavel", str, OpenApiParameter.PATH),
        ],
        request=CadastrarResponsavelRequestSerializer,
        responses={200: DadosResponsavelResumidoSerializer},
    )
    def post(
        self, request: Request, codigoAluno: str, cpfResponsavel: str
    ) -> Response:
        try:
            codigo = _to_int(codigoAluno, "codigoAluno")
        except ValueError as exc:
            return _erro_400(str(exc))

        serializer = CadastrarResponsavelRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        body: dict[str, Any] = serializer.validated_data

        resumo = services.cadastrar_dados_responsavel(
            codigo_aluno=codigo,
            cpf_responsavel=cpfResponsavel,
            nome=body.get("nome", ""),
            email=body.get("email", ""),
            tipo_responsavel=body.get("tipo_responsavel"),
            ddd_celular=body.get("ddd_celular", ""),
            numero_celular=body.get("numero_celular", ""),
        )
        return Response(DadosResponsavelResumidoSerializer(resumo).data)


# ---------------------------------------------------------------------------
# A27 — Dados de filiação do responsável do aluno
# ---------------------------------------------------------------------------
class FiliacaoAlunoView(APIView):
    """A27 — Dados de filiação do responsável do aluno."""

    @extend_schema(
        tags=_TAG_RESPONSAVEL,
        summary="A27 | Dados de filiação do responsável do aluno",
        parameters=[
            OpenApiParameter("codigoAluno", int, OpenApiParameter.PATH)
        ],
        responses={200: InformacoesAlunoSerializer},
    )
    def get(self, request: Request, codigoAluno: str) -> Response:
        try:
            codigo = _to_int(codigoAluno, "codigoAluno")
        except ValueError as exc:
            return _erro_400(str(exc))

        dado = services.obter_dados_responsavel_filiacao(codigo_aluno=codigo)
        if dado is None:
            return Response(
                {"detail": "Aluno não encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(InformacoesAlunoSerializer(dado).data)


# ---------------------------------------------------------------------------
# M01 — Matrículas consolidadas do ano atual
# ---------------------------------------------------------------------------
class MatriculasAnoAtualView(APIView):
    """M01 — Matrículas consolidadas do ano atual."""

    @extend_schema(
        tags=_TAG_MATRICULA,
        summary="M01 | Matrículas consolidadas do ano atual",
        parameters=[
            OpenApiParameter(
                "anoLetivo", int, OpenApiParameter.QUERY, required=True
            ),
            OpenApiParameter(
                "ueCodigo", str, OpenApiParameter.QUERY, required=True
            ),
        ],
        responses={200: ConsolidacaoMatriculaSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        ano_raw = request.query_params.get("anoLetivo")
        ue_codigo = request.query_params.get("ueCodigo")
        if not ano_raw or not ue_codigo:
            return _erro_400("anoLetivo e ueCodigo são obrigatórios.")
        try:
            ano = _to_int(ano_raw, "anoLetivo")
        except ValueError as exc:
            return _erro_400(str(exc))

        dados = services.obter_matriculas_ano_atual(
            ano_letivo=ano, ue_codigo=ue_codigo
        )
        return Response(ConsolidacaoMatriculaSerializer(dados, many=True).data)


# ---------------------------------------------------------------------------
# M02 — Matrículas consolidadas de anos anteriores
# ---------------------------------------------------------------------------
class MatriculasAnosAnterioresView(APIView):
    """M02 — Matrículas consolidadas de anos anteriores."""

    @extend_schema(
        tags=_TAG_MATRICULA,
        summary="M02 | Matrículas consolidadas de anos anteriores",
        parameters=[
            OpenApiParameter(
                "anoLetivo", int, OpenApiParameter.QUERY, required=True
            ),
            OpenApiParameter(
                "ueCodigo", str, OpenApiParameter.QUERY, required=True
            ),
        ],
        responses={200: ConsolidacaoMatriculaSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        ano_raw = request.query_params.get("anoLetivo")
        ue_codigo = request.query_params.get("ueCodigo")
        if not ano_raw or not ue_codigo:
            return _erro_400("anoLetivo e ueCodigo são obrigatórios.")
        try:
            ano = _to_int(ano_raw, "anoLetivo")
        except ValueError as exc:
            return _erro_400(str(exc))

        dados = services.obter_matriculas_anos_anteriores(
            ano_letivo=ano, ue_codigo=ue_codigo
        )
        return Response(ConsolidacaoMatriculaSerializer(dados, many=True).data)


# ---------------------------------------------------------------------------
# M03 — Total de matrículas por turno em uma escola (out-of-scope)
# ---------------------------------------------------------------------------
class TotalMatriculasPorTurnoUeView(APIView):
    """M03 — Out-of-scope (turno vive no MS Pedagógico).

    Mantemos a rota para preservar o contrato legado, mas a resposta é
    sempre ``[]`` — o Transition Gateway agrega via MS Pedagógico.
    """

    @extend_schema(
        tags=_TAG_MATRICULA,
        summary="M03 | Total de matrículas por turno (UE) — out-of-scope",
        parameters=[
            OpenApiParameter("ueCodigo", str, OpenApiParameter.PATH),
        ],
        responses={200: {"type": "array", "items": {}}},
    )
    def get(self, request: Request, ueCodigo: str) -> Response:
        if not ueCodigo:
            return _erro_400("Código da UE obrigatório.")
        return Response(
            services.obter_total_matriculas_por_turno_ue(ue_codigo=ueCodigo)
        )


# ---------------------------------------------------------------------------
# M04 — Total de matrículas por turno em uma DRE (out-of-scope)
# ---------------------------------------------------------------------------
class TotalMatriculasPorTurnoDreView(APIView):
    """M04 — Out-of-scope (turno + DRE vivem no MS Pedagógico)."""

    @extend_schema(
        tags=_TAG_MATRICULA,
        summary="M04 | Total de matrículas por turno (DRE) — out-of-scope",
        parameters=[
            OpenApiParameter("dreCodigo", str, OpenApiParameter.PATH),
        ],
        responses={200: {"type": "array", "items": {}}},
    )
    def get(self, request: Request, dreCodigo: str) -> Response:
        if not dreCodigo:
            return _erro_400("Código da DRE obrigatório.")
        return Response(
            services.obter_total_matriculas_por_turno_dre(dre_codigo=dreCodigo)
        )


# ---------------------------------------------------------------------------
# E05 — Quantidade de alunos por turma na escola
# ---------------------------------------------------------------------------
class QuantidadeAlunosPorTurmaEscolaView(APIView):
    """E05 — Quantidade de alunos por turma na escola."""

    @extend_schema(
        tags=_TAG_ESCOLA,
        summary="E05 | Quantidade de alunos por turma na escola",
        parameters=[
            OpenApiParameter("codigoEscola", str, OpenApiParameter.PATH)
        ],
        responses={200: ConsolidacaoMatriculaSerializer(many=True)},
    )
    def get(self, request: Request, codigoEscola: str) -> Response:
        if not codigoEscola:
            return _erro_400("Código EOL da escola obrigatório.")
        dados = services.obter_quantidade_alunos_por_turma_da_escola(
            codigo_escola=codigoEscola
        )
        return Response(ConsolidacaoMatriculaSerializer(dados, many=True).data)


# ---------------------------------------------------------------------------
# E24 — Matrículas de um aluno na escola
# ---------------------------------------------------------------------------
class MatriculasAlunoEscolaView(APIView):
    """E24 — Matrículas de um aluno na escola."""

    @extend_schema(
        tags=_TAG_ESCOLA,
        summary="E24 | Matrículas de um aluno na escola",
        parameters=[
            OpenApiParameter("codigoEscola", str, OpenApiParameter.PATH),
            OpenApiParameter("codigoAluno", int, OpenApiParameter.PATH),
        ],
        responses={200: MatriculaEscolaAlunoSerializer(many=True)},
    )
    def get(
        self, request: Request, codigoEscola: str, codigoAluno: str
    ) -> Response:
        if not codigoEscola:
            return _erro_400("O código da escola e do aluno são obrigatórios")
        try:
            codigo_a = _to_int(codigoAluno, "codigoAluno")
        except ValueError:
            return _erro_400("O código da escola e do aluno são obrigatórios")
        dados = services.obter_matriculas_aluno_na_escola(
            codigo_escola=codigoEscola, codigo_aluno=codigo_a
        )
        return Response(MatriculaEscolaAlunoSerializer(dados, many=True).data)
