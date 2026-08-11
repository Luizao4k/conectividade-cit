"""Leitura da lista de INEPs a processar a partir de um CSV."""
from __future__ import annotations

import csv
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class RepositorioIneposCsv:
    """
    Implementação de `RepositorioIneps` (ver `lote/aplicacao/portas.py`)
    que lê os códigos INEP de um arquivo CSV com uma coluna `inep`.
    """

    def __init__(self, arquivo: Path) -> None:
        self._arquivo = arquivo

    def carregar(self) -> list[str]:
        """
        Carrega os INEPs válidos do CSV.

        Raises:
            FileNotFoundError: Se o arquivo não existir.
            ValueError: Se o CSV não tiver cabeçalho, não tiver a coluna
                `inep`, ou não sobrar nenhum INEP válido após a leitura.
        """
        if not self._arquivo.exists():
            raise FileNotFoundError(f"Arquivo de INEPs não encontrado: {self._arquivo}")

        ineps: list[str] = []

        with self._arquivo.open("r", encoding="utf-8-sig", newline="") as arquivo_csv:
            leitor = csv.DictReader(arquivo_csv)

            if not leitor.fieldnames:
                raise ValueError("CSV não possui cabeçalho.")

            if "inep" not in leitor.fieldnames:
                raise ValueError("O CSV precisa possuir uma coluna chamada 'inep'.")

            for linha in leitor:
                inep_valido = self._normalizar_inep(str(linha.get("inep", "")))
                if inep_valido is not None:
                    ineps.append(inep_valido)

        if not ineps:
            raise ValueError("Nenhum INEP válido encontrado no CSV.")

        return ineps

    @staticmethod
    def _normalizar_inep(bruto: str) -> str | None:
        """
        Normaliza um valor bruto de INEP.

        Remove o `.0` que o Excel costuma adicionar ao exportar colunas
        numéricas como CSV, e descarta (com aviso) valores que não sejam
        puramente numéricos.
        """
        inep = bruto.strip()

        if not inep:
            return None

        if inep.endswith(".0"):
            inep = inep[:-2]

        if not inep.isdigit():
            logger.warning("INEP inválido ignorado: %s", inep)
            return None

        return inep
