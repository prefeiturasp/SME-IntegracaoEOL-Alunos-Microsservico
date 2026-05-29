# language: pt

Funcionalidade: API - Alunos

  Cenário: Consultar informações completas do aluno
    Dado que possuo acesso à API de alunos
    Quando realizo consulta de informações completas do aluno
    Então retorna o status 200
    E o retorno das informações do aluno deve ser válido

  Cenário: Consultar informações completas - Aluno não encontrado
    Dado que possuo acesso à API de alunos
    Quando realizo consulta de informações completas com código de aluno inexistente
    Então retorna o status 404
    E a mensagem de aluno não encontrado deve ser exibida

  Cenário: Consultar necessidades especiais do aluno
    Dado que possuo acesso à API de alunos
    Quando realizo consulta de necessidades especiais do aluno
    Então retorna o status 200
    E os dados de necessidades especiais do aluno devem ser válidos

  Cenário: Consultar necessidades especiais - Aluno não encontrado
     Dado que possuo acesso à API de alunos
     Quando realizo consulta de necessidades especiais com código de aluno inexistente
     Então retorna o status 200
     E o retorno de necessidades especiais do aluno deve ser vazio

  Cenário: Consultar turmas do aluno
    Dado que possuo acesso à API de alunos
    Quando realizo consulta de turmas do aluno
    Então retorna o status 200
    E o retorno das turmas do aluno deve ser válido

  Cenário: Consultar turmas do aluno - Aluno não encontrado
    Dado que possuo acesso à API de alunos
    Quando realizo consulta de turmas do aluno com código de aluno inexistente
    Então retorna o status 404
    E a mensagem de turma não encontrada para o aluno deve ser exibida

  Cenário: Consultar turmas do aluno - Sem Código de aluno
    Dado que possuo acesso à API de alunos
    Quando realizo consulta de turmas do aluno sem código de aluno
    Então retorna o status 400
    E a mensagem de código de aluno é obrigatório deve ser exibida

  Cenário: Consultar turmas do aluno por ano letivo
    Dado que possuo acesso à API de alunos
    Quando realizo consulta de turmas do aluno por ano letivo
    Então retorna o status 200
    E o retorno do alunos deve ser válido

  Cenário: Consultar turmas do aluno por ano letivo - Aluno não encontrado
    Dado que possuo acesso à API de alunos
    Quando realizo consulta de turmas do aluno por ano letivo com código de aluno inexistente
    Então retorna o status 404
    E a mensagem de turma não encontrada para o aluno deve ser exibida

  Cenário: Consultar turmas do aluno por ano letivo - Sem Código de aluno
    Dado que possuo acesso à API de alunos
    Quando realizo consulta de turmas do aluno por ano letivo sem código de aluno
    Então retorna o status 400
    E a mensagem de código de aluno é obrigatório deve ser exibida  

  Cenário: Consultar alunos matriculados no ano letivo
    Dado que possuo acesso à API de alunos
    Quando realizo consulta de alunos matriculados
    Então retorna o status 200
    E o retorno dos alunos matriculados deve ser válido

  Cenário: Consultar alunos matriculados em ano letivo sem alunos matriculados
     Dado que possuo acesso à API de alunos
     Quando realizo consulta de alunos matriculados para um ano letivo sem alunos matriculados
     Então retorna o status 200
     E o retorno dos alunos matriculados deve ser vazio

  Cenário: Consultar alunos ativos da turma
    Dado que possuo acesso à API de alunos
    Quando realizo consulta de alunos ativos da turma
    Então retorna o status 200
    E o retorno dos alunos ativos da turma deve ser válido

  Cenário: Consultar dados de acompanhamento escolar por Código do aluno
    Dado que possuo acesso à API de alunos
    Quando realizo consulta de acompanhamento escolar por código do aluno
    Então retorna o status 200
    E o retorno dos dados de acompanhamento escolar deve ser válido

  Cenário: Consultar alunos por UE
    Dado que possuo acesso à API de alunos
    Quando realizo consulta de alunos por UE
    Então retorna o status 200
    E o retorno dos alunos por UE deve ser válido

  Cenário: Consultar autocomplete de alunos ativos
    Dado que possuo acesso à API de alunos
    Quando realizo consulta de autocomplete de alunos ativos
    Então retorna o status 200
    E o retorno do autocomplete de alunos ativos deve ser válido

  Cenário: Consultar filiação do aluno
    Dado que possuo acesso à API de alunos
    Quando realizo consulta de filiação do aluno
    Então retorna o status 200
    E o retorno da filiação do aluno deve ser válido

  Cenário: Consultar dados completos do responsável por CPF
    Dado que possuo acesso à API de alunos
    Quando realizo consulta de responsável por CPF
    Então retorna o status 200
    E o retorno do responsável por CPF deve ser válido

  Cenário: Consultar resumo do responsável
    Dado que possuo acesso à API de alunos
    Quando realizo consulta de resumo do responsável
    Então retorna o status 200
    E o retorno do resumo do responsável deve ser válido

  Cenário: Consultar matrículas de aluno na escola
    Dado que possuo acesso à API de alunos
    Quando realizo consulta de matrículas de aluno na escola
    Então retorna o status 200
    E o retorno das matrículas de aluno na escola deve ser válido

  Cenário: Consultar quantidade de alunos por turma
    Dado que possuo acesso à API de alunos
    Quando realizo consulta de quantidade de alunos por turma
    Então retorna o status 200
    E o retorno da quantidade de alunos por turma deve ser válido

  Cenário: Consultar matrículas consolidada do ano atual
    Dado que possuo acesso à API de alunos
    Quando realizo consulta de matrículas
    Então retorna o status 200
    E o retorno das matrículas deve ser válido

  Cenário: Consultar matrículas consolidadas de anos anteriores
    Dado que possuo acesso à API de alunos
    Quando realizo consulta de matrículas de anos anteriores
    Então retorna o status 200
    E o retorno das matrículas de anos anteriores deve ser válido
    