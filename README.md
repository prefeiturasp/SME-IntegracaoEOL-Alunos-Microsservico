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
config/                  # settings, urls, wsgi/asgi, settings_test, test_runner
requirements/            # base.txt + local.txt
```

## Endpoints implementados

> Todos os paths preservam o contrato legado. Documentação interativa disponível em `/api/docs/` (Swagger UI).

### `/api/alunos` (AlunoController)

| ID  | Verbo | Path                                                                                                                                        | Descrição                                              |
|-----|-------|---------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------|
| A01 | GET   | `/api/alunos/{codigoAluno}/turmas/`                                                                                                         | Turmas do aluno                                        |
| A02 | GET   | `/api/alunos/{codigoAluno}/turmas/anosLetivos/{anoLetivo}/historico/{historico}/filtrar-situacao/{filtrarSituacao}/tipo-turma/{tipoTurma}`  | Turmas com filtro de situação e tipo                   |
| A03 | GET   | `/api/alunos/{codigoAluno}/turmas/anosLetivos/{anoLetivo}/matriculaTurma/{filtrarSituacaoMatricula}/tipoTurma/{tipoTurma}`                  | Turmas filtradas por situação de matrícula             |
| A04 | GET   | `/api/alunos/ues/{codigoUe}/anosLetivos/{anoLetivo}`                                                                                        | Alunos de uma UE em determinado ano letivo             |
| A05 | GET   | `/api/alunos/ues/{codigoUe}/anosLetivos/{anoLetivo}/autocomplete`                                                                           | Autocomplete de alunos por UE e ano letivo             |
| A06 | GET   | `/api/alunos/ues/{ueCodigo}/autocomplete/ativos`                                                                                            | Autocomplete de alunos ativos por UE                   |
| A07 | GET   | `/api/alunos/ativos/anos/{anoTurma}/anos-letivos/{anoLetivo}/inicio/{dataInicio}/fim/{dataFim}`                                             | Total de alunos ativos em um período                   |
| A08 | GET   | `/api/alunos/turmas/{codigoTurma}/ativos/{dataReferenciaFim}`                                                                               | Alunos ativos na turma até uma data de corte           |
| A09 | GET   | `/api/alunos/turmas/{codigoTurma}/ativos`                                                                                                   | Alunos ativos na turma                                 |
| A10 | GET   | `/api/alunos/{codigoAluno}/necessidades-especiais`                                                                                          | Necessidades especiais (deficiências) do aluno         |
| A11 | GET   | `/api/alunos/anoLetivo/{anoLetivo}/alunos`                                                                                                  | Alunos em lote por lista de códigos e ano letivo       |
| A12 | GET   | `/api/alunos/alunos`                                                                                                                        | Alunos em lote por lista de códigos                    |
| A13 | GET   | `/api/alunos/{codigoAluno}/informacoes`                                                                                                     | Dados cadastrais do aluno                              |
| A14 | GET   | `/api/alunos/{codigoTurma}/turma/informacoes`                                                                                               | Dados de todos os alunos de uma turma                  |
| A15 | GET   | `/api/alunos/ano-letivo/{anoLetivo}/matriculados`                                                                                           | Alunos matriculados por CC e ano letivo                |
| A16 | GET   | `/api/alunos/ano-letivo/{anoLetivo}/matriculados/quantidade`                                                                                | Total de alunos matriculados por CC e ano letivo       |
| A18 | GET   | `/api/alunos/dados-acompanhamento-escolar`                                                                                                  | Dados de acompanhamento escolar                        |
| A19 | GET   | `/api/alunos/responsaveis`                                                                                                                  | Responsáveis filtrados por DRE / UE / turma            |
| A20 | GET   | `/api/alunos/responsaveis/{cpfResponsavel}`                                                                                                 | Dados completos de um responsável                      |
| A21 | GET   | `/api/alunos/responsaveis/{cpfResponsavel}/resumido`                                                                                        | Resumo de um responsável                               |
| A22 | PUT   | `/api/alunos/{codigoAluno}/responsaveis/{cpfResponsavel}`                                                                                   | Atualiza responsável (busca ativa)                     |
| A23 | POST  | `/api/alunos/{codigoAluno}/responsaveis/{cpfResponsavel}`                                                                                   | Cadastra novo responsável                              |
| A27 | GET   | `/api/alunos/{codigoAluno}/responsaveis/filiacao`                                                                                           | Filiação / vínculo dos responsáveis do aluno           |

### `/api/matriculas` (MatriculaController)

| ID  | Verbo | Path                                                  | Descrição                                     |
|-----|-------|-------------------------------------------------------|-----------------------------------------------|
| M01 | GET   | `/api/matriculas`                                     | Matrículas do ano corrente                    |
| M02 | GET   | `/api/matriculas/anos-anteriores`                     | Matrículas de anos anteriores                 |
| M03 | GET   | `/api/matriculas/escolas/{ueCodigo}/quantidades`      | Quantitativo de matrículas por turno na UE    |
| M04 | GET   | `/api/matriculas/escolas/dre/{dreCodigo}/quantidades` | Quantitativo de matrículas por turno na DRE   |

### `/api/escolas` (EscolaController — apenas E05 e E24)

| ID  | Verbo | Path                                                         | Descrição                                     |
|-----|-------|--------------------------------------------------------------|-----------------------------------------------|
| E05 | GET   | `/api/escolas/{codigoEscola}/alunos/quantidade`              | Quantidade de alunos por turma na escola      |
| E24 | GET   | `/api/escolas/{codigoEscola}/aluno/{codigoAluno}/matriculas` | Matrículas de um aluno em uma escola          |

## Variáveis de ambiente

Veja [`.env.example`](./.env.example).

| Variável                 | Default                                                                 | Descrição                                |
|--------------------------|-------------------------------------------------------------------------|------------------------------------------|
| `URL_BANCO_ALUNOS`       | `postgresql://postgres:postgres@.../alunos_db`                          | Connection string do `alunos_db`         |
| `DJANGO_SECRET_KEY`      | obrigatório em produção                                                 | Secret do Django                         |
| `DJANGO_DEBUG`           | `1`                                                                     | Modo debug                               |
| `DJANGO_ALLOWED_HOSTS`   | `*`                                                                     | Lista CSV de hosts                       |
| `API_KEY`                | `dev-key-default`                                                       | Chave usada para autenticar consumidores |
| `API_KEY_HEADER`         | `X-API-Key`                                                             | Header da API Key                        |
| `DB_POOL_SIZE`           | `5`                                                                     | Pool size do datasource                  |
| `PORT_WEB` / `PORT_DEBUGPY` | `8002` / `5679`                                                       | Portas em dev                            |

## Como rodar

```bash
# Build + subir a aplicação no docker (modo dev, com debugpy)
docker compose -f docker-compose-dev.yml up --build

# Acessar swagger UI
# http://localhost:8002/api/docs/
```

## Testes

```bash
# Local
python manage.py test --settings=config.settings_test

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
