# SME-IntegracaoEOL-Alunos-Microsservico

Microsserviço de leitura/escrita do **domínio Alunos** do programa
SME-NOVO-PEDAGOGICO-MS, desenvolvido sob o padrão Strangler Fig
(ADR-02). Substitui os endpoints de aluno/matrícula/responsável hoje
servidos pelo `SME-Pedagogico-API-master`
(`AlunoController`, `MatriculaController`, e os endpoints **E05/E24** do
`EscolaController`), mantendo o **mesmo contrato** (paths, query params
e shape de resposta em camelCase).

Os dados consumidos pelo microsserviço são consolidados pelo
[`SME-IntegracaoEOL-MS-ETL`](../SME-IntegracaoEOL-MS-ETL) em
`alunos_db` (PostgreSQL) — eliminando o acesso direto ao banco legado
**SE1426** (SQL Server / EOL), conforme ADR-01 e ADR-05.

## Stack

| Camada                | Tecnologia                                    |
|-----------------------|-----------------------------------------------|
| Linguagem             | Python 3.12                                   |
| Framework HTTP        | Django 5 + Django REST Framework              |
| Documentação OpenAPI  | drf-spectacular                               |
| Persistência          | PostgreSQL (via dj_db_conn_pool / psycopg2)   |
| Autenticação          | API Key via header `X-API-Key`                |
| Testes                | manage.py test + coverage (≥ 80%)             |
| Qualidade             | black + ruff + mypy                           |

## Estrutura

```
apps/
├── core/               # ApiKey auth e utilitários compartilhados
└── alunos/
    ├── enums.py        # SituacaoMatricula, TipoSexo, TipoResponsavel...
    ├── models.py       # tabelas read-only (managed=False) do alunos_db
    ├── services.py     # 1 função/dataclass DTO por endpoint
    ├── api/
    │   ├── serializers.py  # camelCase shape (contrato legado)
    │   ├── views.py        # APIViews por endpoint
    │   └── urls.py         # paths replicando o contrato
    └── tests/          # test_models / test_services / test_api
config/                  # settings, urls, wsgi/asgi, test_runner
requirements/            # base.txt + local.txt
```

## Hierarquia (idêntica ao MS-ETL):
    `TipoNecessidadeEspecial`
    Aluno
        ├── `ResponsavelAluno`
        ├── `NecessidadeEspecialAluno`  ──► `TipoNecessidadeEspecial`
        └── `Matricula`
                └── `MatriculaTurma`

Qualquer dado fora deste universo (Endereço completo, metadados de
Turma/DRE/Modalidade, Escola, etapa/ciclo de ensino, agregações de
matrícula por turno etc.) NÃO é responsabilidade do domínio Alunos —
o Transition Gateway agrega esses dados a partir dos demais
microsserviços (Pedagógico, Programas).

## Endpoints implementados

> Todos os paths preservam o contrato legado. Documentação interativa disponível em `/api/docs/` (Swagger UI).

### `/api/alunos` (AlunoController)

| ID  | Verbo | Path                                                                                                                                            | Descrição                                              |
|-----|-------|-------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------|
| A01 | GET   | `/api/alunos/{codigo_aluno}/turmas/`                                                                                                            | Turmas do aluno                                        |
| A02 | GET   | `/api/alunos/{codigo_aluno}/turmas/anosLetivos/{ano_letivo}/historico/{historico}/filtrar-situacao/{filtrar_situacao}/tipo-turma/{tipo_turma}`  | Turmas com filtro de situação e tipo                   |
| A03 | GET   | `/api/alunos/{codigo_aluno}/turmas/anosLetivos/{ano_letivo}/matriculaTurma/{filtrar_situacao_matricula}/tipoTurma/{tipo_turma}`                    | Turmas filtradas por situação de matrícula             |
| A04 | GET   | `/api/alunos/ues/{codigo_ue}/anosLetivos/{ano_letivo}`                                                                                         | Alunos de uma UE em determinado ano letivo             |
| A05 | GET   | `/api/alunos/ues/{codigo_ue}/anosLetivos/{ano_letivo}/autocomplete`                                                                           | Autocomplete de alunos por UE e ano letivo             |
| A06 | GET   | `/api/alunos/ues/{ue_codigo}/autocomplete/ativos`                                                                                            | Autocomplete de alunos ativos por UE                   |
| A07 | GET   | `/api/alunos/ativos/anos/{ano_turma}/anos-letivos/{ano_letivo}/inicio/{data_inicio}/fim/{data_fim}`                                             | Total de alunos ativos em um período                   |
| A08 | GET   | `/api/alunos/turmas/{codigo_turma}/ativos/{data_referencia_fim}`                                                                               | Alunos ativos na turma até uma data de corte           |
| A09 | GET   | `/api/alunos/turmas/{codigo_turma}/ativos`                                                                                                   | Alunos ativos na turma                                 |
| A10 | GET   | `/api/alunos/{codigo_aluno}/necessidades-especiais`                                                                                          | Necessidades especiais (deficiências) do aluno         |
| A11 | GET   | `/api/alunos/anoLetivo/{ano_letivo}/alunos`                                                                                                  | Alunos em lote por lista de códigos e ano letivo       |
| A12 | GET   | `/api/alunos/alunos`                                                                                                                        | Alunos em lote por lista de códigos                    |
| A13 | GET   | `/api/alunos/{codigo_aluno}/informacoes`                                                                                                     | Dados cadastrais do aluno                              |
| A14 | GET   | `/api/alunos/{codigo_turma}/turma/informacoes`                                                                                               | Dados de todos os alunos de uma turma                  |
| A15 | GET   | `/api/alunos/ano-letivo/{ano_letivo}/matriculados`                                                                                           | Alunos matriculados por CC e ano letivo                |
| A16 | GET   | `/api/alunos/ano-letivo/{ano_letivo}/matriculados/quantidade`                                                                                | Total de alunos matriculados por CC e ano letivo       |
| A18 | GET   | `/api/alunos/dados-acompanhamento-escolar`                                                                                                  | Dados de acompanhamento escolar                        |
| A19 | GET   | `/api/alunos/responsaveis`                                                                                                                  | Responsáveis filtrados por DRE / UE / turma            |
| A20 | GET   | `/api/alunos/responsaveis/{cpf_responsavel}`                                                                                                 | Dados completos de um responsável                      |
| A21 | GET   | `/api/alunos/responsaveis/{cpf_responsavel}/resumido`                                                                                        | Resumo de um responsável                               |
| A22 | PUT   | `/api/alunos/{codigo_aluno}/responsaveis/{cpf_responsavel}`                                                                                   | Atualiza responsável (busca ativa)                     |
| A23 | POST  | `/api/alunos/{codigo_aluno}/responsaveis/{cpf_responsavel}`                                                                                   | Cadastra novo responsável                              |
| A27 | GET   | `/api/alunos/{codigo_aluno}/responsaveis/filiacao`                                                                                           | Filiação / vínculo dos responsáveis do aluno           |

### `/api/matriculas` (MatriculaController)

| ID  | Verbo | Path                                                  | Descrição                                     |
|-----|-------|-------------------------------------------------------|-----------------------------------------------|
| M01 | GET   | `/api/matriculas`                                     | Matrículas do ano corrente                    |
| M02 | GET   | `/api/matriculas/anos-anteriores`                     | Matrículas de anos anteriores                 |
| M03 | GET   | `/api/matriculas/escolas/{ue_codigo}/quantidades`      | Quantitativo de matrículas por turno na UE    |
| M04 | GET   | `/api/matriculas/escolas/dre/{dre_codigo}/quantidades` | Quantitativo de matrículas por turno na DRE   |

### `/api/escolas` (EscolaController — apenas E05 e E24)

| ID  | Verbo | Path                                                         | Descrição                                     |
|-----|-------|--------------------------------------------------------------|-----------------------------------------------|
| E05 | GET   | `/api/escolas/{codigo_escola}/alunos/quantidade`              | Quantidade de alunos por turma na escola      |
| E24 | GET   | `/api/escolas/{codigo_escola}/aluno/{codigo_aluno}/matriculas` | Matrículas de um aluno em uma escola          |

## Variáveis de ambiente

Veja [`.env.example`](./.env.example).

| Variável                    | Default                                            | Descrição                                |
|-----------------------------|----------------------------------------------------|------------------------------------------|
| `URL_BANCO_ALUNOS`          | `postgresql://postgres:postgres@.../alunos_db`     | Connection string do `alunos_db`         |
| `DJANGO_SECRET_KEY`         | obrigatório em produção                            | Secret do Django                         |
| `DJANGO_DEBUG`              | `1`                                                | Modo debug (`0` em produção)             |
| `DJANGO_ALLOWED_HOSTS`      | `*`                                                | Lista CSV de hosts permitidos            |
| `API_KEY`                   | `dev-key-default`                                  | Chave usada para autenticar consumidores |
| `API_KEY_HEADER`            | `X-API-Key`                                        | Header da API Key                        |
| `DB_POOL_SIZE`              | `5`                                                | Pool size do datasource                  |
| `NOME_APLICACAO`            | `SME-IntegracaoEOL-Alunos-Microsservico`           | Nome da aplicação (logs / health)        |
| `AMBIENTE_APLICACAO`        | `local`                                            | Ambiente (`local`, `staging`, `prod`)    |
| `NIVEL_LOG`                 | `INFO`                                             | Nível de log                             |
| `PORT_WEB` / `PORT_DEBUGPY` | `8002` / `5679`                                    | Portas em dev                            |

## Descrição de dados do model:

### TipoNecessidadeEspecial
Espelha a tabela ``tipo_necessidade_especial`` em ``alunos_db``.
Atua como tabela de domínio: cada registro é uma categoria
referenciada por ``NecessidadeEspecialAluno`` para descrever a NEE
de um aluno.

### Alunos
Espelha a tabela ``aluno`` em ``alunos_db``. Concentra os campos
pessoais (nome, CPF, data de nascimento, raça/cor, filiação) e o
indicador ``possui_deficiencia``, derivado a partir das NEE ativas
pelo MS-ETL.

É a raiz do agregado do domínio Alunos: ``Matricula``,
``ResponsavelAluno`` e ``NecessidadeEspecialAluno`` apontam para
este model via ``codigo_aluno``.

### ResponsavelAluno
Espelha a tabela ``responsavel_aluno`` em ``alunos_db``. Cada
registro representa um responsável vigente ou histórico: o vínculo
é considerado **ativo** enquanto ``data_fim_vinculo`` for ``NULL``.

Mantém os dados de contato (telefone, e-mail, endereço,
consentimento de SMS) usados pelos endpoints A19/A20/A21 e pelo
fluxo de busca ativa (atualização de contato).

### NecessidadeEspecialAluno
Espelha a tabela ``necessidade_especial_aluno`` em ``alunos_db``.
Cada registro materializa o histórico de NEE de um aluno em um
intervalo (``data_inicio`` / ``data_fim``); a NEE é considerada
**vigente** enquanto ``data_fim`` for ``NULL``.

Funciona como tabela associativa entre ``Aluno`` e
``TipoNecessidadeEspecial`` — preserva o tipo da NEE e o período
em que esteve ativa, alimentando o endpoint A10 e o flag
``possui_deficiencia`` em ``Aluno``.

### Matricula
Espelha a tabela ``matricula`` em ``alunos_db``. Representa o
vínculo do aluno com a escola — é a entidade central para os
endpoints de listagem (A04/A05/A11/A12), totais (A07/A15/A16) e
derivações de situação (ativa/válida) controladas por
``codigo_situacao_matricula`` (ver ``apps.alunos.enums``).

Liga-se a ``Aluno`` (N:1) e a ``MatriculaTurma`` (1:N) — esta
última materializa em qual turma o aluno está alocado dentro da
UE.

### MatriculaTurma
Espelha a tabela ``matricula_turma`` em ``alunos_db``. Resolve a
relação N:N entre ``Matricula`` e turma — uma matrícula pode passar
por mais de uma turma ao longo do ano letivo (transferência,
progressão), e cada vínculo carrega o ``numero_chamada`` e a
``data_situacao_aluno`` do aluno naquela turma.

A constraint ``unique_together = (codigo_matricula, codigo_turma)``
garante que cada par matrícula/turma apareça uma única vez, mesmo
quando o histórico inclui reentradas.

Os metadados da turma propriamente dita (nome, modalidade, etapa,
turno, etc.) **não** vivem aqui — pertencem ao domínio Pedagógico
e são compostos pelo Transition Gateway quando necessário.

## Informações adicionais acerca dos DTOs:

### TurmaDoAlunoDTO:
A01/A02/A03/A04/A11/A12 — Turmas/matrículas do aluno (shape reduzido).

### AlunoAutocompleteDTO:
A05/A06 — Alunos para autocomplete (shape reduzido).

### AlunoAtivoTurmaDTO:
A08/A09 — Alunos ativos em uma turma (shape reduzido).

Fora do escopo: tipoTurma, codigoEscola via turma, codigoDre,
transferenciaInterna, remanejado, escolaTransferencia,
turmaTransferencia, turmaRemanejamento, parecerConclusivo,
nomeResponsavel/celular/tipo, dataAtualizacaoContato (este último
fica como data_atualizacao_contato do Aluno).

Fora do escopo: turma (nome), modalidade.

Fora do escopo (Transition Gateway agrega): nomeResponsavel,
tipoResponsavel, celularResponsavel, codigoTipoTurma,
dataAtualizacaoTabela.

#### NecessidadeEspecialDTO:
A10 — Necessidade especial vinculada ao aluno.

Junta o vínculo (``NecessidadeEspecialAluno``) com o catálogo
(``TipoNecessidadeEspecial``) num único registro, expondo código e
descrição da NEE.

### InformacoesAlunoDTO
A13/A27 — Informações do aluno (shape reduzido).

Fora do escopo (Transition Gateway agrega): grupoEtnico,
nacionalidadeResponsavel, ehImigrante, responsavelEhImigrante, cns,
teg e endereço completo (nro/complemento/bairro/cep/município/UF/
tipoLogradouro/logradouro). Aqui retornamos apenas os campos do
Aluno presentes em ``alunos_db``.

### QuantidadeMatriculaCCDTO:
A15 — Quantidade de matrículas por ano letivo (shape reduzido).

O domínio Alunos não possui o vínculo matrícula-componente
curricular (não é coluna de ``matricula``). Retornamos apenas a
quantidade total agregada por turma — campos como modalidade,
ano (turma) e nome de turma ficam por conta do MS Pedagógico via
Transition Gateway.

### QuantidadeMatriculadosDTO:
A16 — Quantidade de matrículas por DRE/UE/turma (shape reduzido).

Sem dados de Turma no domínio Alunos; o endpoint retorna o agregado
que conseguimos calcular: por (codigo_ue, codigo_turma).

### DadosAcompanhamentoEscolarDTO:
A18 — Acompanhamento escolar (shape reduzido).

Sem view materializada no MS-ETL; agregamos o que existe em
Aluno+Matricula+ResponsavelAluno+MatriculaTurma. Fora do escopo:
nomeEscola, codigoDre/siglaDre, codigoTipoEscola/descricaoTipoEscola,
serieResumida, codigoCicloEnsino/codigoEtapaEnsino, modalidade.

### ResponsavelTurmaDTO:
A19 — Responsável agrupado por turma (shape reduzido).

Sem dados de Turma/DRE/Escola no domínio Alunos; retornamos apenas
UE+turma+aluno+CPF+tipoResponsavel. Os campos pedagógicos
(codigoTipoEscola, codigoEtapaEnsino, codigoCicloEnsino,
serieResumida, codigoModalidadeTurma) e ``temAppInstalado`` são
agregados pelo Transition Gateway.

### DadosResponsavelDTO:
A20 — Dados do responsável (shape reduzido).

Fora do escopo: tipoSigilo, RG/dígito/UF, telefone fixo/comercial e
suas turnos, dataNascimento (do responsável e da mãe), nomeMae do
responsável, autorizaSMS — campos que NÃO existem em
``responsavel_aluno`` do MS-ETL.

### InformacoesAlunoTurmaDTO:
A14 — Resumo dos alunos de uma turma (shape reduzido).

Fora do escopo: agrupamento de raça em descrição amigável.

### DadosResponsavelResumidoDTO:
A21/A22/A23 — Versão enxuta dos dados do responsável.

Reaproveitado por três endpoints: A21 (consulta resumida pelo
CPF), A22 (retorno do PUT de busca ativa) e A23 (retorno do POST
de cadastro). Contém o vínculo mínimo (responsável + aluno) e os
contatos (e-mail, celular).

### TotalAlunosAtivosPeriodoDTO:
A07 — Total de alunos distintos ativos no intervalo informado.

Conta cada ``aluno_id`` uma única vez, mesmo que o aluno tenha mais
de uma matrícula ativa no período (ex.: dupla matrícula em UEs
distintas).

### ConsolidacaoMatriculaDTO:
M01/M02/E05 — Total de matrículas válidas agrupadas por turma.

Compartilhado entre M01 (ano atual), M02 (anos anteriores) e E05
(último ano disponível para a escola). A diferença entre eles está
apenas no critério de seleção do ano letivo na função chamadora.

### MatriculaEscolaAlunoDTO:
E24 — Matrícula do aluno em uma escola específica.

Cada registro representa uma matrícula vinculada à escola
informada, com a turma corrente (quando há) e o estado da
matrícula (situação + data). Pode haver múltiplas linhas por
aluno quando ele teve matrículas em anos letivos distintos.

## Como rodar

```bash
# Desenvolvimento — hot reload + debugpy (porta 5679)
docker compose -f docker-compose-dev.yml up --build

# Produção — gunicorn (3 workers)
docker compose up --build
```

Swagger UI disponível em `http://localhost:8002/alunos/api/v1/docs/`.

## Testes

```bash
# Local
python manage.py test

# Via docker (espelha pipeline)
./executar_testes_docker.sh
```

A cobertura mínima exigida é **80%**.

## Observações arquiteturais

- O microsserviço opera **read-only** para os endpoints A01-A21, A27,
  M01-M04, E05 e E24 — todos os models declaram `Meta.managed = False`,
  bloqueando geração de migrations nesta aplicação. DDL é
  responsabilidade exclusiva do `SME-IntegracaoEOL-MS-ETL`.
- Os endpoints **A22 (PUT)** e **A23 (POST)** são **escritas** —
  persistem em tabelas próprias (`responsavel`, `responsavel_aluno`)
  mantidas pelo MS-ETL mas atualizadas por este microsserviço sob
  contrato bem definido (busca ativa / cadastro feito pelas equipes
  pedagógicas).
- A agregação com domínios **Pedagógico** e **Programas** acontece no
  Transition Gateway, que orquestra as chamadas aos microsserviços por
  domínio.
