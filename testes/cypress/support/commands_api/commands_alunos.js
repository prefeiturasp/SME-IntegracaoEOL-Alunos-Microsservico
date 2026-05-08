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