import { Given, When, Then, And } from "cypress-cucumber-preprocessor/steps";

// GIVEN

Given("que possuo acesso à API de alunos", () => {
  expect(Cypress.env("API_URL")).to.exist;
  expect(Cypress.env("API_KEY")).to.exist;
});

// WHEN

When("realizo consulta de informações completas do aluno", () => {
  cy.apiGet(`/api/v1/alunos/${Cypress.env("CODIGO_ALUNO")}/informacoes`).as(
    "response",
  );
});

When("realizo consulta de informações completas do aluno", () => {
  cy.apiGet(`/api/v1/alunos/${Cypress.env("CODIGO_ALUNO")}/informacoes`).as(
    "response",
  );
});

When(
  "realizo consulta de informações completas com código de aluno inexistente",
  () => {
    cy.apiGet(`/api/v1/alunos/0/informacoes`).as("response");
  },
);

When("realizo consulta de necessidades especiais do aluno", () => {
  cy.apiGet(
    `/api/v1/alunos/${Cypress.env("CODIGO_ALUNO_NECESSIDADE")}/necessidades-especiais`,
  ).as("response");
});

When(
  "realizo consulta de necessidades especiais com código de aluno inexistente",
  () => {
    cy.apiGet(`/api/v1/alunos/0/necessidades-especiais`).as("response");
  },
);

When("realizo consulta de turmas do aluno", () => {
  cy.apiGet(`/api/v1/alunos/${Cypress.env("CODIGO_ALUNO")}/turmas/`).as(
    "response",
  );
});

When(
  "realizo consulta de turmas do aluno com código de aluno inexistente",
  () => {
    cy.apiGet(
      `/api/v1/alunos/${Cypress.env("CODIGO_ALUNO_INEXISTENTE_TURMAS")}/turmas`,
    ).as("response");
  },
);

When("realizo consulta de turmas do aluno sem código de aluno", () => {
  cy.apiGet(`/api/v1/alunos/0/turmas`).as("response");
});

When("realizo consulta de turmas do aluno por ano letivo", () => {
  cy.apiGet(
    `/api/v1/alunos/${Cypress.env("CODIGO_ALUNO")}/turmas/anos_letivos/${Cypress.env("ANO_LETIVO")}/historico/true/filtrar-situacao/true/tipo-turma/true`,
  ).as("response");
});

When(
  "realizo consulta de turmas do aluno por ano letivo com código de aluno inexistente",
  () => {
    cy.apiGet(
      `/api/v1/alunos/${Cypress.env("CODIGO_ALUNO_INEXISTENTE_TURMAS_ANO_LETIVO")}/turmas/anos_letivos/${Cypress.env("ANO_LETIVO")}/historico/true/filtrar-situacao/true/tipo-turma/true`,
    ).as("response");
  },
);

When(
  "realizo consulta de turmas do aluno por ano letivo sem código de aluno",
  () => {
    cy.apiGet(
      `/api/v1/alunos/0/turmas/anos_letivos/${Cypress.env("ANO_LETIVO")}/historico/true/filtrar-situacao/true/tipo-turma/true`,
    ).as("response");
  },
);

When("realizo consulta de alunos matriculados", () => {
  cy.apiGet(
    `/api/v1/alunos/ano-letivo/${Cypress.env("ANO_LETIVO")}/matriculados?componentes_curriculares=1`,
  ).as("response");
});

When(
  "realizo consulta de alunos matriculados para um ano letivo sem alunos matriculados",
  () => {
    cy.apiGet(
      `/api/v1/alunos/ano-letivo/${Cypress.env("ANO_LETIVO_SEM_MATRICULADOS")}/matriculados?componentes_curriculares=1`,
    ).as("response");
  },
);

When("realizo consulta de alunos ativos da turma", () => {
  cy.apiGet(`/api/v1/alunos/turmas/${Cypress.env("CODIGO_TURMA")}/ativos`).as(
    "response",
  );
});

When("realizo consulta de acompanhamento escolar por código do aluno", () => {
  cy.apiGet(
    `/api/v1/alunos/dados-acompanhamento-escolar?codigo_aluno=${Cypress.env("CODIGO_ALUNO")}`,
  ).as("response");
});

When("realizo consulta de alunos por UE", () => {
  cy.apiGet(
    `/api/v1/alunos/ues/${Cypress.env("CODIGO_UE")}/anos_letivos/${Cypress.env("ANO_LETIVO")}`,
  ).as("response");
});

When("realizo consulta de autocomplete de alunos ativos", () => {
  cy.apiGet(
    `/api/v1/alunos/ues/${Cypress.env("CODIGO_UE")}/autocomplete/ativos?aluno_nome=${Cypress.env("AUTOCOMPLETE_ALUNO_NOME")}&limite=${Cypress.env("AUTOCOMPLETE_LIMITE")}`,
  ).as("response");
});

When("realizo consulta de filiação do aluno", () => {
  cy.apiGet(
    `/api/v1/alunos/${Cypress.env("CODIGO_ALUNO")}/responsaveis/filiacao`,
  ).as("response");
});

When("realizo consulta de responsável por CPF", () => {
  cy.apiGet(`/api/v1/alunos/responsaveis/${Cypress.env("CPF_RESPONSAVEL")}`).as(
    "response",
  );
});

When("realizo consulta de resumo do responsável", () => {
  cy.apiGet(
    `/api/v1/alunos/responsaveis/${Cypress.env("CPF_RESPONSAVEL")}/resumido`,
  ).as("response");
});

When("realizo consulta de matrículas de aluno na escola", () => {
  cy.apiGet(
    `/api/v1/alunos/escolas/${Cypress.env("CODIGO_ESCOLA")}/aluno/${Cypress.env("CODIGO_ALUNO")}/matriculas`,
  ).as("response");
});

When("realizo consulta de quantidade de alunos por turma", () => {
  cy.apiGet(
    `/api/v1/alunos/escolas/${Cypress.env("CODIGO_UE")}/alunos/quantidade`,
  ).as("response");
});

When("realizo consulta de matrículas", () => {
  cy.apiGet(
    `/api/v1/alunos/matriculas?ano_letivo=${Cypress.env("ANO_LETIVO")}&ue_codigo=${Cypress.env("CODIGO_UE")}`,
  ).as("response");
});

When("realizo consulta de matrículas de anos anteriores", () => {
  cy.apiGet(
    `/api/v1/alunos/matriculas/anos-anteriores?ano_letivo=${Cypress.env("ANO_LETIVO") - 1}&ue_codigo=${Cypress.env("CODIGO_UE")}`,
  ).as("response");
});

When(
  "realizo atualização de dados do responsável do aluno sem alterar dados",
  () => {
    cy.apiPost(
      `/api/v1/alunos/${Cypress.env("CODIGO_ALUNO_SEM_ALTERACAO")}/responsaveis/${Cypress.env("CPF_RESPONSAVEL_SEM_ALTERACAO")}`,
      {
        id: 0,
        cpf: Cypress.env("CPF_RESPONSAVEL_SEM_ALTERACAO"),
        email: Cypress.env("EMAIL_RESPONSAVEL_SEM_ALTERACAO"),
        nome: Cypress.env("NOME_RESPONSAVEL_SEM_ALTERACAO"),
        tipo_responsavel: 0,
        data_nascimento: Cypress.env("DATA_NASCIMENTO_SEM_ALTERACAO"),
        data_atualizacao: Cypress.env("DATA_ATUALIZACAO_SEM_ALTERACAO"),
        nome_mae: Cypress.env("NOME_RESPONSAVEL_SEM_ALTERACAO"),
        ddd_celular: Cypress.env("DDD_SEM_ALTERACAO"),
        numero_celular: Cypress.env("NUMERO_CELULAR_SEM_ALTERACAO"),
        codigo_aluno: Cypress.env("CODIGO_ALUNO_SEM_ALTERACAO"),
      },
    ).as("response");
  },
);

When(
  "realizo atualização de dados de contato do responsável do aluno sem alterar dados",
  () => {
    cy.apiPut(
      `/api/v1/alunos/${Cypress.env("CODIGO_ALUNO_SEM_ALTERACAO")}/responsaveis/${Cypress.env("CPF_RESPONSAVEL_SEM_ALTERACAO")}`,
      {
        codigo_aluno: Cypress.env("CODIGO_ALUNO_SEM_ALTERACAO"),
        cpf: Cypress.env("CPF_RESPONSAVEL_SEM_ALTERACAO"),
        email: Cypress.env("EMAIL_RESPONSAVEL_SEM_ALTERACAO"),
        ddd_celular: Cypress.env("DDD_SEM_ALTERACAO"),
        numero_celular: Cypress.env("NUMERO_CELULAR_SEM_ALTERACAO"),
        ddd_residencial: Cypress.env("DDD_SEM_ALTERACAO"),
        numero_residencial: Cypress.env("NUMERO_RESIDENCIAL_SEM_ALTERACAO"),
        ddd_comercial: Cypress.env("DDD_SEM_ALTERACAO"),
        numero_comercial: Cypress.env("NUMERO_COMERCIAL_SEM_ALTERACAO"),
      },
    ).as("response");
  },
);

When("realizo consulta de nomes dos alunos por código", () => {
  cy.apiPost(`/api/v1/alunos/obter-nomes-alunos/contrato`, {
    codigos_alunos: [Cypress.env("CODIGO_ALUNO")],
    ano_letivo: Number(Cypress.env("ANO_LETIVO")),
  }).as("response");
});

When("realizo consulta de nomes dos alunos sem informar códigos", () => {
  cy.apiPost(`/api/v1/alunos/obter-nomes-alunos/contrato`, {
    codigos_alunos: [],
    ano_letivo: Number(Cypress.env("ANO_LETIVO")),
  }).as("response");
});

// THEN

Then("retorna o status 200", function () {
  cy.get("@response").then((response) => {
    expect(response.status).to.eq(200);
  });
});

Then("retorna o status 400", function () {
  cy.get("@response").then((response) => {
    expect(response.status).to.eq(400);
  });
});

Then("retorna o status 404", function () {
  cy.get("@response").then((response) => {
    expect(response.status).to.eq(404);
  });
});

// AND

And("o retorno das informações do aluno deve ser válido", () => {
  cy.get("@response").then((response) => {
    if (response.status === 200) {
      expect(response.body).to.have.property("codigo_aluno");
      expect(response.body).to.have.property("nome_aluno");
    }
  });
});

And("a mensagem de aluno não encontrado deve ser exibida", function () {
  cy.get("@response").then((response) => {
    if (response.status === 404) {
      expect(response.body).to.have.property("detail");
      expect(response.body.detail).to.eq("Aluno não encontrado.");
    }
  });
});

And("os dados de necessidades especiais do aluno devem ser válidos", () => {
  cy.get("@response").then((response) => {
    if (response.status === 200) {
      expect(response.body[0]).to.have.property("codigo_aluno");
      expect(response.body[0]).to.have.property("tipo_necessidade_especial");
      expect(response.body[0]).to.have.property(
        "descricao_necessidade_especial",
      );
      expect(response.body[0]).to.have.property("tipo_recurso");
      expect(response.body[0]).to.have.property("descricao_recurso");
    }
  });
});

And("o retorno de necessidades especiais do aluno deve ser vazio", () => {
  cy.get("@response").then((response) => {
    if (response.status === 200) {
      expect(response.body).to.be.an("array").that.is.empty;
    }
  });
});

And("o retorno das turmas do aluno deve ser válido", () => {
  cy.get("@response").then((response) => {
    if (response.status === 200) {
      expect(response.body[0]).to.have.property("codigo_aluno");
      expect(response.body[0]).to.have.property("ano_letivo");
      expect(response.body[0]).to.have.property("nome_aluno");
      expect(response.body[0]).to.have.property("codigo_situacao_matricula");
      expect(response.body[0]).to.have.property("codigo_turma");
    }
  });
});

And("o retorno do acompanhamento escolar deve ser válido", () => {
  cy.get("@response").then((response) => {
    if (response.status === 200) {
      expect(response.body).to.have.property("codigo_aluno");
      expect(response.body).to.have.property("nome_aluno");
      expect(response.body).to.have.property("acompanhamento_escolar");
    }
  });
});

And("a mensagem de turma não encontrada para o aluno deve ser exibida", () => {
  cy.get("@response").then((response) => {
    if (response.status === 404) {
      expect(response.body).to.have.property("detail");
      expect(response.body.detail).to.eq(
        "Não foram encontradas turmas para o aluno.",
      );
    }
  });
});

And("a mensagem de código de aluno é obrigatório deve ser exibida", () => {
  cy.get("@response").then((response) => {
    if (response.status === 400) {
      expect(response.body).to.have.property("detail");
      expect(response.body.detail).to.eq("Código do aluno obrigatório.");
    }
  });
});

And("o retorno do alunos deve ser válido", () => {
  cy.get("@response").then((response) => {
    if (response.status === 200) {
      expect(response.body[0]).to.have.property("codigo_aluno");
      expect(response.body[0]).to.have.property("nome_aluno");
      expect(response.body[0]).to.have.property("ano_letivo");
      expect(response.body[0]).to.have.property("codigo_situacao_matricula");
      expect(response.body[0]).to.have.property("situacao_matricula");
      expect(response.body[0]).to.have.property("codigo_turma");
      expect(response.body[0]).to.have.property("numero_aluno_chamada");
    }
  });
});

And("o retorno dos alunos matriculados deve ser válido", () => {
  cy.get("@response").then((response) => {
    if (response.status === 200) {
      expect(response.body[0]).to.have.property("codigo_turma");
      expect(response.body[0]).to.have.property("quantidade");
      expect(response.body[0]).to.have.property("ordem");
    }
  });
});

And("o retorno dos alunos matriculados deve ser vazio", () => {
  cy.get("@response").then((response) => {
    if (response.status === 200) {
      expect(response.body).to.be.an("array").that.is.empty;
    }
  });
});

And("o retorno dos alunos ativos da turma deve ser válido", () => {
  cy.get("@response").then((response) => {
    if (response.status === 200) {
      expect(response.body[0]).to.have.property("codigo_aluno");
      expect(response.body[0]).to.have.property("nome_aluno");
      expect(response.body[0]).to.have.property("data_nascimento");
      expect(response.body[0]).to.have.property("ano_letivo");
      expect(response.body[0]).to.have.property("codigo_situacao_matricula");
      expect(response.body[0]).to.have.property("situacao_matricula");
      expect(response.body[0]).to.have.property("codigo_turma");
      expect(response.body[0]).to.have.property("numero_aluno_chamada");
      expect(response.body[0]).to.have.property("codigo_matricula");
      expect(response.body[0]).to.have.property("codigo_escola");
      expect(response.body[0]).to.have.property("possui_deficiencia");
    }
  });
});

And("o retorno dos dados de acompanhamento escolar deve ser válido", () => {
  cy.get("@response").then((response) => {
    if (response.status === 200) {
      expect(response.body[0]).to.have.property("codigo_eol");
      expect(response.body[0]).to.have.property("nome_responsavel");
      expect(response.body[0]).to.have.property("cpf_responsavel");
      expect(response.body[0]).to.have.property("nome");
      expect(response.body[0]).to.have.property("codigo_escola");
      expect(response.body[0]).to.have.property("tipo_responsavel");
      expect(response.body[0]).to.have.property("codigo_turma");
      expect(response.body[0]).to.have.property("situacao_matricula");
      expect(response.body[0]).to.have.property("data_nascimento");
      expect(response.body[0]).to.have.property("data_situacao_matricula");
      expect(response.body[0]).to.have.property("ano_letivo");
    }
  });
});

And("o retorno dos alunos por UE deve ser válido", () => {
  cy.get("@response").then((response) => {
    if (response.status === 200) {
      expect(response.body[0]).to.have.property("codigo_aluno");
      expect(response.body[0]).to.have.property("nome_aluno");
      expect(response.body[0]).to.have.property("data_nascimento");
      expect(response.body[0]).to.have.property("ano_letivo");
      expect(response.body[0]).to.have.property("codigo_situacao_matricula");
      expect(response.body[0]).to.have.property("situacao_matricula");
      expect(response.body[0]).to.have.property("codigo_turma");
      expect(response.body[0]).to.have.property("numero_aluno_chamada");
      expect(response.body[0]).to.have.property("tipo_turno");
      expect(response.body[0]).to.have.property("desc_etapa_ensino");
    }
  });
});

And("o retorno do autocomplete de alunos ativos deve ser válido", () => {
  cy.get("@response").then((response) => {
    if (response.status === 200) {
      expect(response.body[0]).to.have.property("codigo_aluno");
      expect(response.body[0]).to.have.property("nome_aluno");
      expect(response.body[0]).to.have.property("codigo_turma");
      expect(response.body[0]).to.have.property("numero_aluno_chamada");
      expect(response.body[0]).to.have.property("nome_social_aluno");
    }
  });
});

And("o retorno da filiação do aluno deve ser válido", () => {
  cy.get("@response").then((response) => {
    if (response.status === 200) {
      expect(response.body[0]).to.have.property("nome_responsavel");
      expect(response.body[0]).to.have.property("cpf");
      expect(response.body[0]).to.have.property("email");
      expect(response.body[0]).to.have.property("ddd_celular");
      expect(response.body[0]).to.have.property("numero_celular");
      expect(response.body[0]).to.have.property("ddd_residencial");
      expect(response.body[0]).to.have.property("numero_residencial");
      expect(response.body[0]).to.have.property("ddd_comercial");
      expect(response.body[0]).to.have.property("numero_comercial");
      expect(response.body[0]).to.have.property("tipo_responsavel");
      expect(response.body[0]).to.have.property("endereco");
      expect(response.body[0].endereco).to.have.property("id");
      expect(response.body[0].endereco).to.have.property("bairro");
      expect(response.body[0].endereco).to.have.property("cep");
      expect(response.body[0].endereco).to.have.property("nome_municipio");
      expect(response.body[0].endereco).to.have.property("logradouro");
      expect(response.body[0].endereco).to.have.property("nro");
      expect(response.body[0].endereco).to.have.property("complemento");
      expect(response.body[0].endereco).to.have.property("sigla_uf");
      expect(response.body[0].endereco).to.have.property("tipo_logradouro");
    }
  });
});

And("o retorno do responsável por CPF deve ser válido", () => {
  cy.get("@response").then((response) => {
    if (response.status === 200) {
      expect(response.body[0]).to.have.property("codigo_responsavel");
      expect(response.body[0]).to.have.property("cpf");
      expect(response.body[0]).to.have.property("email");
      expect(response.body[0]).to.have.property("nome");
      expect(response.body[0]).to.have.property("tipo_responsavel");
      expect(response.body[0]).to.have.property("nome_aluno");
      expect(response.body[0]).to.have.property("codigo_aluno");
      expect(response.body[0]).to.have.property("data_nascimento_aluno");
      expect(response.body[0]).to.have.property("ddd_celular");
      expect(response.body[0]).to.have.property("numero_celular");
      expect(response.body[0]).to.have.property("autoriza_sms");
      expect(response.body[0]).to.have.property("logradouro");
      expect(response.body[0]).to.have.property("cep");
      expect(response.body[0]).to.have.property("data_fim_vinculo");
    }
  });
});

And("o retorno do resumo do responsável deve ser válido", () => {
  cy.get("@response").then((response) => {
    if (response.status === 200) {
      expect(response.body).to.have.property("id");
      expect(response.body).to.have.property("cpf");
      expect(response.body).to.have.property("email");
      expect(response.body).to.have.property("nome");
      expect(response.body).to.have.property("tipo_responsavel");
      expect(response.body).to.have.property("data_nascimento");
      expect(response.body).to.have.property("data_atualizacao");
      expect(response.body).to.have.property("ddd_celular");
      expect(response.body).to.have.property("numero_celular");
      expect(response.body).to.have.property("nome_mae");
      expect(response.body).to.have.property("codigo_aluno");
    }
  });
});

And("o retorno das matrículas de aluno na escola deve ser válido", () => {
  cy.get("@response").then((response) => {
    if (response.status === 200) {
      expect(response.body[0]).to.have.property("codigo_aluno");
      expect(response.body[0]).to.have.property("nome_aluno");
      expect(response.body[0]).to.have.property("nome_social_aluno");
      expect(response.body[0]).to.have.property("codigo_situacao_matricula");
      expect(response.body[0]).to.have.property("situacao_matricula");
      expect(response.body[0]).to.have.property("data_situacao");
      expect(response.body[0]).to.have.property("codigo_turma");
      expect(response.body[0]).to.have.property("codigo_matricula");
      expect(response.body[0]).to.have.property("ano_letivo");
    }
  });
});

And("o retorno da quantidade de alunos por turma deve ser válido", () => {
  cy.get("@response").then((response) => {
    if (response.status === 200) {
      expect(response.body[0]).to.have.property("turma_codigo");
      expect(response.body[0]).to.have.property("quantidade");
    }
  });
});

And("o retorno das matrículas de anos anteriores deve ser válido", () => {
  cy.get("@response").then((response) => {
    if (response.status === 200) {
      expect(response.body[0]).to.have.property("turma_codigo");
      expect(response.body[0]).to.have.property("quantidade");
    }
  });
});

And("o retorno das matrículas deve ser válido", () => {
  cy.get("@response").then((response) => {
    if (response.status === 200) {
      expect(response.body[0]).to.have.property("turma_codigo");
      expect(response.body[0]).to.have.property("quantidade");
    }
  });
});

And(
  "o retorno da atualização do responsável deve indicar que nenhum dado foi alterado",
  () => {
    cy.get("@response").then((response) => {
      if (response.status === 200) {
        expect(response.body).to.eq(false);
      }
    });
  },
);

And("o retorno dos nomes dos alunos deve ser válido", () => {
  cy.get("@response").then((response) => {
    if (response.status === 200) {
      expect(response.body[0]).to.have.property("nome_aluno");
      expect(response.body[0]).to.have.property("situacao_matricula");
      expect(response.body[0]).to.have.property("codigo_escola");
      expect(response.body[0]).to.have.property("data_matricula");
      expect(response.body[0]).to.have.property("codigo_aluno");
      expect(response.body[0]).to.have.property("codigo_turma");
      expect(response.body[0]).to.have.property("codigo_situacao_matricula");
    }
  });
});

And(
  "a mensagem de códigos dos alunos obrigatórios deve ser exibida",
  () => {
    cy.get("@response").then((response) => {
      if (response.status === 400) {
        expect(response.body).to.eq(
          "Os códigos dos alunos são obrigatórios.",
        );
      }
    });
  },
);
