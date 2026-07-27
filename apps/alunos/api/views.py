"""Views do domínio Alunos."""

from datetime import datetime
from typing import Any

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.alunos import services
from apps.alunos.api.serializers import (
    AlunoAcompanhamentoEscolarSerializer,
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
from apps.core.utils import (
    query_bool,
    query_int_list,
    ticks_to_datetime,
    to_bool,
    to_datetime,
    to_int,
)

_TAG_ALUNO = ["Alunos"]
_TAG_RESPONSAVEL = ["Alunos — Responsáveis"]
_TAG_MATRICULA = ["Matrículas"]
_TAG_ESCOLA = ["Escolas"]

ALUNO_SEM_TURMA = "Não foram encontradas turmas para o aluno."
CODIGO_ALUNO_OBRIGATORIO = "Código do aluno obrigatório."
CODIGO_UE_E_ANO_LETIVO_OBRIGATORIOS = (
    "Código da UE e ano letivo são obrigatórios."
)


def _erro_400(detalhe: str) -> Response:
    """Constrói uma resposta 400 com a mensagem informada."""
    return Response({"detail": detalhe}, status=status.HTTP_400_BAD_REQUEST)


ERRO_LEGADO_SEM_MODALIDADES = (
    "Houve um problema na conexão com o banco do EOL. "
    "Por favor, contate a SME."
)
ERRO_LEGADO_SEM_RESULTADO = (
    "Houve um comportamento inesperado do sistema. Por favor, contate a SME."
)
ERRO_LEGADO_ACOMPANHAMENTO_SEM_FILTRO = (
    "Nenhum filtro foi especificado para busca de dados dos alunos "
    "para acompanhamento do estudante"
)
ERRO_LEGADO_ANO_LETIVO_OBRIGATORIO = "Ano Letivo deve ser informado"
ERRO_LEGADO_CODIGOS_ALUNOS = "Os códigos dos Alunos são obrigatórios."
ERRO_LEGADO_COMPONENTES_CURRICULARES = (
    "Os códigos dos componentes curriculares são obrigatórios."
)


def _erro_legado(mensagem: str) -> Response:
    """Replica a resposta de erro do legado com a mensagem informada."""
    return Response(mensagem, status=status.HTTP_400_BAD_REQUEST)


# Código de status usado pelo legado nos erros de negócio.
_STATUS_NEGOCIO_LEGADO = 601


def _erro_negocio_legado(mensagem: str) -> Response:
    """Replica o erro de negócio do legado (status 601, corpo string)."""
    resposta = Response(mensagem, status=status.HTTP_400_BAD_REQUEST)
    # O construtor do Django limita o status a 100-599; o legado usa 601,
    # então o código é atribuído após a construção.
    resposta.status_code = _STATUS_NEGOCIO_LEGADO
    return resposta


class BuscaTurmasDoAlunoView(APIView):
    """Lista as turmas do aluno."""

    @extend_schema(
        tags=_TAG_ALUNO,
        summary="Turmas do aluno",
        parameters=[
            OpenApiParameter("codigo_aluno", int, OpenApiParameter.PATH),
            OpenApiParameter(
                "tipo_turma", bool, OpenApiParameter.QUERY, required=False
            ),
            OpenApiParameter(
                "filtrar_situacao",
                bool,
                OpenApiParameter.QUERY,
                required=False,
            ),
        ],
        responses={200: TurmaDoAlunoSerializer(many=True)},
    )
    def get(self, request: Request, codigo_aluno: str) -> Response:
        """Retorna as turmas do aluno no ano corrente.

        Args:
            request: Requisição com os filtros opcionais ``tipo_turma`` e
                ``filtrar_situacao``.
            codigo_aluno: Código EOL do aluno.

        Returns:
            Turmas do aluno, ou ausência de conteúdo quando não há turmas.
        """
        try:
            codigo = to_int(codigo_aluno, "codigo_aluno")
            tipo_turma = query_bool(request, "tipo_turma", default=True)
            filtrar_situacao = query_bool(
                request, "filtrar_situacao", default=True
            )
        except ValueError as exc:
            return _erro_400(str(exc))

        if codigo <= 0:
            return _erro_400(CODIGO_ALUNO_OBRIGATORIO)

        dados = services.buscar_turmas_do_aluno(
            codigo_aluno=codigo,
            tipo_turma=tipo_turma,
            filtrar_situacao=filtrar_situacao,
        )
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
        """Retorna as turmas do aluno filtradas por situação de matrícula.

        Args:
            codigo_aluno: Código EOL do aluno.
            ano_letivo: Ano letivo consultado.
            filtrar_situacao_matricula: Restringe às situações de matrícula
                válidas quando verdadeiro.
            tipo_turma: Indicador de tipo de turma recebido na rota.

        Returns:
            Turmas do aluno conforme os filtros, ou ausência de conteúdo
            quando não há turmas.
        """
        try:
            codigo = to_int(codigo_aluno, "codigo_aluno")
            ano = to_int(ano_letivo, "ano_letivo")
            filtra = to_bool(
                filtrar_situacao_matricula, "filtrar_situacao_matricula"
            )
            tipo = to_bool(tipo_turma, "tipo_turma")
        except ValueError as exc:
            return _erro_400(str(exc))

        if codigo <= 0:
            return _erro_400(CODIGO_ALUNO_OBRIGATORIO)

        dados = services.buscar_turmas_do_aluno_por_situacao_matricula(
            codigo_aluno=codigo,
            ano_letivo=ano,
            filtrar_situacao_matricula=filtra,
            tipo_turma=tipo,
        )
        if not dados:
            return Response(
                {"detail": ALUNO_SEM_TURMA},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(TurmaDoAlunoSerializer(dados, many=True).data)


class CodigosTurmasRegularesAlunoView(APIView):
    """Lista códigos de turma do aluno no ano (recorte de matrícula)."""

    @extend_schema(
        tags=_TAG_ALUNO,
        summary="Códigos de turma do aluno no ano letivo",
        parameters=[
            OpenApiParameter("ano_letivo", int, OpenApiParameter.PATH),
            OpenApiParameter("codigo_aluno", int, OpenApiParameter.PATH),
            OpenApiParameter(
                "data_referencia",
                str,
                OpenApiParameter.QUERY,
                required=False,
            ),
        ],
        responses={200: {"type": "array", "items": {"type": "integer"}}},
    )
    def get(
        self,
        request: Request,
        ano_letivo: str,
        codigo_aluno: str,
    ) -> Response:
        """Retorna os códigos de turma do aluno no ano letivo.

        Resolve a última situação por matrícula+turma, exclui Vínculo
        Indevido e aplica o filtro ativa/inativa vs. data de referência.
        O recorte por tipo de turma/UE/semestre é do domínio Pedagógico;
        a interseção é feita no gateway.

        Args:
            request: Requisição com o filtro opcional ``data_referencia``.
            ano_letivo: Ano letivo consultado.
            codigo_aluno: Código EOL do aluno.

        Returns:
            Códigos de turma ordenados por data da situação decrescente,
            ou lista vazia quando não há vínculos válidos.
        """
        try:
            ano = to_int(ano_letivo, "ano_letivo")
            codigo = to_int(codigo_aluno, "codigo_aluno")
            data_referencia = None
            data_bruta = request.query_params.get("data_referencia")
            if data_bruta:
                data_referencia = to_datetime(
                    data_bruta, "data_referencia"
                ).date()
        except ValueError as exc:
            return _erro_400(str(exc))

        if ano <= 0 or codigo <= 0:
            return _erro_400("Ano letivo e código do aluno são obrigatórios.")

        codigos = services.obter_codigos_turmas_regulares_aluno(
            codigo_aluno=codigo,
            ano_letivo=ano,
            data_referencia=data_referencia,
        )
        return Response(codigos)


class BuscaTurmasDoAlunoComHistoricoView(APIView):
    """Lista as turmas do aluno com origem histórica explícita."""

    @extend_schema(
        tags=_TAG_ALUNO,
        summary="Turmas do aluno por histórico, situação e tipo",
        parameters=[
            OpenApiParameter("codigo_aluno", int, OpenApiParameter.PATH),
            OpenApiParameter("ano_letivo", int, OpenApiParameter.PATH),
            OpenApiParameter("historico", bool, OpenApiParameter.PATH),
            OpenApiParameter("filtrar_situacao", bool, OpenApiParameter.PATH),
            OpenApiParameter("tipo_turma", bool, OpenApiParameter.PATH),
        ],
        responses={200: TurmaDoAlunoSerializer(many=True)},
    )
    def get(
        self,
        request: Request,
        codigo_aluno: str,
        ano_letivo: str,
        historico: str,
        filtrar_situacao: str,
        tipo_turma: str,
    ) -> Response:
        """Retorna as turmas do aluno conforme origem e filtros.

        Args:
            codigo_aluno: Código EOL do aluno.
            ano_letivo: Ano letivo consultado.
            historico: Consulta os vínculos históricos quando verdadeiro.
            filtrar_situacao: Restringe às situações de matrícula válidas.
            tipo_turma: Exclui turmas do tipo programa quando verdadeiro.

        Returns:
            Turmas do aluno, ou ausência de conteúdo quando não há turmas.
        """
        try:
            codigo = to_int(codigo_aluno, "codigo_aluno")
            ano = to_int(ano_letivo, "ano_letivo")
            eh_historico = to_bool(historico, "historico")
            filtra = to_bool(filtrar_situacao, "filtrar_situacao")
            tipo = to_bool(tipo_turma, "tipo_turma")
        except ValueError as exc:
            return _erro_400(str(exc))

        if codigo <= 0:
            return _erro_400(CODIGO_ALUNO_OBRIGATORIO)

        dados = services.buscar_turmas_do_aluno_com_historico(
            codigo_aluno=codigo,
            ano_letivo=ano,
            historico=eh_historico,
            filtrar_situacao=filtra,
            tipo_turma=tipo,
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
        responses={200: AlunoDaUeSerializer(many=True)},
    )
    def get(
        self, request: Request, codigo_ue: str, ano_letivo: str
    ) -> Response:
        """Lista os alunos de uma UE no ano letivo.

        Args:
            request: Requisição com os filtros opcionais de nome e código EOL.
            codigo_ue: Código da unidade educacional.
            ano_letivo: Ano letivo consultado.

        Returns:
            Alunos da UE, ou ausência de conteúdo quando não há alunos.
        """
        if not codigo_ue or not ano_letivo:
            return _erro_400(CODIGO_UE_E_ANO_LETIVO_OBRIGATORIOS)
        try:
            ano = to_int(ano_letivo, "ano_letivo")
        except ValueError as exc:
            return _erro_400(str(exc))
        if ano <= 0:
            return _erro_400(CODIGO_UE_E_ANO_LETIVO_OBRIGATORIOS)

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
        return Response(AlunoDaUeSerializer(dados, many=True).data)


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
        """Lista dados de autocomplete de alunos da UE no ano letivo.

        Args:
            request: Requisição com os filtros de turma, nome, código e limite.
            codigo_ue: Código da unidade educacional.
            ano_letivo: Ano letivo consultado.

        Returns:
            Alunos para autocomplete, ou ausência de conteúdo quando não há
            alunos.
        """
        if not codigo_ue:
            return _erro_400(CODIGO_UE_E_ANO_LETIVO_OBRIGATORIOS)
        try:
            ano = to_int(ano_letivo, "ano_letivo")
            codigos_turmas = query_int_list(request, "codigos_turmas")
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
        """Lista dados de autocomplete de alunos ativos por referência.

        Args:
            request: Requisição com nome, código, data de referência e limite.
            ue_codigo: Código da unidade educacional.

        Returns:
            Alunos ativos para autocomplete, ou ausência de conteúdo quando
            não há alunos.
        """
        if not ue_codigo:
            return _erro_400(CODIGO_UE_E_ANO_LETIVO_OBRIGATORIOS)

        aluno_nome = request.query_params.get("aluno_nome")
        try:
            aluno_codigo = int(request.query_params.get("aluno_codigo", "0"))
            limite = int(request.query_params.get("limite", "10"))
            data_ref = request.query_params.get("data_referencia")
            data_ref_dt = (
                to_datetime(data_ref, "data_referencia") if data_ref else None
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
        """Retorna o total de alunos ativos no período informado.

        Args:
            request: Requisição com os filtros de UE, DRE e modalidades.
            ano_turma: Ano da turma consultado.
            ano_letivo: Ano letivo consultado.
            data_inicio: Início do período de referência.
            data_fim: Fim do período de referência.

        Returns:
            Total de alunos ativos no período.
        """
        try:
            ano = to_int(ano_letivo, "ano_letivo")
            inicio = to_datetime(data_inicio, "data_inicio")
            fim = to_datetime(data_fim, "data_fim")
            modalidades = query_int_list(request, "modalidades")
        except ValueError as exc:
            return _erro_400(str(exc))

        # Replica o erro do legado quando não há modalidades.
        if not modalidades:
            return _erro_legado(ERRO_LEGADO_SEM_MODALIDADES)

        dados = services.obter_total_alunos_ativos_periodo(
            ano_turma=ano_turma,
            ano_letivo=ano,
            data_inicio=inicio,
            data_fim=fim,
            ue_id=request.query_params.get("ue_id"),
            dre_id=request.query_params.get("dre_id"),
            modalidades=modalidades,
        )
        # Replica o erro do legado quando não há resultado.
        if dados["quantidade"] == 0:
            return _erro_legado(ERRO_LEGADO_SEM_RESULTADO)

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
        """Lista os alunos ativos em uma turma no período informado.

        Args:
            request: Requisição com a data de referência inicial opcional.
            codigo_turma: Código da turma consultada.
            data_referencia_fim: Fim do período de referência.

        Returns:
            Alunos ativos na turma no período.
        """
        try:
            codigo = to_int(codigo_turma, "codigo_turma")
            fim = to_datetime(data_referencia_fim, "data_referencia_fim")
            inicio_raw = request.query_params.get("data_referencia_inicio")
            inicio = (
                to_datetime(inicio_raw, "data_referencia_inicio")
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
        """Lista os alunos ativos em uma turma.

        Args:
            codigo_turma: Código da turma consultada.

        Returns:
            Alunos ativos na turma.
        """
        try:
            codigo = to_int(codigo_turma, "codigo_turma")
        except ValueError as exc:
            return _erro_400(str(exc))

        dados = services.obter_alunos_ativos_por_turma(codigo_turma=codigo)
        return Response(AlunoAtivoTurmaSerializer(dados, many=True).data)


def _ticks_para_datetime(request: Request, nome: str) -> datetime | None:
    """Retorna o ``datetime`` correspondente a um query param em .NET ticks.

    Args:
        request: Requisição com o query param opcional.
        nome: Nome do query param em ticks.

    Returns:
        ``datetime`` correspondente, ou ``None`` quando ausente ou ``0``.

    Raises:
        ValueError: Quando os ticks são inválidos ou negativos.
    """
    bruto = request.query_params.get(nome)
    if bruto is None:
        return None
    ticks = to_int(bruto, nome)
    if ticks < 0:
        raise ValueError("O código da turma e data da aula são obrigatórios.")
    return ticks_to_datetime(ticks) if ticks > 0 else None


class AlunosTurmaView(APIView):
    """Lista os alunos de uma turma conforme os filtros informados."""

    @extend_schema(
        tags=_TAG_ALUNO,
        summary="Alunos de uma turma",
        parameters=[
            OpenApiParameter("codigo_turma", int, OpenApiParameter.PATH),
            OpenApiParameter(
                "data_aula_ticks",
                int,
                OpenApiParameter.QUERY,
                required=False,
            ),
            OpenApiParameter(
                "data_matricula_ticks",
                int,
                OpenApiParameter.QUERY,
                required=False,
            ),
            OpenApiParameter(
                "codigo_aluno", str, OpenApiParameter.QUERY, required=False
            ),
            OpenApiParameter(
                "considerar_inativos",
                bool,
                OpenApiParameter.QUERY,
                required=True,
            ),
            OpenApiParameter(
                "sequencia",
                int,
                OpenApiParameter.QUERY,
                required=False,
            ),
            OpenApiParameter(
                "ano_letivo",
                int,
                OpenApiParameter.QUERY,
                required=False,
            ),
        ],
        responses={200: AlunoAtivoDataAulaSerializer(many=True)},
    )
    def get(self, request: Request, codigo_turma: str) -> Response:
        """Lista os alunos de uma turma conforme os filtros informados.

        Args:
            request: Requisição com o filtro obrigatório
                ``considerar_inativos`` e os opcionais ``data_aula_ticks``,
                ``data_matricula_ticks``, ``codigo_aluno``, ``sequencia`` e
                ``ano_letivo``.
            codigo_turma: Código da turma consultada.

        Returns:
            Alunos distintos na turma conforme os filtros informados.
        """
        if "considerar_inativos" not in request.query_params:
            return _erro_400("considerar_inativos é obrigatório.")
        try:
            codigo = to_int(codigo_turma, "codigo_turma")
            data_aula = _ticks_para_datetime(request, "data_aula_ticks")
            data_matricula = _ticks_para_datetime(
                request, "data_matricula_ticks"
            )
            codigo_aluno_raw = request.query_params.get("codigo_aluno")
            codigo_aluno = (
                to_int(codigo_aluno_raw, "codigo_aluno")
                if codigo_aluno_raw
                else None
            )
            considerar_inativos = query_bool(
                request, "considerar_inativos", False
            )
            sequencia_raw = request.query_params.get("sequencia")
            sequencia = (
                to_int(sequencia_raw, "sequencia") if sequencia_raw else None
            )
            ano_letivo_raw = request.query_params.get("ano_letivo")
            ano_letivo = (
                to_int(ano_letivo_raw, "ano_letivo")
                if ano_letivo_raw
                else None
            )
        except ValueError as exc:
            return _erro_400(str(exc))

        dados = services.obter_alunos_turma(
            codigo_turma=codigo,
            data_aula=data_aula,
            data_matricula=data_matricula,
            codigo_aluno=codigo_aluno,
            considerar_inativos=considerar_inativos,
            sequencia=sequencia,
            ano_letivo=ano_letivo if ano_letivo and ano_letivo > 0 else None,
        )
        return Response(AlunoAtivoDataAulaSerializer(dados, many=True).data)


class QuantidadeMatriculasTurmasPeriodoView(APIView):
    """Conta alocações válidas em turmas cuja matrícula começou até a data."""

    @extend_schema(
        tags=_TAG_MATRICULA,
        summary="Quantidade de matrículas-turma por período",
        request=None,
        responses={200: dict},
    )
    def post(self, request: Request) -> Response:
        """Conta as alocações válidas das turmas até a data informada.

        Args:
            request: Requisição com ``codigos_turmas`` (lista) e ``data_fim``
                (ticks .NET) no corpo.

        Returns:
            Dicionário com a quantidade de alocações no período.
        """
        codigos_turmas = request.data.get("codigos_turmas")
        data_fim_ticks = request.data.get("data_fim")
        if not isinstance(codigos_turmas, list):
            return _erro_400("codigos_turmas deve ser uma lista.")
        try:
            codigos = [to_int(c, "codigos_turmas") for c in codigos_turmas]
            ticks = to_int(data_fim_ticks, "data_fim")
        except ValueError as exc:
            return _erro_400(str(exc))
        if ticks <= 0:
            return _erro_400("data_fim é obrigatório.")

        quantidade = services.contar_matriculas_turmas_periodo(
            codigos_turmas=codigos,
            data_fim=ticks_to_datetime(ticks),
        )
        return Response({"quantidade": quantidade})


class AcompanhamentoEscolarTurmaView(APIView):
    """Lista alunos e responsáveis vigentes de uma turma de acompanhamento."""

    @extend_schema(
        tags=_TAG_ALUNO,
        summary="Acompanhamento escolar da turma",
        parameters=[
            OpenApiParameter("codigo_turma", int, OpenApiParameter.PATH),
        ],
        responses={200: AlunoAcompanhamentoEscolarSerializer(many=True)},
    )
    def get(self, _request: Request, codigo_turma: str) -> Response:
        """Lista alunos e responsáveis vigentes da turma.

        Args:
            _request: Requisição HTTP recebida.
            codigo_turma: Código da turma consultada.

        Returns:
            Um registro por aluno com responsável vigente na turma.
        """
        try:
            codigo = to_int(codigo_turma, "codigo_turma")
        except ValueError as exc:
            return _erro_400(str(exc))

        dados = services.obter_acompanhamento_escolar_turma(
            codigo_turma=codigo,
        )
        return Response(
            AlunoAcompanhamentoEscolarSerializer(dados, many=True).data
        )


class TodosAlunosTurmaView(APIView):
    """Lista o histórico de vínculos dos alunos com a turma."""

    @extend_schema(
        tags=_TAG_ALUNO,
        summary="Histórico de vínculos dos alunos com a turma",
        parameters=[
            OpenApiParameter("codigo_turma", int, OpenApiParameter.PATH),
            OpenApiParameter(
                "codigo_aluno", int, OpenApiParameter.QUERY, required=False
            ),
        ],
        responses={200: AlunoAtivoDataAulaSerializer(many=True)},
    )
    def get(self, request: Request, codigo_turma: str) -> Response:
        """Lista o histórico de vínculos dos alunos com a turma.

        Args:
            request: Requisição com o filtro opcional ``codigo_aluno``.
            codigo_turma: Código da turma consultada.

        Returns:
            Vínculos dos alunos com a turma, sem filtro de situação.
        """
        try:
            codigo = to_int(codigo_turma, "codigo_turma")
            codigo_aluno_raw = request.query_params.get("codigo_aluno")
            codigo_aluno = (
                to_int(codigo_aluno_raw, "codigo_aluno")
                if codigo_aluno_raw
                else None
            )
        except ValueError as exc:
            return _erro_400(str(exc))

        dados = services.obter_todos_alunos_turma(
            codigo_turma=codigo,
            codigo_aluno=codigo_aluno,
        )
        return Response(AlunoAtivoDataAulaSerializer(dados, many=True).data)


class MatriculasTurmasAlunoView(APIView):
    """Lista as matrículas-turma do aluno em todas as turmas e anos."""

    @extend_schema(
        tags=_TAG_ALUNO,
        summary="Matrículas-turma do aluno",
        parameters=[
            OpenApiParameter("codigo_aluno", int, OpenApiParameter.PATH),
            OpenApiParameter(
                "data_aula_ticks",
                int,
                OpenApiParameter.QUERY,
                required=False,
            ),
            OpenApiParameter(
                "ano_letivo",
                int,
                OpenApiParameter.QUERY,
                required=False,
            ),
        ],
        responses={200: AlunoAtivoDataAulaSerializer(many=True)},
    )
    def get(self, request: Request, codigo_aluno: str) -> Response:
        """Lista as matrículas-turma do aluno.

        Args:
            request: Requisição com os filtros opcionais ``data_aula_ticks``
                e ``ano_letivo``.
            codigo_aluno: Código do aluno consultado.

        Returns:
            Uma linha por matrícula do aluno conforme os filtros informados.
        """
        try:
            codigo = to_int(codigo_aluno, "codigo_aluno")
            data_aula_raw = request.query_params.get("data_aula_ticks")
            data_aula = (
                ticks_to_datetime(to_int(data_aula_raw, "data_aula_ticks"))
                if data_aula_raw is not None
                else None
            )
            ano_letivo_raw = request.query_params.get("ano_letivo")
            ano_letivo = (
                to_int(ano_letivo_raw, "ano_letivo")
                if ano_letivo_raw
                else None
            )
        except ValueError as exc:
            return _erro_400(str(exc))

        dados = services.obter_matriculas_turmas_aluno(
            codigo_aluno=codigo,
            data_aula=data_aula,
            ano_letivo=ano_letivo if ano_letivo and ano_letivo > 0 else None,
        )
        return Response(AlunoAtivoDataAulaSerializer(dados, many=True).data)


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
        """Lista as necessidades especiais do aluno.

        Args:
            codigo_aluno: Código EOL do aluno.

        Returns:
            Necessidades especiais do aluno.
        """
        try:
            codigo = to_int(codigo_aluno, "codigo_aluno")
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
        """Lista os alunos pelos códigos e ano letivo informados.

        Args:
            request: Requisição com a lista de códigos de aluno.
            ano_letivo: Ano letivo consultado.

        Returns:
            Alunos correspondentes aos códigos no ano letivo.
        """
        try:
            ano = to_int(ano_letivo, "ano_letivo")
            codigos = query_int_list(request, "codigos_aluno")
        except ValueError as exc:
            return _erro_400(str(exc))
        if not codigos:
            return _erro_negocio_legado(ERRO_LEGADO_CODIGOS_ALUNOS)

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
        """Lista os alunos pelos códigos informados.

        Args:
            request: Requisição com a lista de códigos de aluno.

        Returns:
            Alunos correspondentes aos códigos.
        """
        try:
            codigos = query_int_list(request, "codigos_aluno")
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
        """Retorna as informações completas do aluno.

        Args:
            codigo_aluno: Código EOL do aluno.

        Returns:
            Informações do aluno, ou ausência de conteúdo quando não
            encontrado.
        """
        try:
            codigo = to_int(codigo_aluno, "codigo_aluno")
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
        """Lista as informações dos alunos de uma turma.

        Args:
            codigo_turma: Código da turma consultada.

        Returns:
            Informações dos alunos da turma.
        """
        try:
            codigo = to_int(codigo_turma, "codigo_turma")
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
        """Retorna a quantidade de matriculados por componente e ano.

        Args:
            request: Requisição com os componentes curriculares e os filtros
                de DRE e UE.
            ano_letivo: Ano letivo consultado.

        Returns:
            Quantidade de matriculados por componente curricular.
        """
        try:
            ano = to_int(ano_letivo, "ano_letivo")
            componentes = query_int_list(request, "componentes_curriculares")
        except ValueError as exc:
            return _erro_400(str(exc))
        if not componentes:
            return _erro_400("componentes_curriculares é obrigatório.")

        dados = services.obter_quantidade_matriculados_por_ano_e_cc(
            ano_letivo=ano,
            componentes_curriculares=componentes,
            dre_id=request.query_params.get("dre_id"),
            ue_id=request.query_params.get("ue_id"),
        )
        return Response(
            QuantidadeMatriculadosCCSerializer(dados, many=True).data
        )


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
        """Retorna a quantidade de matriculados conforme os filtros.

        Args:
            request: Requisição com os filtros de DRE, UE, modalidade, ano e
                turma.
            ano_letivo: Ano letivo consultado.

        Returns:
            Quantidade de matriculados conforme os filtros.
        """
        try:
            ano = to_int(ano_letivo, "ano_letivo")
            modalidade = query_int_list(request, "modalidade")
            ano_lst = query_int_list(request, "ano")
        except ValueError as exc:
            return _erro_400(str(exc))

        turma = request.query_params.getlist("turma")
        dados = services.obter_quantidade_matriculados(
            ano_letivo=ano,
            dre_codigo=request.query_params.get("dre_codigo", ""),
            ue_codigo=request.query_params.get("ue_codigo", ""),
            modalidade=modalidade,
            ano=ano_lst,
            turma=turma,
        )
        return Response(
            QuantidadeMatriculadosSerializer(dados, many=True).data
        )


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
        """Lista os dados de acompanhamento escolar conforme os filtros.

        Args:
            request: Requisição com os filtros de aluno, DRE, UE e responsável.

        Returns:
            Dados de acompanhamento escolar conforme os filtros.
        """
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
                to_int(codigo_aluno_raw, "codigo_aluno")
                if codigo_aluno_raw
                else None
            )
        except ValueError as exc:
            return _erro_400(str(exc))

        outros_filtros = any(
            (codigo_aluno is not None, codigo_ue, cpf_responsavel)
        )
        if codigo_dre and not outros_filtros:
            return Response([])

        dados = services.obter_dados_acompanhamento_escolar(
            codigo_aluno=codigo_aluno,
            codigo_dre=codigo_dre,
            codigo_ue=codigo_ue,
            cpf_responsavel=cpf_responsavel,
        )
        return Response(
            DadosAcompanhamentoEscolarSerializer(dados, many=True).data
        )


class QuantidadeMatriculadosCCContratoView(APIView):
    """Lista matriculados por componente curricular (contrato legado)."""

    @extend_schema(
        tags=_TAG_ALUNO,
        summary="Matriculados por componente curricular (contrato legado)",
        parameters=[
            OpenApiParameter("ano_letivo", int, OpenApiParameter.PATH),
            OpenApiParameter(
                "componentes_curriculares",
                int,
                OpenApiParameter.QUERY,
                many=True,
                required=True,
            ),
            OpenApiParameter("dre_id", str, OpenApiParameter.QUERY),
            OpenApiParameter("ue_id", str, OpenApiParameter.QUERY),
        ],
        responses={200: QuantidadeMatriculadosCCContratoSerializer(many=True)},
    )
    def get(self, request: Request, ano_letivo: str) -> Response:
        """Lista matriculados por componente conforme filtros do legado.

        Args:
            request: Requisição com componentes curriculares, DRE e UE.
            ano_letivo: Ano letivo consultado.

        Returns:
            Quantidades agregadas no contrato do legado.
        """
        try:
            ano_int = to_int(ano_letivo, "ano_letivo")
            componentes = query_int_list(request, "componentes_curriculares")
        except ValueError as exc:
            return _erro_400(str(exc))
        if not componentes:
            return _erro_negocio_legado(ERRO_LEGADO_COMPONENTES_CURRICULARES)

        dados = services.obter_quantidade_matriculados_cc_contrato(
            ano_letivo=ano_int,
            componentes_curriculares=componentes,
            dre_id=request.query_params.get("dre_id"),
            ue_id=request.query_params.get("ue_id"),
        )
        return Response(
            QuantidadeMatriculadosCCContratoSerializer(dados, many=True).data
        )


class QuantidadeMatriculadosContratoView(APIView):
    """Lista a quantidade de matriculados no contrato do legado."""

    @extend_schema(
        tags=_TAG_ALUNO,
        summary="Quantidade de matriculados (contrato legado)",
        parameters=[
            OpenApiParameter("ano_letivo", int, OpenApiParameter.PATH),
            OpenApiParameter("dre_codigo", str, OpenApiParameter.QUERY),
            OpenApiParameter("ue_codigo", str, OpenApiParameter.QUERY),
            OpenApiParameter(
                "modalidade", int, OpenApiParameter.QUERY, many=True
            ),
            OpenApiParameter("ano", int, OpenApiParameter.QUERY, many=True),
            OpenApiParameter("turma", int, OpenApiParameter.QUERY, many=True),
        ],
        responses={200: QuantidadeMatriculadosContratoSerializer(many=True)},
    )
    def get(self, request: Request, ano_letivo: str) -> Response:
        """Lista quantidades de matriculados conforme filtros do legado.

        Args:
            request: Requisição com os filtros de DRE, UE, modalidade, ano
                e turma.
            ano_letivo: Ano letivo consultado.

        Returns:
            Quantidades agregadas no contrato do legado.
        """
        try:
            ano_int = to_int(ano_letivo, "ano_letivo")
            modalidades = query_int_list(request, "modalidade")
            anos = query_int_list(request, "ano")
            turmas = query_int_list(request, "turma")
        except ValueError as exc:
            return _erro_400(str(exc))
        if ano_int == 0:
            return _erro_negocio_legado(ERRO_LEGADO_ANO_LETIVO_OBRIGATORIO)

        dados = services.obter_quantidade_matriculados_contrato(
            ano_letivo=ano_int,
            dre_codigo=request.query_params.get("dre_codigo"),
            ue_codigo=request.query_params.get("ue_codigo"),
            modalidade=modalidades,
            ano=anos,
            turma=turmas,
        )
        return Response(
            QuantidadeMatriculadosContratoSerializer(dados, many=True).data
        )


class DadosAcompanhamentoEscolarContratoView(APIView):
    """Lista dados de acompanhamento escolar no contrato do legado."""

    @extend_schema(
        tags=_TAG_ALUNO,
        summary="Acompanhamento escolar (contrato legado)",
        parameters=[
            OpenApiParameter("codigo_aluno", int, OpenApiParameter.QUERY),
            OpenApiParameter("codigo_dre", str, OpenApiParameter.QUERY),
            OpenApiParameter("codigo_ue", str, OpenApiParameter.QUERY),
            OpenApiParameter("cpf_responsavel", str, OpenApiParameter.QUERY),
        ],
        responses={
            200: DadosAcompanhamentoEscolarContratoSerializer(many=True)
        },
    )
    def get(self, request: Request) -> Response:
        """Lista os dados de acompanhamento conforme os filtros do legado.

        Args:
            request: Requisição com os filtros de aluno, DRE, UE e
                responsável.

        Returns:
            Dados de acompanhamento escolar no contrato do legado.
        """
        codigo_aluno_raw = request.query_params.get("codigo_aluno")
        codigo_dre = request.query_params.get("codigo_dre")
        codigo_ue = request.query_params.get("codigo_ue")
        cpf_responsavel = request.query_params.get("cpf_responsavel")
        if not any((codigo_aluno_raw, codigo_dre, codigo_ue, cpf_responsavel)):
            return _erro_negocio_legado(ERRO_LEGADO_ACOMPANHAMENTO_SEM_FILTRO)
        try:
            codigo_aluno = (
                to_int(codigo_aluno_raw, "codigo_aluno")
                if codigo_aluno_raw
                else None
            )
        except ValueError as exc:
            return _erro_400(str(exc))

        dados = services.obter_dados_acompanhamento_escolar_contrato(
            codigo_aluno=codigo_aluno,
            codigo_dre=codigo_dre,
            codigo_ue=codigo_ue,
            cpf_responsavel=cpf_responsavel,
        )
        return Response(
            DadosAcompanhamentoEscolarContratoSerializer(dados, many=True).data
        )


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
        """Lista os responsáveis por DRE, UE e turma.

        Args:
            request: Requisição com os filtros de DRE, UE e ano letivo.

        Returns:
            Responsáveis conforme os filtros.
        """
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

        dados = services.obter_responsaveis_dre_ue_turma(
            codigo_dre=codigo_dre,
            codigo_ue=codigo_ue,
            ano_letivo=ano,
        )
        return Response(ResponsavelTurmaSerializer(dados, many=True).data)


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
        """Lista os dados completos do responsável.

        Args:
            cpf_responsavel: CPF do responsável consultado.

        Returns:
            Dados completos do responsável.
        """
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
        """Retorna os dados resumidos do responsável.

        Args:
            cpf_responsavel: CPF do responsável consultado.

        Returns:
            Dados resumidos do responsável, ou ausência de conteúdo quando não
            encontrado.
        """
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
        """Atualiza os dados de contato do responsável (busca ativa).

        Args:
            request: Requisição com os dados de contato no corpo.
            codigo_aluno: Código EOL do aluno.
            cpf_responsavel: CPF do responsável atualizado.

        Returns:
            Dados resumidos do responsável após a atualização.

        Raises:
            ValidationError: Quando os dados informados são inválidos.
        """
        try:
            codigo = to_int(codigo_aluno, "codigo_aluno")
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
        """Cadastra os dados de um responsável do aluno.

        Args:
            request: Requisição com os dados do responsável no corpo.
            codigo_aluno: Código EOL do aluno.
            cpf_responsavel: CPF do responsável cadastrado.

        Returns:
            Dados resumidos do responsável cadastrado.

        Raises:
            ValidationError: Quando os dados informados são inválidos.
        """
        try:
            codigo = to_int(codigo_aluno, "codigo_aluno")
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
        responses={200: DadosResponsavelFiliacaoSerializer(many=True)},
    )
    def get(self, request: Request, codigo_aluno: str) -> Response:
        """Retorna os dados de filiação do responsável do aluno.

        Args:
            codigo_aluno: Código EOL do aluno.

        Returns:
            Dados de filiação encontrados para o aluno.
        """
        try:
            codigo = to_int(codigo_aluno, "codigo_aluno")
        except ValueError as exc:
            return _erro_400(str(exc))

        dados = services.obter_dados_responsavel_filiacao(codigo_aluno=codigo)
        return Response(
            DadosResponsavelFiliacaoSerializer(dados, many=True).data
        )


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
        """Lista as matrículas consolidadas do ano atual.

        Args:
            request: Requisição com o ano letivo e o código da UE.

        Returns:
            Matrículas consolidadas do ano atual.
        """
        ano_raw = request.query_params.get("ano_letivo")
        ue_codigo = request.query_params.get("ue_codigo")
        if not ano_raw or not ue_codigo:
            return _erro_400("ano_letivo e ue_codigo são obrigatórios.")
        try:
            ano = to_int(ano_raw, "ano_letivo")
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
        """Lista as matrículas consolidadas de anos anteriores.

        Args:
            request: Requisição com o ano letivo e o código da UE.

        Returns:
            Matrículas consolidadas de anos anteriores.
        """
        ano_raw = request.query_params.get("ano_letivo")
        ue_codigo = request.query_params.get("ue_codigo")
        if not ano_raw or not ue_codigo:
            return _erro_400("ano_letivo e ue_codigo são obrigatórios.")
        try:
            ano = to_int(ano_raw, "ano_letivo")
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
        """Retorna o total de matrículas por turno na UE.

        Args:
            ue_codigo: Código da unidade educacional.

        Returns:
            Total de matrículas por turno na UE.
        """
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
        """Retorna o total de matrículas por turno na DRE.

        Args:
            dre_codigo: Código da DRE.

        Returns:
            Total de matrículas por turno na DRE.
        """
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
        """Lista a quantidade de alunos por turma na escola.

        Args:
            codigo_escola: Código EOL da escola.

        Returns:
            Quantidade de alunos por turma na escola.
        """
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
        """Lista as matrículas de um aluno na escola.

        Args:
            codigo_escola: Código EOL da escola.
            codigo_aluno: Código EOL do aluno.

        Returns:
            Matrículas do aluno na escola.
        """
        if not codigo_escola:
            return _erro_400("O código da escola e do aluno são obrigatórios")
        try:
            codigo_a = to_int(codigo_aluno, "codigo_aluno")
        except ValueError:
            return _erro_400("O código da escola e do aluno são obrigatórios")
        dados = services.obter_matriculas_aluno_na_escola(
            codigo_escola=codigo_escola, codigo_aluno=codigo_a
        )
        return Response(MatriculaEscolaAlunoSerializer(dados, many=True).data)
