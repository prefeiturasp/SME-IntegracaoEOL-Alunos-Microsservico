import { Given, When, Then } from 'cypress-cucumber-preprocessor/steps'

Given('que possuo acesso à API de alunos', () => {
  expect(Cypress.env('API_URL')).to.exist
  expect(Cypress.env('API_KEY')).to.exist
})

When('realizo consulta de informações completas do aluno', () => {
  cy.apiGet(`/api/v1/alunos/${Cypress.env('CODIGO_ALUNO')}/informacoes`)
    .as('response')
})

When('realizo consulta de necessidades especiais do aluno', () => {
  cy.apiGet(`/api/v1/alunos/${Cypress.env('CODIGO_ALUNO_NECESSIDADE')}/necessidades-especiais`)
    .as('response')
})

When('realizo consulta de turmas do aluno', () => {
  cy.apiGet(`/api/v1/alunos/${Cypress.env('CODIGO_ALUNO')}/turmas/`)
    .as('response')
})

When('realizo consulta de turmas do aluno por ano letivo', () => {
  cy.apiGet(`/api/v1/alunos/${Cypress.env('CODIGO_ALUNO')}/turmas/anosLetivos/${Cypress.env('ANO_LETIVO')}`)
    .as('response')
})

When('realizo consulta de alunos matriculados', () => {
  cy.apiGet(`/api/v1/alunos/ano-letivo/${Cypress.env('ANO_LETIVO')}/matriculados`)
    .as('response')
})

When('realizo consulta de alunos ativos da turma', () => {
  cy.apiGet(`/api/v1/alunos/turmas/${Cypress.env('CODIGO_TURMA')}/ativos`)
    .as('response')
})

When('realizo consulta de acompanhamento escolar', () => {
  cy.apiGet(`/api/v1/alunos/dados-acompanhamento-escolar`)
    .as('response')
})

When('realizo consulta de alunos por UE', () => {
  cy.apiGet(`/api/v1/alunos/ues/${Cypress.env('CODIGO_UE')}/anosLetivos/${Cypress.env('ANO_LETIVO')}`)
    .as('response')
})

When('realizo consulta de autocomplete de alunos ativos', () => {
  cy.apiGet(`/api/v1/alunos/ues/${Cypress.env('CODIGO_UE')}/autocomplete/ativos`)
    .as('response')
})

When('realizo consulta de filiação do aluno', () => {
  cy.apiGet(`/api/v1/alunos/${Cypress.env('CODIGO_ALUNO')}/responsaveis/filiacao`)
    .as('response')
})

When('realizo consulta de responsável por CPF', () => {
  cy.apiGet(`/api/v1/alunos/responsaveis/${Cypress.env('CPF_RESPONSAVEL')}`)
    .as('response')
})

When('realizo consulta de resumo do responsável', () => {
  cy.apiGet(`/api/v1/alunos/responsaveis/${Cypress.env('CPF_RESPONSAVEL')}/resumo`)
    .as('response')
})

When('realizo consulta de aluno por escola', () => {
  cy.apiGet(`/api/v1/alunos/escolas/${Cypress.env('CODIGO_UE')}/aluno/${Cypress.env('CODIGO_ALUNO')}`)
    .as('response')
})

When('realizo consulta de quantidade de alunos por escola', () => {
  cy.apiGet(`/api/v1/alunos/escolas/${Cypress.env('CODIGO_UE')}/alunos/quantidade`)
    .as('response')
})

When('realizo consulta de matrículas', () => {
  cy.apiGet(`/api/v1/alunos/matriculas`)
    .as('response')
})

When('realizo consulta de matrículas de anos anteriores', () => {
  cy.apiGet(`/api/v1/alunos/matriculas/anos-anteriores`)
    .as('response')
})

Then('o status da resposta de alunos deve ser válido', () => {
  cy.get('@response').then((response) => {

    expect(
      [200, 201, 202, 204, 400, 404]
    ).to.include(response.status)

  })
})

Then('o retorno das informações do aluno deve ser válido', () => {
  cy.get('@response').then((response) => {

    if (response.status === 200) {
      expect(response.body).to.have.property('codigoAluno')
      expect(response.body).to.have.property('nomeAluno')
    }

  })
})