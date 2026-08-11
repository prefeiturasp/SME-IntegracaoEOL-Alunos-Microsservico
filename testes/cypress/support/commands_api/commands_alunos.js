Cypress.Commands.add('apiGet', (url) => {
  return cy.request({
    method: 'GET',
    url: `${Cypress.env('API_URL')}${url}`,
    headers: {
      accept: 'application/json',
      [Cypress.env('API_KEY_HEADER')]: Cypress.env('API_KEY'),
    },
    failOnStatusCode: false,
  })
})

Cypress.Commands.add('apiPost', (url, body) => {
  return cy.request({
    method: 'POST',
    url: `${Cypress.env('API_URL')}${url}`,
    headers: {
      accept: 'application/json',
      [Cypress.env('API_KEY_HEADER')]: Cypress.env('API_KEY'),
    },
    body,
    failOnStatusCode: false,
  })
})

Cypress.Commands.add('apiPut', (url, body) => {
  return cy.request({
    method: 'PUT',
    url: `${Cypress.env('API_URL')}${url}`,
    headers: {
      accept: 'application/json',
      [Cypress.env('API_KEY_HEADER')]: Cypress.env('API_KEY'),
    },
    body,
    failOnStatusCode: false,
  })
})