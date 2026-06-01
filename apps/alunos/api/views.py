"""Views do domínio Alunos."""

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

_CONTENT_TYPE_JSON = "application/json"

ALUNO_SEM_TURMA = "Não foram encontradas turmas para o aluno."
CODIGO_UE_E_ANO_LETIVO_OBRIGATORIOS = (
    "Código da UE e ano letivo são obrigatórios."
)

# ---------------------------------------------------------------------------
# Helpers de parsing
# ---------------------------------------------------------------------------


def _to_int(valor: str, nome_param: str) -> int:
    """Converte um path/query param para inteiro.

    Args:
        valor: Valor recebido na URL.
        nome_param: Nome usado na mensagem de erro.

    Returns:
        Valor convertido para inteiro.

    Raises:
        ValueError: Se ``valor`` não puder ser convertido.
    """
    try:
        return int(valor)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Parâmetro '{nome_param}' deve ser um inteiro válido: "
            f"recebido {valor!r}."
        ) from exc


def _to_bool(valor: str, nome_param: str) -> bool:
    """Converte um path/query param para booleano.

    Args:
        valor: Valor recebido (``true``/``false`` e variantes em PT/EN).
        nome_param: Nome usado na mensagem de erro.

    Raises:
        ValueError: Se ``valor`` for ``None`` ou não representar booleano.
    """
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
    """Converte um path/query param para datetime.

    Aceita formato ISO 8601 com ou sem horário; ``Z`` é tratado como UTC.

    Args:
        valor: Valor recebido na URL.
        nome_param: Nome usado na mensagem de erro.

    Raises:
        ValueError: Se o valor não for uma data ISO válida.
    """
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
    """Extrai uma lista de inteiros da query string.

    Args:
        request: Requisição DRF.
        nome: Nome do parâmetro repetível.

    Returns:
        Inteiros recebidos, ignorando entradas vazias.

    Raises:
        ValueError: Se qualquer entrada não puder ser convertida.
    """
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
    """Constrói uma resposta 400 com a mensagem informada."""
    return Response({"detail": detalhe}, status=status.HTTP_400_BAD_REQUEST)


class BuscaTurmasDoAlunoView(APIView):
    """Lista as turmas do aluno."""

    @extend_schema(
        tags=_TAG_ALUNO,
        summary="Turmas do aluno",
        parameters=[
            OpenApiParameter("codigo_aluno", int, OpenApiParameter.PATH),
        ],
        responses={200: TurmaDoAlunoSerializer(many=True)},
    )
    def get(self, request: Request, codigo_aluno: str) -> Response:
        try:
            codigo = _to_int(codigo_aluno, "codigo_aluno")
        except ValueError as exc:
            return _erro_400(str(exc))

        if codigo <= 0:
            return _erro_400("Código do aluno obrigatório.")

        dados = services.buscar_turmas_do_aluno(codigo_aluno=codigo)
        if not dados:
            return Response(
                {"detail": ALUNO_SEM_TURMA},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(TurmaDoAlunoSerializer(dados, many=True).data)


class BuscaTurmasDoAlunoPorSituacaoMatriculaView(APIView):
    """Lista as turmas do aluno com filtro de situação de matrícula."""

    @extend_schema(
        tags=_TAG_ALUNO,
        summary="Turmas filtradas por situação de matrícula",
        parameters=[
            OpenApiParameter("codigo_aluno", int, OpenApiParameter.PATH),
            OpenApiParameter("ano_letivo", int, OpenApiParameter.PATH),
            OpenApiParameter(
                "filtrar_situacao_matricula", bool, OpenApiParameter.PATH
            ),
            OpenApiParameter("tipo_turma", bool, OpenApiParameter.PATH),
        ],
        responses={200: TurmaDoAlunoSerializer(many=True)},
    )
    def get(
        self,
        request: Request,
        codigo_aluno: str,
        ano_letivo: str,
        filtrar_situacao_matricula: str,
        tipo_turma: str,
    ) -> Response:
        try:
            codigo = _to_int(codigo_aluno, "codigo_aluno")
            ano = _to_int(ano_letivo, "ano_letivo")
            filtra = _to_bool(
                filtrar_situacao_matricula, "filtrar_situacao_matricula"
            )
            _to_bool(tipo_turma, "tipo_turma")
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


class BuscarAlunosDaUeView(APIView):
    """Lista os alunos de uma UE no ano letivo."""

    @extend_schema(
        tags=_TAG_ALUNO,
        summary="Alunos de uma UE por ano letivo",
        parameters=[
            OpenApiParameter("codigo_ue", str, OpenApiParameter.PATH),
            OpenApiParameter("ano_letivo", int, OpenApiParameter.PATH),
            OpenApiParameter("nome_aluno", str, OpenApiParameter.QUERY),
            OpenApiParameter("codigo_eol", str, OpenApiParameter.QUERY),
        ],
        responses={200: TurmaDoAlunoSerializer(many=True)},
    )
    def get(
        self, request: Request, codigo_ue: str, ano_letivo: str
    ) -> Response:
        if not codigo_ue or not ano_letivo:
            return _erro_400(CODIGO_UE_E_ANO_LETIVO_OBRIGATORIOS)
        try:
            ano = _to_int(ano_letivo, "ano_letivo")
        except ValueError as exc:
            return _erro_400(str(exc))

        dados = services.buscar_alunos_da_ue(
            codigo_ue=codigo_ue,
            ano_letivo=ano,
            nome_aluno=request.query_params.get("nome_aluno"),
            codigo_eol=request.query_params.get("codigo_eol"),
        )
        if not dados:
            return Response(
                {"detail": ALUNO_SEM_TURMA},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(TurmaDoAlunoSerializer(dados, many=True).data)


class AutocompleteAlunosUeView(APIView):
    """Lista dados de autocomplete de alunos da UE/ano."""

    @extend_schema(
        tags=_TAG_ALUNO,
        summary="Autocomplete de alunos da UE/ano",
        parameters=[
            OpenApiParameter("codigo_ue", str, OpenApiParameter.PATH),
            OpenApiParameter("ano_letivo", int, OpenApiParameter.PATH),
            OpenApiParameter(
                "codigos_turmas", int, OpenApiParameter.QUERY, many=True
            ),
            OpenApiParameter("nome_aluno", str, OpenApiParameter.QUERY),
            OpenApiParameter("codigo_eol", str, OpenApiParameter.QUERY),
            OpenApiParameter("somente_ativos", bool, OpenApiParameter.QUERY),
            OpenApiParameter("eh_historico", bool, OpenApiParameter.QUERY),
            OpenApiParameter("limite", int, OpenApiParameter.QUERY),
        ],
        responses={200: AlunoAutocompleteSerializer(many=True)},
    )
    def get(
        self, request: Request, codigo_ue: str, ano_letivo: str
    ) -> Response:
        if not codigo_ue:
            return _erro_400(CODIGO_UE_E_ANO_LETIVO_OBRIGATORIOS)
        try:
            ano = _to_int(ano_letivo, "ano_letivo")
            codigos_turmas = _query_int_list(request, "codigos_turmas")
            limite = int(request.query_params.get("limite", "10"))
        except ValueError as exc:
            return _erro_400(str(exc))

        somente_ativos = request.query_params.get(
            "somente_ativos", ""
        ).lower() in ("true", "1")
        eh_historico = request.query_params.get(
            "eh_historico", ""
        ).lower() in (
            "true",
            "1",
        )

        dados = services.buscar_alunos_autocomplete(
            codigo_ue=codigo_ue,
            ano_letivo=ano,
            codigo_turmas=codigos_turmas,
            nome_aluno=request.query_params.get("nome_aluno"),
            codigo_eol=request.query_params.get("codigo_eol"),
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


class AutocompleteAlunosAtivosView(APIView):
    """Lista dados de autocomplete de alunos ativos por data de referência."""

    @extend_schema(
        tags=_TAG_ALUNO,
        summary="Autocomplete de alunos ativos por referência",
        parameters=[
            OpenApiParameter("ue_codigo", str, OpenApiParameter.PATH),
            OpenApiParameter("aluno_nome", str, OpenApiParameter.QUERY),
            OpenApiParameter("data_referencia", str, OpenApiParameter.QUERY),
            OpenApiParameter("aluno_codigo", int, OpenApiParameter.QUERY),
            OpenApiParameter("limite", int, OpenApiParameter.QUERY),
        ],
        responses={200: AlunoAutocompleteSerializer(many=True)},
    )
    def get(self, request: Request, ue_codigo: str) -> Response:
        if not ue_codigo:
            return _erro_400(CODIGO_UE_E_ANO_LETIVO_OBRIGATORIOS)

        aluno_nome = request.query_params.get("aluno_nome")
        try:
            aluno_codigo = int(request.query_params.get("aluno_codigo", "0"))
            limite = int(request.query_params.get("limite", "10"))
            data_ref = request.query_params.get("data_referencia")
            data_ref_dt = (
                _to_datetime(data_ref, "data_referencia") if data_ref else None
            )
        except ValueError as exc:
            return _erro_400(str(exc))

        if aluno_codigo == 0 and (not aluno_nome or len(aluno_nome) < 3):
            return _erro_400("O Nome deve conter no mínimo 3 caracteres.")

        dados = services.buscar_alunos_ativos_autocomplete(
            ue_codigo=ue_codigo,
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


class TotalAlunosAtivosPorPeriodoView(APIView):
    """Lista o total de alunos ativos por período."""

    @extend_schema(
        tags=_TAG_ALUNO,
        summary="Total de alunos ativos por período",
        parameters=[
            OpenApiParameter("ano_turma", str, OpenApiParameter.PATH),
            OpenApiParameter("ano_letivo", int, OpenApiParameter.PATH),
            OpenApiParameter("data_inicio", str, OpenApiParameter.PATH),
            OpenApiParameter("data_fim", str, OpenApiParameter.PATH),
            OpenApiParameter("ue_id", str, OpenApiParameter.QUERY),
            OpenApiParameter("dre_id", str, OpenApiParameter.QUERY),
            OpenApiParameter(
                "modalidades", int, OpenApiParameter.QUERY, many=True
            ),
        ],
        responses={200: TotalAlunosAtivosPeriodoSerializer},
    )
    def get(
        self,
        request: Request,
        ano_turma: str,
        ano_letivo: str,
        data_inicio: str,
        data_fim: str,
    ) -> Response:
        try:
            ano = _to_int(ano_letivo, "ano_letivo")
            inicio = _to_datetime(data_inicio, "data_inicio")
            fim = _to_datetime(data_fim, "data_fim")
            modalidades = _query_int_list(request, "modalidades")
        except ValueError as exc:
            return _erro_400(str(exc))

        dados = services.obter_total_alunos_ativos_periodo(
            ano_turma=ano_turma,
            ano_letivo=ano,
            data_inicio=inicio,
            data_fim=fim,
            ue_id=request.query_params.get("ue_id"),
            dre_id=request.query_params.get("dre_id"),
            modalidades=modalidades,
        )
        return Response(TotalAlunosAtivosPeriodoSerializer(dados).data)


class AlunosAtivosPeriodoTurmaView(APIView):
    """Lista os alunos ativos em uma turma por período."""

    @extend_schema(
        tags=_TAG_ALUNO,
        summary="Alunos ativos em turma por período",
        parameters=[
            OpenApiParameter("codigo_turma", int, OpenApiParameter.PATH),
            OpenApiParameter(
                "data_referencia_fim", str, OpenApiParameter.PATH
            ),
            OpenApiParameter(
                "data_referencia_inicio", str, OpenApiParameter.QUERY
            ),
        ],
        responses={200: AlunoAtivoTurmaSerializer(many=True)},
    )
    def get(
        self,
        request: Request,
        codigo_turma: str,
        data_referencia_fim: str,
    ) -> Response:
        try:
            codigo = _to_int(codigo_turma, "codigo_turma")
            fim = _to_datetime(data_referencia_fim, "data_referencia_fim")
            inicio_raw = request.query_params.get("data_referencia_inicio")
            inicio = (
                _to_datetime(inicio_raw, "data_referencia_inicio")
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


class AlunosAtivosTurmaView(APIView):
    """Lista os alunos ativos em uma turma."""

    @extend_schema(
        tags=_TAG_ALUNO,
        summary="Alunos ativos em turma",
        parameters=[
            OpenApiParameter("codigo_turma", int, OpenApiParameter.PATH)
        ],
        responses={200: AlunoAtivoTurmaSerializer(many=True)},
    )
    def get(self, request: Request, codigo_turma: str) -> Response:
        try:
            codigo = _to_int(codigo_turma, "codigo_turma")
        except ValueError as exc:
            return _erro_400(str(exc))

        dados = services.obter_alunos_ativos_por_turma(codigo_turma=codigo)
        return Response(AlunoAtivoTurmaSerializer(dados, many=True).data)


class NecessidadesEspeciaisAlunoView(APIView):
    """Lista os dados das necessidades especiais do aluno."""

    @extend_schema(
        tags=_TAG_ALUNO,
        summary="Necessidades especiais do aluno",
        parameters=[
            OpenApiParameter("codigo_aluno", int, OpenApiParameter.PATH)
        ],
        responses={200: NecessidadeEspecialSerializer(many=True)},
    )
    def get(self, request: Request, codigo_aluno: str) -> Response:
        try:
            codigo = _to_int(codigo_aluno, "codigo_aluno")
        except ValueError as exc:
            return _erro_400(str(exc))

        dados = services.obter_necessidades_especiais_por_aluno(
            codigo_aluno=codigo
        )
        return Response(NecessidadeEspecialSerializer(dados, many=True).data)


class AlunosPorCodigosEAnoView(APIView):
    """Lista os alunos por códigos e ano letivo."""

    @extend_schema(
        tags=_TAG_ALUNO,
        summary="Alunos por lista de códigos e ano letivo",
        parameters=[
            OpenApiParameter("ano_letivo", int, OpenApiParameter.PATH),
            OpenApiParameter(
                "codigos_aluno",
                int,
                OpenApiParameter.QUERY,
                many=True,
                required=True,
            ),
        ],
        responses={200: TurmaDoAlunoSerializer(many=True)},
    )
    def get(self, request: Request, ano_letivo: str) -> Response:
        try:
            ano = _to_int(ano_letivo, "ano_letivo")
            codigos = _query_int_list(request, "codigos_aluno")
        except ValueError as exc:
            return _erro_400(str(exc))

        dados = services.obter_alunos_por_codigos_e_ano(
            codigos_aluno=codigos, ano_letivo=ano
        )
        return Response(TurmaDoAlunoSerializer(dados, many=True).data)


class AlunosPorCodigosView(APIView):
    """Lista os alunos por lista de códigos."""

    @extend_schema(
        tags=_TAG_ALUNO,
        summary="Alunos por lista de códigos",
        parameters=[
            OpenApiParameter(
                "codigos_aluno",
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
            codigos = _query_int_list(request, "codigos_aluno")
        except ValueError as exc:
            return _erro_400(str(exc))

        dados = services.obter_alunos_por_codigos(codigos_aluno=codigos)
        return Response(TurmaDoAlunoSerializer(dados, many=True).data)


class InformacoesAlunoView(APIView):
    """Lista as informações completas do aluno."""

    @extend_schema(
        tags=_TAG_ALUNO,
        summary="Informações completas do aluno",
        parameters=[
            OpenApiParameter("codigo_aluno", int, OpenApiParameter.PATH)
        ],
        responses={200: InformacoesAlunoSerializer},
    )
    def get(self, request: Request, codigo_aluno: str) -> Response:
        try:
            codigo = _to_int(codigo_aluno, "codigo_aluno")
        except ValueError as exc:
            return _erro_400(str(exc))

        dado = services.obter_informacoes_aluno(codigo_aluno=codigo)
        if dado is None:
            return Response(
                {"detail": "Aluno não encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(InformacoesAlunoSerializer(dado).data)


class InformacoesAlunosTurmaView(APIView):
    """Lista as informações dos alunos de uma turma."""

    @extend_schema(
        tags=_TAG_ALUNO,
        summary="Informações dos alunos da turma",
        parameters=[
            OpenApiParameter("codigo_turma", int, OpenApiParameter.PATH)
        ],
        responses={200: InformacoesAlunoTurmaSerializer(many=True)},
    )
    def get(self, request: Request, codigo_turma: str) -> Response:
        try:
            codigo = _to_int(codigo_turma, "codigo_turma")
        except ValueError as exc:
            return _erro_400(str(exc))

        dados = services.obter_informacoes_alunos_da_turma(codigo_turma=codigo)
        return Response(InformacoesAlunoTurmaSerializer(dados, many=True).data)


class QuantidadeMatriculadosPorAnoCCView(APIView):
    """Lista a quantidade de matriculados por componente curricular e ano."""

    @extend_schema(
        tags=_TAG_ALUNO,
        summary="Quantidade de matriculados por CC e ano",
        parameters=[
            OpenApiParameter("ano_letivo", int, OpenApiParameter.PATH),
            OpenApiParameter("dre_id", str, OpenApiParameter.QUERY),
            OpenApiParameter("ue_id", str, OpenApiParameter.QUERY),
            OpenApiParameter(
                "componentes_curriculares",
                int,
                OpenApiParameter.QUERY,
                many=True,
                required=True,
            ),
        ],
        responses={200: QuantidadeMatriculadosCCSerializer(many=True)},
    )
    def get(self, request: Request, ano_letivo: str) -> Response:
        try:
            ano = _to_int(ano_letivo, "ano_letivo")
            componentes = _query_int_list(request, "componentes_curriculares")
        except ValueError as exc:
            return _erro_400(str(exc))
        if not componentes:
            return _erro_400("componentes_curriculares é obrigatório.")

        payload = services.obter_quantidade_matriculados_por_ano_e_cc_json(
            ano_letivo=ano,
            componentes_curriculares=componentes,
            dre_id=request.query_params.get("dre_id"),
            ue_id=request.query_params.get("ue_id"),
        )
        return HttpResponse(payload, content_type=_CONTENT_TYPE_JSON)


class QuantidadeMatriculadosView(APIView):
    """Lista a quantidade de matriculados com múltiplos filtros."""

    @extend_schema(
        tags=_TAG_ALUNO,
        summary="Quantidade de matriculados (filtros)",
        parameters=[
            OpenApiParameter("ano_letivo", int, OpenApiParameter.PATH),
            OpenApiParameter("dre_codigo", str, OpenApiParameter.QUERY),
            OpenApiParameter("ue_codigo", str, OpenApiParameter.QUERY),
            OpenApiParameter(
                "modalidade", int, OpenApiParameter.QUERY, many=True
            ),
            OpenApiParameter("ano", int, OpenApiParameter.QUERY, many=True),
            OpenApiParameter("turma", str, OpenApiParameter.QUERY, many=True),
        ],
        responses={200: QuantidadeMatriculadosSerializer(many=True)},
    )
    def get(self, request: Request, ano_letivo: str) -> Response:
        try:
            ano = _to_int(ano_letivo, "ano_letivo")
            modalidade = _query_int_list(request, "modalidade")
            ano_lst = _query_int_list(request, "ano")
        except ValueError as exc:
            return _erro_400(str(exc))

        turma = request.query_params.getlist("turma")
        payload = services.obter_quantidade_matriculados_json(
            ano_letivo=ano,
            dre_codigo=request.query_params.get("dre_codigo", ""),
            ue_codigo=request.query_params.get("ue_codigo", ""),
            modalidade=modalidade,
            ano=ano_lst,
            turma=turma,
        )
        return HttpResponse(payload, content_type=_CONTENT_TYPE_JSON)


class DadosAcompanhamentoEscolarView(APIView):
    """Lista dados de acompanhamento escolar."""

    @extend_schema(
        tags=_TAG_ALUNO,
        summary="Dados de acompanhamento escolar",
        parameters=[
            OpenApiParameter("codigo_aluno", int, OpenApiParameter.QUERY),
            OpenApiParameter("codigo_dre", str, OpenApiParameter.QUERY),
            OpenApiParameter("codigo_ue", str, OpenApiParameter.QUERY),
            OpenApiParameter("cpf_responsavel", str, OpenApiParameter.QUERY),
        ],
        responses={200: DadosAcompanhamentoEscolarSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        codigo_aluno_raw = request.query_params.get("codigo_aluno")
        codigo_dre = request.query_params.get("codigo_dre")
        codigo_ue = request.query_params.get("codigo_ue")
        cpf_responsavel = request.query_params.get("cpf_responsavel")
        if not any((codigo_aluno_raw, codigo_dre, codigo_ue, cpf_responsavel)):
            return _erro_400(
                "Nenhum filtro foi especificado para busca de dados "
                "dos alunos para acompanhamento do estudante"
            )
        try:
            codigo_aluno = (
                _to_int(codigo_aluno_raw, "codigo_aluno")
                if codigo_aluno_raw
                else None
            )
        except ValueError as exc:
            return _erro_400(str(exc))

        outros_filtros = any(
            (codigo_aluno is not None, codigo_ue, cpf_responsavel)
        )
        if codigo_dre and not outros_filtros:
            return HttpResponse(b"[]", content_type=_CONTENT_TYPE_JSON)

        payload = services.obter_dados_acompanhamento_escolar_json(
            codigo_aluno=codigo_aluno,
            codigo_dre=codigo_dre,
            codigo_ue=codigo_ue,
            cpf_responsavel=cpf_responsavel,
        )
        return HttpResponse(payload, content_type=_CONTENT_TYPE_JSON)


class ResponsaveisDreUeTurmaView(APIView):
    """Lista dados dos responsáveis por DRE/UE/turma."""

    @extend_schema(
        tags=_TAG_RESPONSAVEL,
        summary="Responsáveis por DRE/UE/turma",
        parameters=[
            OpenApiParameter("codigo_dre", str, OpenApiParameter.QUERY),
            OpenApiParameter("codigo_ue", str, OpenApiParameter.QUERY),
            OpenApiParameter("ano_letivo", int, OpenApiParameter.QUERY),
        ],
        responses={200: ResponsavelTurmaSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        codigo_dre = request.query_params.get("codigo_dre")
        try:
            ano = (
                int(request.query_params["ano_letivo"])
                if "ano_letivo" in request.query_params
                else None
            )
        except (TypeError, ValueError) as exc:
            return _erro_400(str(exc))

        codigo_ue = request.query_params.get("codigo_ue")

        if codigo_dre and not codigo_ue and ano is None:
            return HttpResponse(b"[]", content_type=_CONTENT_TYPE_JSON)

        payload = services.obter_responsaveis_dre_ue_turma_json(
            codigo_dre=codigo_dre,
            codigo_ue=codigo_ue,
            ano_letivo=ano,
        )
        return HttpResponse(payload, content_type=_CONTENT_TYPE_JSON)


class DadosResponsavelView(APIView):
    """Lista os dados completos do responsável."""

    @extend_schema(
        tags=_TAG_RESPONSAVEL,
        summary="Dados completos do responsável",
        parameters=[
            OpenApiParameter("cpf_responsavel", str, OpenApiParameter.PATH)
        ],
        responses={200: DadosResponsavelSerializer(many=True)},
    )
    def get(self, request: Request, cpf_responsavel: str) -> Response:
        dados = services.obter_dados_responsavel(
            cpf_responsavel=cpf_responsavel
        )
        return Response(DadosResponsavelSerializer(dados, many=True).data)


class DadosResponsavelResumidoView(APIView):
    """Lista dados resumidos do responsável."""

    @extend_schema(
        tags=_TAG_RESPONSAVEL,
        summary="Dados resumidos do responsável",
        parameters=[
            OpenApiParameter("cpf_responsavel", str, OpenApiParameter.PATH)
        ],
        responses={200: DadosResponsavelResumidoSerializer},
    )
    def get(self, request: Request, cpf_responsavel: str) -> Response:
        dado = services.obter_dados_responsavel_resumido(
            cpf_responsavel=cpf_responsavel
        )
        if dado is None:
            return Response(
                {"detail": "Responsável não encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(DadosResponsavelResumidoSerializer(dado).data)


class ResponsavelAlunoView(APIView):
    """Atualiza ou cadastra dados de um responsável."""

    @extend_schema(
        tags=_TAG_RESPONSAVEL,
        summary="Atualizar dados do responsável (busca ativa)",
        parameters=[
            OpenApiParameter("codigo_aluno", int, OpenApiParameter.PATH),
            OpenApiParameter("cpf_responsavel", str, OpenApiParameter.PATH),
        ],
        request=AtualizarResponsavelBuscaAtivaRequestSerializer,
        responses={200: DadosResponsavelResumidoSerializer},
    )
    def put(
        self, request: Request, codigo_aluno: str, cpf_responsavel: str
    ) -> Response:
        try:
            codigo = _to_int(codigo_aluno, "codigo_aluno")
        except ValueError as exc:
            return _erro_400(str(exc))

        serializer = AtualizarResponsavelBuscaAtivaRequestSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)
        body: dict[str, Any] = serializer.validated_data

        resumo = services.atualizar_dados_responsavel_busca_ativa(
            codigo_aluno=codigo,
            cpf_responsavel=cpf_responsavel,
            email=body.get("email"),
            ddd_celular=body.get("ddd_celular"),
            numero_celular=body.get("numero_celular"),
        )
        return Response(DadosResponsavelResumidoSerializer(resumo).data)

    @extend_schema(
        tags=_TAG_RESPONSAVEL,
        summary="Cadastrar dados do responsável do aluno",
        parameters=[
            OpenApiParameter("codigo_aluno", int, OpenApiParameter.PATH),
            OpenApiParameter("cpf_responsavel", str, OpenApiParameter.PATH),
        ],
        request=CadastrarResponsavelRequestSerializer,
        responses={200: DadosResponsavelResumidoSerializer},
    )
    def post(
        self, request: Request, codigo_aluno: str, cpf_responsavel: str
    ) -> Response:
        try:
            codigo = _to_int(codigo_aluno, "codigo_aluno")
        except ValueError as exc:
            return _erro_400(str(exc))

        serializer = CadastrarResponsavelRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        body: dict[str, Any] = serializer.validated_data

        resumo = services.cadastrar_dados_responsavel(
            codigo_aluno=codigo,
            cpf_responsavel=cpf_responsavel,
            nome=body.get("nome", ""),
            email=body.get("email", ""),
            tipo_responsavel=body.get("tipo_responsavel"),
            ddd_celular=body.get("ddd_celular", ""),
            numero_celular=body.get("numero_celular", ""),
        )
        return Response(DadosResponsavelResumidoSerializer(resumo).data)


class FiliacaoAlunoView(APIView):
    """Lista os dados de filiação do responsável do aluno."""

    @extend_schema(
        tags=_TAG_RESPONSAVEL,
        summary="Dados de filiação do responsável do aluno",
        parameters=[
            OpenApiParameter("codigo_aluno", int, OpenApiParameter.PATH)
        ],
        responses={200: InformacoesAlunoSerializer},
    )
    def get(self, request: Request, codigo_aluno: str) -> Response:
        try:
            codigo = _to_int(codigo_aluno, "codigo_aluno")
        except ValueError as exc:
            return _erro_400(str(exc))

        dado = services.obter_dados_responsavel_filiacao(codigo_aluno=codigo)
        if dado is None:
            return Response(
                {"detail": "Aluno não encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(InformacoesAlunoSerializer(dado).data)


class MatriculasAnoAtualView(APIView):
    """Lista matrículas consolidadas do ano atual."""

    @extend_schema(
        tags=_TAG_MATRICULA,
        summary="Matrículas consolidadas do ano atual",
        parameters=[
            OpenApiParameter(
                "ano_letivo", int, OpenApiParameter.QUERY, required=True
            ),
            OpenApiParameter(
                "ue_codigo", str, OpenApiParameter.QUERY, required=True
            ),
        ],
        responses={200: ConsolidacaoMatriculaSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        ano_raw = request.query_params.get("ano_letivo")
        ue_codigo = request.query_params.get("ue_codigo")
        if not ano_raw or not ue_codigo:
            return _erro_400("ano_letivo e ue_codigo são obrigatórios.")
        try:
            ano = _to_int(ano_raw, "ano_letivo")
        except ValueError as exc:
            return _erro_400(str(exc))

        dados = services.obter_matriculas_ano_atual(
            ano_letivo=ano, ue_codigo=ue_codigo
        )
        return Response(ConsolidacaoMatriculaSerializer(dados, many=True).data)


class MatriculasAnosAnterioresView(APIView):
    """Lista matrículas consolidadas de anos anteriores."""

    @extend_schema(
        tags=_TAG_MATRICULA,
        summary="Matrículas consolidadas de anos anteriores",
        parameters=[
            OpenApiParameter(
                "ano_letivo", int, OpenApiParameter.QUERY, required=True
            ),
            OpenApiParameter(
                "ue_codigo", str, OpenApiParameter.QUERY, required=True
            ),
        ],
        responses={200: ConsolidacaoMatriculaSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        ano_raw = request.query_params.get("ano_letivo")
        ue_codigo = request.query_params.get("ue_codigo")
        if not ano_raw or not ue_codigo:
            return _erro_400("ano_letivo e ue_codigo são obrigatórios.")
        try:
            ano = _to_int(ano_raw, "ano_letivo")
        except ValueError as exc:
            return _erro_400(str(exc))

        dados = services.obter_matriculas_anos_anteriores(
            ano_letivo=ano, ue_codigo=ue_codigo
        )
        return Response(ConsolidacaoMatriculaSerializer(dados, many=True).data)


class TotalMatriculasPorTurnoUeView(APIView):
    """Lista o total de matrículas por turno (UE)."""

    @extend_schema(
        tags=_TAG_MATRICULA,
        summary="Total de matrículas por turno (UE) — out-of-scope",
        parameters=[
            OpenApiParameter("ue_codigo", str, OpenApiParameter.PATH),
        ],
        responses={200: {"type": "array", "items": {}}},
    )
    def get(self, request: Request, ue_codigo: str) -> Response:
        if not ue_codigo:
            return _erro_400("Código da UE obrigatório.")
        return Response(
            services.obter_total_matriculas_por_turno_ue(ue_codigo=ue_codigo)
        )


class TotalMatriculasPorTurnoDreView(APIView):
    """Lista o total de matrículas por turno (DRE)."""

    @extend_schema(
        tags=_TAG_MATRICULA,
        summary="Total de matrículas por turno (DRE) — out-of-scope",
        parameters=[
            OpenApiParameter("dre_codigo", str, OpenApiParameter.PATH),
        ],
        responses={200: {"type": "array", "items": {}}},
    )
    def get(self, request: Request, dre_codigo: str) -> Response:
        if not dre_codigo:
            return _erro_400("Código da DRE obrigatório.")
        return Response(
            services.obter_total_matriculas_por_turno_dre(
                dre_codigo=dre_codigo
            )
        )


class QuantidadeAlunosPorTurmaEscolaView(APIView):
    """Lista a quantidade de alunos por turma na escola."""

    @extend_schema(
        tags=_TAG_ESCOLA,
        summary="Quantidade de alunos por turma na escola",
        parameters=[
            OpenApiParameter("codigo_escola", str, OpenApiParameter.PATH)
        ],
        responses={200: ConsolidacaoMatriculaSerializer(many=True)},
    )
    def get(self, request: Request, codigo_escola: str) -> Response:
        if not codigo_escola:
            return _erro_400("Código EOL da escola obrigatório.")
        dados = services.obter_quantidade_alunos_por_turma_da_escola(
            codigo_escola=codigo_escola
        )
        return Response(ConsolidacaoMatriculaSerializer(dados, many=True).data)


class MatriculasAlunoEscolaView(APIView):
    """Lista as matrículas de um aluno na escola."""

    @extend_schema(
        tags=_TAG_ESCOLA,
        summary="Matrículas de um aluno na escola",
        parameters=[
            OpenApiParameter("codigo_escola", str, OpenApiParameter.PATH),
            OpenApiParameter("codigo_aluno", int, OpenApiParameter.PATH),
        ],
        responses={200: MatriculaEscolaAlunoSerializer(many=True)},
    )
    def get(
        self, request: Request, codigo_escola: str, codigo_aluno: str
    ) -> Response:
        if not codigo_escola:
            return _erro_400("O código da escola e do aluno são obrigatórios")
        try:
            codigo_a = _to_int(codigo_aluno, "codigo_aluno")
        except ValueError:
            return _erro_400("O código da escola e do aluno são obrigatórios")
        dados = services.obter_matriculas_aluno_na_escola(
            codigo_escola=codigo_escola, codigo_aluno=codigo_a
        )
        return Response(MatriculaEscolaAlunoSerializer(dados, many=True).data)
