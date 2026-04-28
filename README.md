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

> Todos os paths preservam o contrato legado.

### `/api/alunos` (AlunoController)

| ID  | Verbo | Path                                                                                                                                       |
|-----|-------|---------------------------------------------------------------------------------------------------------------------------------------------|
| A01 | GET   | `/api/alunos/{codigoAluno}/turmas/`                                                                                                         |
| A02 | GET   | `/api/alunos/{codigoAluno}/turmas/anosLetivos/{anoLetivo}/historico/{historico}/filtrar-situacao/{filtrarSituacao}/tipo-turma/{tipoTurma}`  |
| A03 | GET   | `/api/alunos/{codigoAluno}/turmas/anosLetivos/{anoLetivo}/matriculaTurma/{filtrarSituacaoMatricula}/tipoTurma/{tipoTurma}`                  |
| A04 | GET   | `/api/alunos/ues/{codigoUe}/anosLetivos/{anoLetivo}`                                                                                        |
| A05 | GET   | `/api/alunos/ues/{codigoUe}/anosLetivos/{anoLetivo}/autocomplete`                                                                           |
| A06 | GET   | `/api/alunos/ues/{ueCodigo}/autocomplete/ativos`                                                                                            |
| A07 | GET   | `/api/alunos/ativos/anos/{anoTurma}/anos-letivos/{anoLetivo}/inicio/{dataInicio}/fim/{dataFim}`                                             |
| A08 | GET   | `/api/alunos/turmas/{codigoTurma}/ativos/{dataReferenciaFim}`                                                                               |
| A09 | GET   | `/api/alunos/turmas/{codigoTurma}/ativos`                                                                                                   |
| A10 | GET   | `/api/alunos/{codigoAluno}/necessidades-especiais`                                                                                          |
| A11 | GET   | `/api/alunos/anoLetivo/{anoLetivo}/alunos`                                                                                                  |
| A12 | GET   | `/api/alunos/alunos`                                                                                                                        |
| A13 | GET   | `/api/alunos/{codigoAluno}/informacoes`                                                                                                     |
| A14 | GET   | `/api/alunos/{codigoTurma}/turma/informacoes`                                                                                               |
| A15 | GET   | `/api/alunos/ano-letivo/{anoLetivo}/matriculados`                                                                                           |
| A16 | GET   | `/api/alunos/ano-letivo/{anoLetivo}/matriculados/quantidade`                                                                                |
| A18 | GET   | `/api/alunos/dados-acompanhamento-escolar`                                                                                                  |
| A19 | GET   | `/api/alunos/responsaveis`                                                                                                                  |
| A20 | GET   | `/api/alunos/responsaveis/{cpfResponsavel}`                                                                                                 |
| A21 | GET   | `/api/alunos/responsaveis/{cpfResponsavel}/resumido`                                                                                        |
| A22 | PUT   | `/api/alunos/{codigoAluno}/responsaveis/{cpfResponsavel}`                                                                                   |
| A23 | POST  | `/api/alunos/{codigoAluno}/responsaveis/{cpfResponsavel}`                                                                                   |
| A27 | GET   | `/api/alunos/{codigoAluno}/responsaveis/filiacao`                                                                                           |

### `/api/matriculas` (MatriculaController)

| ID  | Verbo | Path                                                |
|-----|-------|-----------------------------------------------------|
| M01 | GET   | `/api/matriculas`                                   |
| M02 | GET   | `/api/matriculas/anos-anteriores`                   |
| M03 | GET   | `/api/matriculas/escolas/{ueCodigo}/quantidades`    |
| M04 | GET   | `/api/matriculas/escolas/dre/{dreCodigo}/quantidades` |

### `/api/escolas` (EscolaController — apenas E05 e E24)

| ID  | Verbo | Path                                                                  |
|-----|-------|-----------------------------------------------------------------------|
| E05 | GET   | `/api/escolas/{codigoEscola}/alunos/quantidade`                       |
| E24 | GET   | `/api/escolas/{codigoEscola}/aluno/{codigoAluno}/matriculas`          |

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

A cobertura mínima exigida é **80%** (regra institucional, ADR
documentada em `CLAUDE_ProgramasEdu.md`).

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
