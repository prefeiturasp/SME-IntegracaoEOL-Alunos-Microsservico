"""Test runner customizado para o microsserviço Alunos.

Os models do app ``alunos`` declaram ``Meta.managed = False`` em
produção (DDL é responsabilidade do ``SME-IntegracaoEOL-MS-ETL``). Em
testes isso impediria o Django de criar as tabelas no banco de testes.
Este runner marca temporariamente todos os models do app como
gerenciáveis antes de criar o banco, permitindo que o test runner
padrão crie o schema via ``schema_editor`` e os testes manipulem dados
normalmente.
"""

from __future__ import annotations

from django.test.runner import DiscoverRunner


class AlunosTestRunner(DiscoverRunner):
    """Runner que torna models managed=False criáveis em testes."""

    def setup_databases(self, **kwargs):  # type: ignore[no-untyped-def]
        from apps.alunos import models as alunos_models

        for model in (
            alunos_models.TipoNecessidadeEspecial,
            alunos_models.Aluno,
            alunos_models.ResponsavelAluno,
            alunos_models.NecessidadeEspecialAluno,
            alunos_models.Matricula,
            alunos_models.MatriculaTurma,
        ):
            model._meta.managed = True

        return super().setup_databases(**kwargs)
