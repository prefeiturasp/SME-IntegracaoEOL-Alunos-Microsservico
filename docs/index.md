# SME-IntegracaoEOL Alunos

O microsserviço `SME-IntegracaoEOL-Alunos-Microsservico` é uma aplicação Django/DRF que expõe os contratos do domínio **Alunos** (aluno, matrícula, responsável e necessidades especiais) da SME-SP.

O serviço opera majoritariamente em modo *read-only* sobre o banco `alunos_db` (a maior parte dos models declara `Meta.managed = False`) e responde aos contratos definidos pela SME, preservando caminhos, parâmetros, códigos de status e cabeçalhos (autenticação por `X-API-Key`). Endpoints específicos de busca ativa (PUT/POST de responsáveis) realizam escrita nas tabelas previstas pelo contrato.

O SME Sidecar SDK padroniza os logs estruturados, a correlação por
`X-Request-ID` e o tracing OpenTelemetry. O runtime é iniciado no app `core`
e o middleware de observabilidade precede as demais camadas Django.

## Escopo e Arquitetura

Este microsserviço é uma unidade autônoma responsável pelo domínio Alunos: recebe requisições HTTP, consulta (e, quando previsto, atualiza) o banco relacional e devolve a resposta no formato esperado pelos consumidores. Não executa rotinas de ingestão, transformação ou orquestração — sua única responsabilidade é servir os contratos de Aluno/Matrícula/Responsável a partir do estado atual do banco.

A documentação é gerada automaticamente pelo Sphinx a partir das docstrings do código e está estruturada da seguinte forma:

```{toctree}
:maxdepth: 2
:caption: Referência de código

api
```
