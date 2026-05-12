import '@shelex/cypress-allure-plugin'

// Seus comandos
import './commands_api/commands_alunos'

// Evita quebra de teste
Cypress.on('uncaught:exception', () => false)