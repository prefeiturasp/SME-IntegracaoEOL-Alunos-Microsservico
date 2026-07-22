"""Fachada dos services do domínio Alunos."""

# ruff: noqa: F401

from apps.alunos.services import alunos
from apps.alunos.services.acompanhamento import (
    obter_dados_acompanhamento_escolar,
    obter_dados_acompanhamento_escolar_contrato,
)
from apps.alunos.services.alunos import (
    SITUACOES_MATRICULA_TURMA_ATIVAS,
    obter_alunos_ativos_por_periodo_e_turma,
    obter_alunos_ativos_por_turma,
    obter_alunos_turma,
    obter_informacoes_aluno,
    obter_informacoes_alunos_da_turma,
    obter_necessidades_especiais_por_aluno,
    obter_total_alunos_ativos_periodo,
)
from apps.alunos.services.autocomplete import (
    buscar_alunos_ativos_autocomplete,
    buscar_alunos_autocomplete,
)
from apps.alunos.services.matriculas import (
    obter_matriculas_aluno_na_escola,
    obter_matriculas_ano_atual,
    obter_matriculas_anos_anteriores,
    obter_quantidade_alunos_por_turma_da_escola,
    obter_total_matriculas_por_turno_dre,
    obter_total_matriculas_por_turno_ue,
)
from apps.alunos.services.quantidades import (
    obter_quantidade_matriculados,
    obter_quantidade_matriculados_cc_contrato,
    obter_quantidade_matriculados_contrato,
    obter_quantidade_matriculados_por_ano_e_cc,
)
from apps.alunos.services.responsaveis import (
    atualizar_dados_responsavel_busca_ativa,
    cadastrar_dados_responsavel,
    obter_dados_responsavel,
    obter_dados_responsavel_filiacao,
    obter_dados_responsavel_resumido,
    obter_responsaveis_dre_ue_turma,
)
from apps.alunos.services.turmas import (
    buscar_alunos_da_ue,
    buscar_turmas_do_aluno,
    buscar_turmas_do_aluno_com_historico,
    buscar_turmas_do_aluno_por_situacao_matricula,
    obter_alunos_por_codigos,
    obter_alunos_por_codigos_e_ano,
    obter_codigos_turmas_regulares_aluno,
)
