"""
Armazenamento dos resultados do lote em CSV, com suporte a retomar um
lote interrompido (checkpoint).
"""
from __future__ import annotations

import csv
from pathlib import Path

from conectividade.dominio.dados_escola import DadosEscolaLote
from conectividade.dominio.resultado_consulta import ResultadoConsultaLote

CAMPOS_RESULTADO: tuple[str, ...] = ("inep", "status", "tempo", *DadosEscolaLote.CAMPOS)
"""Colunas do CSV de resultados, na ordem em que são escritas."""


class RepositorioResultadosLoteCsv:
    """
    Implementação de `RepositorioResultadosLote` (ver
    `aplicacao/portas.py`) que grava cada resultado imediatamente,
    em modo append, em um arquivo CSV.

    Cada linha já salva no arquivo é considerada um INEP "processado" —
    independentemente do status —, permitindo retomar um lote
    interrompido sem reprocessar o que já tem resultado (ver
    `PlanoExecucaoLote`).
    """

    def __init__(self, arquivo: Path) -> None:
        self._arquivo = arquivo

    def carregar_processados(self) -> set[str]:
        """Retorna os INEPs que já têm uma linha de resultado salva."""
        if not self._arquivo.exists():
            return set()

        processados: set[str] = set()

        with self._arquivo.open("r", encoding="utf-8-sig", newline="") as arquivo_csv:
            leitor = csv.DictReader(arquivo_csv)

            for linha in leitor:
                inep = str(linha.get("inep", "")).strip()
                if inep:
                    processados.add(inep)

        return processados

    def salvar(self, resultado: ResultadoConsultaLote) -> None:
        """
        Acrescenta uma linha com o resultado ao CSV, criando o arquivo (e
        o cabeçalho) se ainda não existir. O arquivo é sincronizado em
        disco imediatamente após cada gravação.
        """
        self._arquivo.parent.mkdir(parents=True, exist_ok=True)

        arquivo_ja_existe = self._arquivo.exists()

        registro: dict[str, object] = {
            "inep": resultado.inep,
            "status": resultado.status.value,
            "tempo": f"{resultado.tempo_segundos:.2f}",
        }
        for campo, valor in resultado.dados.como_dict().items():
            registro[campo] = valor if valor is not None else ""

        with self._arquivo.open("a", encoding="utf-8-sig", newline="") as arquivo_csv:
            escritor = csv.DictWriter(arquivo_csv, fieldnames=CAMPOS_RESULTADO, extrasaction="ignore")

            if not arquivo_ja_existe:
                escritor.writeheader()

            escritor.writerow(registro)
            arquivo_csv.flush()
