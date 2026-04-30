"""Test runner customizado para o microsserviço Alunos.

Os models do app ``alunos`` declaram ``Meta.managed = False`` em
produção (DDL é responsabilidade do ``SME-IntegracaoEOL-MS-ETL``). Em
testes isso impediria o Django de criar as tabelas no banco SQLite em
memória. Este runner cria as tabelas de models unmanaged manualmente
via ``schema_editor`` após o ``setup_databases`` padrão.
"""

from __future__ import annotations

from django.apps import apps
from django.db import connections
from django.test.runner import DiscoverRunner


class AlunosTestRunner(DiscoverRunner):
    """Cria tabelas de models unmanaged antes de executar os testes."""

    def setup_databases(self, **kwargs):  # type: ignore[no-untyped-def]
        result = super().setup_databases(**kwargs)
        with connections["default"].schema_editor() as editor:
            created_tables: set[str] = set()
            for model in apps.get_models():
                if not model._meta.managed:
                    table_name = model._meta.db_table
                    if table_name not in created_tables:
                        editor.create_model(model)
                        created_tables.add(table_name)
        return result
