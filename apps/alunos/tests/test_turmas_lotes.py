"""Valida contrato, ordenação e consultas das turmas em lote."""

import json
from collections.abc import Sequence
from datetime import UTC, date, datetime
from functools import partial
from hashlib import sha256
from pathlib import Path
from typing import Any
from unittest.mock import patch

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from apps.alunos.api.serializers import TurmaDoAlunoSerializer
from apps.alunos.models import (
    Aluno,
    Matricula,
    MatriculaTurma,
    ResponsavelAluno,
)
from apps.alunos.services import turmas as turmas_service

HASHES_TURMAS: dict[str, str] = json.loads(
    (
        Path(__file__).parent / "fixtures" / "turmas_lotes_hashes.json"
    ).read_text()
)
CENARIOS_ALUNOS = {
    "um": [101],
    "seis": [106, 101, 102, 103, 104, 105],
    "repetido": [101, 102, 101],
    "inexistente": [9999],
    "misto": [9999, 101],
    "sem_turma": [103],
    "sem_responsavel": [102],
    "vazio": [],
}


class TurmasLotesPerformanceTest(TestCase):
    """Preserva o contrato das turmas e limita as consultas dos lotes."""

    @classmethod
    def setUpTestData(cls) -> None:
        """Cria vínculos sintéticos com origens e contatos distintos."""
        for codigo in range(101, 107):
            Aluno.objects.create(
                codigo_aluno=codigo,
                nome=f"ALUNO SINTETICO {codigo}",
                nome_social="SOCIAL" if codigo == 101 else None,
                data_nascimento=date(2015, 1, 2),
                cpf="00000000000" if codigo == 101 else None,
            )
            Matricula.objects.create(
                codigo_matricula=codigo,
                aluno_id=codigo,
                codigo_ue="000001",
                ano_letivo=2026,
                codigo_situacao_matricula=1,
                situacao_matricula="Ativo",
                data_situacao_matricula=date(2026, 2, 1),
                origem_atual=True,
            )
            if codigo != 103:
                for sequencia in (1, 2):
                    MatriculaTurma.objects.create(
                        codigo_matricula=codigo,
                        codigo_turma=1000 + codigo,
                        sequencia=sequencia,
                        codigo_situacao_aluno=2 if codigo == 104 else 1,
                        codigo_tipo_turma=1,
                        numero_chamada="0" if sequencia == 1 else None,
                        data_situacao_aluno=date(2026, 2, sequencia),
                        data_atualizacao_tabela=datetime(
                            2026, 2, sequencia, tzinfo=UTC
                        ),
                        origem_atual=True,
                    )
            Matricula.objects.create(
                codigo_matricula=1000 + codigo,
                aluno_id=codigo,
                codigo_ue="000002",
                ano_letivo=2025,
                codigo_situacao_matricula=14,
                situacao_matricula="Remanejado Saída",
                data_situacao_matricula=date(2025, 3, 1),
                data_situacao_matricula_historica=datetime(
                    2025, 2, 1, tzinfo=UTC
                ),
                origem_atual=False,
                origem_historica=True,
            )
            MatriculaTurma.objects.create(
                codigo_matricula=1000 + codigo,
                codigo_turma=2000 + codigo,
                sequencia=1,
                codigo_situacao_aluno=14,
                codigo_tipo_turma=3,
                origem_atual=False,
            )
        for numero in (3, 1, 2):
            ResponsavelAluno.objects.create(
                codigo_responsavel=numero,
                aluno_id=101,
                nome=f"RESPONSAVEL SINTETICO {numero}",
                tipo_responsavel=numero,
                ddd_celular="00" if numero == 1 else None,
                numero_celular="000000000" if numero == 1 else None,
                data_fim_vinculo=date(2025, 1, 1) if numero == 3 else None,
                data_atualizacao_tabela=datetime(2026, 1, numero, tzinfo=UTC),
            )
        Matricula.objects.create(
            codigo_matricula=2104,
            aluno_id=104,
            codigo_ue="000003",
            ano_letivo=2026,
            codigo_situacao_matricula=1,
            situacao_matricula="Ativo",
            origem_atual=False,
            origem_historica=True,
        )
        MatriculaTurma.objects.create(
            codigo_matricula=2104,
            codigo_turma=3104,
            sequencia=1,
            codigo_situacao_aluno=1,
            codigo_tipo_turma=1,
            origem_atual=False,
        )

    def setUp(self) -> None:
        """Fixa o ano usado para selecionar a origem das matrículas."""
        self.enterContext(
            patch(
                "apps.alunos.services.turmas.timezone.now",
                return_value=datetime(2026, 10, 27, tzinfo=UTC),
            )
        )

    @staticmethod
    def _hash(linhas: list) -> str:
        dados = TurmaDoAlunoSerializer(linhas, many=True).data
        return sha256(
            json.dumps(dados, sort_keys=True, ensure_ascii=True).encode()
        ).hexdigest()

    @staticmethod
    def _consultar_lote(
        codigos: Sequence[int], ano: int | None = None
    ) -> list[dict[str, Any]]:
        if ano is None:
            return turmas_service.obter_alunos_por_codigos(codigos)
        return turmas_service.obter_alunos_por_codigos_e_ano(codigos, ano)

    @staticmethod
    def _criar_lote(
        codigos: Sequence[int], codigo_aluno: int | None = None
    ) -> None:
        if codigo_aluno is None:
            Aluno.objects.bulk_create(
                [
                    Aluno(codigo_aluno=codigo, nome="ALUNO SINTETICO")
                    for codigo in codigos
                ]
            )
        Matricula.objects.bulk_create(
            [
                Matricula(
                    codigo_matricula=codigo,
                    aluno_id=codigo if codigo_aluno is None else codigo_aluno,
                    codigo_ue="000001",
                    ano_letivo=2026,
                    codigo_situacao_matricula=1,
                    situacao_matricula="Ativo",
                    origem_atual=True,
                )
                for codigo in codigos
            ]
        )
        MatriculaTurma.objects.bulk_create(
            [
                MatriculaTurma(
                    codigo_matricula=codigo,
                    codigo_turma=codigo,
                    sequencia=1,
                    codigo_situacao_aluno=1,
                    origem_atual=True,
                )
                for codigo in codigos
            ]
        )

    def test_lotes_fazem_quatro_consultas(self) -> None:
        """Mantém quatro consultas para um, seis ou códigos repetidos."""
        for ano in (None, 2026):
            for cenario in ("um", "seis", "repetido"):
                with self.subTest(ano=ano, cenario=cenario):
                    with self.assertNumQueries(4):
                        linhas = self._consultar_lote(
                            CENARIOS_ALUNOS[cenario], ano
                        )
                    self.assertTrue(linhas)

    def test_lotes_preservam_contrato(self) -> None:
        """Preserva os resultados atuais, históricos e futuros."""
        for ano in (None, 2025, 2026, 2027):
            for nome, codigos in CENARIOS_ALUNOS.items():
                with self.subTest(ano=ano, cenario=nome):
                    chave = (
                        f"r02_{nome}" if ano is None else f"r03_{ano}_{nome}"
                    )
                    self.assertEqual(
                        self._hash(self._consultar_lote(codigos, ano)),
                        HASHES_TURMAS[chave],
                    )

    def test_lote_vazio_nao_consulta(self) -> None:
        """Encerra o lote vazio sem consultar o banco."""
        for ano in (None, 2026):
            with self.subTest(ano=ano), self.assertNumQueries(0):
                self.assertEqual(self._consultar_lote([], ano), [])

    def test_fatia_lotes_e_preserva_repeticao_entre_blocos(self) -> None:
        """Mantém a posição dos códigos repetidos ao dividir 501 alunos."""
        self._criar_lote(range(10000, 10501))
        codigos = [*range(10000, 10501), 10000]
        for ano in (None, 2026):
            with self.subTest(ano=ano):
                with self.assertNumQueries(8):
                    linhas = self._consultar_lote(codigos, ano)
                self.assertEqual(
                    [linha["matricula"]["aluno_id"] for linha in linhas],
                    codigos,
                )

    def test_historico_preserva_origens_e_reaproveita_cadastro(self) -> None:
        """Preserva as origens e evita reler o cadastro na busca histórica."""
        for nome, argumentos, consultas in (
            ("r13_atual", (101, 2026, False, False, False), 4),
            ("r13_historico", (101, 2025, True, False, False), 4),
            ("r13_fallback", (104, 2026, False), 6),
        ):
            with self.subTest(cenario=nome):
                with self.assertNumQueries(consultas):
                    linhas = (
                        turmas_service.buscar_turmas_do_aluno_com_historico(
                            *argumentos
                        )
                    )
                self.assertEqual(self._hash(linhas), HASHES_TURMAS[nome])

    def test_historico_inexistente_nao_consulta_cadastro(self) -> None:
        """Dispensa o cadastro quando ambas as origens estão vazias."""
        with self.assertNumQueries(2):
            self.assertEqual(
                turmas_service.buscar_turmas_do_aluno_com_historico(
                    9999, 2026, False
                ),
                [],
            )

    def test_turmas_consultam_apenas_contatos_consumidos(self) -> None:
        """Mantém a resposta sem ler documentos e endereços dos contatos."""
        for nome, chave, consultar in (
            (
                "situacao",
                "r15",
                partial(
                    turmas_service.buscar_turmas_do_aluno_por_situacao_matricula,
                    101,
                    2026,
                    False,
                    False,
                ),
            ),
            (
                "turmas",
                "r16",
                partial(turmas_service.buscar_turmas_do_aluno, 101),
            ),
            (
                "srm_regular",
                "r16",
                partial(
                    turmas_service.buscar_turmas_srm_regular_do_aluno, 101, []
                ),
            ),
        ):
            with self.subTest(cenario=nome):
                with CaptureQueriesContext(connection) as capturadas:
                    linhas = consultar()
                self.assertEqual(len(capturadas), 4)
                self.assertEqual(self._hash(linhas), HASHES_TURMAS[chave])
                sql = next(
                    q["sql"]
                    for q in capturadas
                    if 'FROM "responsavel_aluno"' in q["sql"]
                )
                for coluna in ("cpf", "email", "logradouro", "cep"):
                    self.assertNotIn(f'"{coluna}"', sql)

    def test_fatia_matriculas_quando_um_aluno_excede_o_limite(self) -> None:
        """Divide a busca de turmas de um aluno com mais de 500 matrículas."""
        self._criar_lote(range(10000, 10501), codigo_aluno=101)
        for ano in (None, 2026):
            with self.subTest(ano=ano):
                with self.assertNumQueries(5):
                    linhas = self._consultar_lote([101], ano)
                self.assertEqual(
                    len(
                        {
                            linha["matricula"]["codigo_matricula"]
                            for linha in linhas
                        }
                    ),
                    502,
                )

    def test_lotes_preservam_ordem_das_consultas_individuais(self) -> None:
        """Preserva a ordem dos empates entre matrículas e turmas."""
        codigos = [106, 101, 102, 103, 104, 105, 101]
        for codigo in range(101, 107):
            Matricula.objects.create(
                codigo_matricula=4000 + codigo,
                aluno_id=codigo,
                codigo_ue="000001",
                ano_letivo=2026,
                codigo_situacao_matricula=1,
                situacao_matricula="Ativo",
                data_situacao_matricula=date(2026, 2, 1),
                origem_atual=True,
            )
            for matricula in (codigo, 4000 + codigo):
                for turma in (5000 + codigo, 6000 + codigo):
                    MatriculaTurma.objects.create(
                        codigo_matricula=matricula,
                        codigo_turma=turma,
                        sequencia=2,
                        codigo_situacao_aluno=1,
                        codigo_tipo_turma=1,
                        origem_atual=True,
                        data_situacao_aluno=date(2026, 2, 2),
                        data_atualizacao_tabela=datetime(
                            2026, 2, 2, tzinfo=UTC
                        ),
                    )
        for ano in (None, 2026):
            with self.subTest(ano=ano):
                referencia = [
                    linha
                    for codigo in codigos
                    for linha in (
                        turmas_service._turmas_atuais_por_aluno(codigo)
                        if ano is None
                        else turmas_service._consultar_turmas_do_aluno(
                            codigo, ano, False, False, False
                        )
                    )
                ]
                with CaptureQueriesContext(connection) as capturadas:
                    lote = self._consultar_lote(codigos, ano)
                self.assertEqual(len(capturadas), 4)
                self.assertEqual(self._hash(lote), self._hash(referencia))
