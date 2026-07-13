"""DTOs do domínio Alunos."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any


@dataclass(frozen=True)
class TurmaDoAlunoDTO:
    """Dados de uma matrícula/turma do aluno."""

    codigo_aluno: int
    ano_letivo: int
    nome_aluno: str
    nome_social_aluno: str | None
    codigo_situacao_matricula: int
    situacao_matricula: str
    data_situacao: date | datetime | None
    data_nascimento: date | None
    documento_cpf: str | None
    data_matricula: date | None
    numero_aluno_chamada: str | None
    codigo_turma: int
    data_atualizacao_contato: date | datetime | None
    nome_responsavel: str | None = None
    tipo_responsavel: int | None = None
    ddd_celular: str | None = None
    numero_celular: str | None = None
    codigo_escola: str | None = None
    codigo_tipo_turma: int | None = None
    data_atualizacao_tabela: date | datetime | None = None


@dataclass(frozen=True)
class AlunoDaUeDTO:
    """Dados de aluno matriculado em uma unidade educacional."""

    codigo_aluno: int
    tipo_turno: int | None
    ano_letivo: int
    nome_aluno: str
    nome_social_aluno: str | None
    codigo_situacao_matricula: int
    situacao_matricula: str
    data_situacao: date | datetime | None
    data_nascimento: date | None
    numero_aluno_chamada: str | None
    codigo_turma: int
    data_atualizacao_contato: date | datetime | str | None
    codigo_tipo_turma: int | None
    turma_nome: str | None
    etapa_ensino: int | None
    ciclo_ensino: int | None
    desc_etapa_ensino: str | None
    desc_ciclo_ensino: str | None
    nome_responsavel: str | None = None
    tipo_responsavel: int | None = None
    ddd_celular: str | None = None
    numero_celular: str | None = None
    data_atualizacao_tabela: date | datetime | str | None = None


@dataclass(frozen=True)
class AlunoAutocompleteDTO:
    """Dados básicos do aluno para autocomplete."""

    codigo_aluno: int
    nome_aluno: str
    nome_social_aluno: str | None
    codigo_turma: int
    numero_aluno_chamada: str | None
    turma: str | None = None
    modalidade: str | None = None


@dataclass(frozen=True)
class AlunoAtivoTurmaDTO:
    """Dados de alunos ativos em uma turma."""

    codigo_aluno: int
    nome_aluno: str
    nome_social_aluno: str | None
    data_nascimento: date | None
    codigo_situacao_matricula: int
    situacao_matricula: str
    data_situacao: datetime | None
    numero_aluno_chamada: str | None
    possui_deficiencia: bool
    codigo_matricula: int
    codigo_turma: int
    codigo_escola: str
    ano_letivo: int


@dataclass(frozen=True)
class AlunoAtivoDataAulaDTO:
    """Aluno ativo em uma turma até uma data de aula."""

    codigo_aluno: int
    nome_aluno: str
    nome_social_aluno: str | None
    data_nascimento: date | None
    codigo_situacao_matricula: int
    situacao_matricula: str
    data_situacao: datetime | None
    numero_aluno_chamada: str | None
    possui_deficiencia: bool
    codigo_matricula: int
    codigo_turma: int
    codigo_escola: str
    ano_letivo: int
    data_matricula: datetime | None
    nome_responsavel: str | None
    tipo_responsavel: int | None
    celular_responsavel: str | None
    data_atualizacao_contato: datetime | None
    sequencia: int | None
    codigo_dre: str


@dataclass(frozen=True)
class NecessidadeEspecialDTO:
    """Necessidade especial vinculada ao aluno."""

    codigo_aluno: int
    tipo_necessidade_especial: int
    descricao_necessidade_especial: str
    tipo_recurso: int | None
    descricao_recurso: str | None


@dataclass(frozen=True)
class InformacoesAlunoDTO:
    """Dados cadastrais do aluno."""

    codigo_aluno: int
    nome_aluno: str
    nome_social_aluno: str | None
    nome_mae: str | None
    sexo: str | None
    nacionalidade: str | None
    raca_cor: str | None
    nis: str | None
    cpf: str | None
    cns: str | None
    endereco: dict[str, Any] | None
    data_nascimento: date | None
    possui_deficiencia: bool


@dataclass(frozen=True)
class InformacoesAlunoTurmaDTO:
    """Resumo dos alunos de uma turma."""

    numero_aluno_chamada: str | None
    codigo_aluno: int
    nome_aluno: str
    nome_social_aluno: str | None
    sexo: str | None
    raca_cor: str | None
    numero_chamada: int | None = None
    raca: str | None = None
    codigo_raca: int | None = None


@dataclass(frozen=True)
class QuantidadeMatriculadosCCDTO:
    """Quantidade de matrículas por ano letivo."""

    codigo_turma: int
    quantidade: int
    ordem: int


@dataclass(frozen=True)
class QuantidadeMatriculadosDTO:
    """Quantidade de matrículas por turma, sem distinção de ano letivo."""

    quantidade: int
    ordem: int
    codigo_turma: int
    ue_codigo: str


@dataclass(frozen=True)
class DadosAcompanhamentoEscolarDTO:
    """Dados de acompanhamento escolar do aluno."""

    codigo_eol: int
    nome_responsavel: str | None
    cpf_responsavel: str | None
    nome: str
    nome_social: str | None
    codigo_escola: str
    tipo_responsavel: int | None
    codigo_turma: int
    situacao_matricula: str
    data_nascimento: date | None
    data_situacao_matricula: date | None
    ano_letivo: int


@dataclass(frozen=True)
class ResponsavelTurmaDTO:
    """Dados do responsável agrupado por turma."""

    codigo_ue: str
    codigo_turma: int
    cpf_responsavel: str
    codigo_aluno: int


@dataclass(frozen=True)
class DadosResponsavelDTO:
    """Dados do responsável do aluno, incluindo vínculo e contatos."""

    codigo_responsavel: int
    cpf: str | None
    email: str | None
    nome: str | None
    tipo_responsavel: int | None
    nome_aluno: str
    nome_social_aluno: str | None
    data_nascimento_aluno: date | None
    codigo_aluno: str
    ddd_celular: str | None
    numero_celular: str | None
    autoriza_sms: str | None
    logradouro: str | None
    cep: int | None
    data_fim_vinculo: date | None


@dataclass(frozen=True)
class DadosResponsavelResumidoDTO:
    """Dados do responsável resumidos."""

    id: int
    cpf: str | None
    email: str | None
    nome: str | None
    tipo_responsavel: int | None
    data_nascimento: date | None
    data_atualizacao: date | datetime | None
    nome_mae: str | None
    ddd_celular: str | None
    numero_celular: str | None
    codigo_aluno: str | None


@dataclass(frozen=True)
class EnderecoFiliacaoDTO:
    """Dados de endereço do responsável."""

    id: int | None
    nro: str | None
    complemento: str | None
    bairro: str | None
    cep: int | None
    nome_municipio: str | None
    sigla_uf: str | None
    tipo_logradouro: str | None
    logradouro: str | None


@dataclass(frozen=True)
class DadosResponsavelFiliacaoDTO:
    """Dados de filiação do responsável do aluno."""

    nome_responsavel: str | None
    cpf: str | None
    email: str | None
    ddd_celular: str | None
    numero_celular: str | None
    ddd_residencial: str | None
    numero_residencial: str | None
    ddd_comercial: str | None
    numero_comercial: str | None
    tipo_responsavel: int | None
    endereco: EnderecoFiliacaoDTO


@dataclass(frozen=True)
class TotalAlunosAtivosPeriodoDTO:
    """Total de alunos distintos ativos no intervalo informado."""

    quantidade: int


@dataclass(frozen=True)
class ConsolidacaoMatriculaDTO:
    """Total de matrículas válidas agrupadas por turma."""

    turma_codigo: str
    quantidade: int


@dataclass(frozen=True)
class MatriculaEscolaAlunoDTO:
    """Matrícula do aluno em uma escola específica."""

    codigo_aluno: int
    nome_aluno: str
    nome_social_aluno: str | None
    codigo_situacao_matricula: int
    situacao_matricula: str
    data_situacao: date | None
    codigo_turma: int
    codigo_matricula: int
    ano_letivo: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
