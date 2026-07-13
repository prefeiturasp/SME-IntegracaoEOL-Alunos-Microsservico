"""Queries SQL do domínio Alunos (réplicas do contrato legado)."""


SQL_A15_QUANTIDADE_POR_ANO_E_CC = """
SELECT json_agg(row_to_json(t))::text AS j FROM (
    SELECT
        mt.codigo_turma AS "codigo_turma",
        COUNT(*) AS quantidade,
        ROW_NUMBER() OVER (ORDER BY mt.codigo_turma) AS ordem
    FROM matricula m
    JOIN matricula_turma mt ON mt.codigo_matricula = m.codigo_matricula
    WHERE m.ano_letivo = %(ano)s
      AND m.codigo_situacao_matricula = ANY(%(situacoes)s)
      AND (%(ue)s::text IS NULL OR m.codigo_ue = %(ue)s)
    GROUP BY mt.codigo_turma
    ORDER BY mt.codigo_turma
) t
"""

SQL_A16_QUANTIDADE = """
SELECT json_agg(row_to_json(t))::text AS j FROM (
    SELECT
        COUNT(*) AS quantidade,
        ROW_NUMBER() OVER (ORDER BY m.codigo_ue, mt.codigo_turma) AS ordem,
        mt.codigo_turma AS "codigo_turma",
        m.codigo_ue AS "ue_codigo"
    FROM matricula m
    JOIN matricula_turma mt ON mt.codigo_matricula = m.codigo_matricula
    WHERE m.ano_letivo = %(ano)s
      AND m.codigo_situacao_matricula = ANY(%(situacoes)s)
      AND (%(ue)s::text IS NULL OR m.codigo_ue = %(ue)s)
    GROUP BY m.codigo_ue, mt.codigo_turma
    ORDER BY m.codigo_ue, mt.codigo_turma
) t
"""

SQL_A18_ACOMPANHAMENTO = """
SELECT json_agg(row_to_json(t))::text AS j FROM (
    SELECT
        m.codigo_aluno AS "codigo_eol",
        r.nome AS "nome_responsavel",
        r.cpf AS "cpf_responsavel",
        a.nome AS "nome",
        a.nome_social AS "nome_social",
        m.codigo_ue AS "codigo_escola",
        r.tipo_responsavel AS "tipo_responsavel",
        COALESCE(mt.codigo_turma, 0) AS "codigo_turma",
        m.situacao_matricula AS "situacao_matricula",
        a.data_nascimento AS "data_nascimento",
        m.data_situacao_matricula AS "data_situacao_matricula",
        m.ano_letivo AS "ano_letivo"
    FROM matricula m
    JOIN aluno a ON a.codigo_aluno = m.codigo_aluno
    LEFT JOIN LATERAL (
        SELECT codigo_turma
        FROM matricula_turma
        WHERE codigo_matricula = m.codigo_matricula
        LIMIT 1
    ) mt ON TRUE
    LEFT JOIN LATERAL (
        SELECT nome, cpf, tipo_responsavel
        FROM responsavel_aluno
        WHERE codigo_aluno = a.codigo_aluno
          AND data_fim_vinculo IS NULL
        ORDER BY tipo_responsavel DESC NULLS FIRST
        LIMIT 1
    ) r ON TRUE
    WHERE m.codigo_situacao_matricula = ANY(%(situacoes)s)
      AND (%(codigo_aluno)s::bigint IS NULL
           OR m.codigo_aluno = %(codigo_aluno)s::bigint)
      AND (%(codigo_ue)s::text IS NULL OR m.codigo_ue = %(codigo_ue)s)
      AND (%(ano_letivo)s::int IS NULL
           OR m.ano_letivo = %(ano_letivo)s::int)
      AND (%(turma_codigo)s::bigint IS NULL
           OR mt.codigo_turma = %(turma_codigo)s::bigint)
      AND (%(cpf)s::text IS NULL OR EXISTS (
          SELECT 1 FROM responsavel_aluno r2
          WHERE r2.codigo_aluno = m.codigo_aluno
            AND r2.cpf = %(cpf)s
            AND r2.data_fim_vinculo IS NULL
      ))
) t
"""

SQL_A19_RESPONSAVEIS = """
SELECT json_agg(row_to_json(t))::text AS j FROM (
    SELECT
        m.codigo_ue AS "codigo_ue",
        COALESCE(mt.codigo_turma, 0) AS "codigo_turma",
        r.cpf AS "cpf_responsavel",
        m.codigo_aluno AS "codigo_aluno"
    FROM matricula m
    JOIN responsavel_aluno r
        ON r.codigo_aluno = m.codigo_aluno
       AND r.data_fim_vinculo IS NULL
       AND r.cpf IS NOT NULL
       AND r.cpf <> ''
    LEFT JOIN LATERAL (
        SELECT codigo_turma
        FROM matricula_turma
        WHERE codigo_matricula = m.codigo_matricula
        LIMIT 1
    ) mt ON TRUE
    WHERE m.codigo_situacao_matricula = ANY(%(situacoes)s)
      AND (%(codigo_ue)s::text IS NULL OR m.codigo_ue = %(codigo_ue)s)
      AND (%(ano_letivo)s::int IS NULL
           OR m.ano_letivo = %(ano_letivo)s::int)
) t
"""
