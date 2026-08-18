"""Planejamento de quais INEPs faltam processar em uma execução do lote."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PlanoExecucaoLote:
    """
    Resultado de cruzar a lista completa de INEPs com o checkpoint de
    resultados já salvos (`RepositorioResultadosLote.carregar_processados`).

    Um INEP é considerado "já processado" independentemente do status
    salvo anteriormente (inclusive `timeout` ou `erro`) — reexecutar o
    lote não tenta essas falhas de novo automaticamente. Isso preserva o
    comportamento original do checkpoint: para reprocessar falhas, é
    preciso remover as linhas correspondentes do CSV de resultados.
    """

    total_ineps: int
    ja_processados: int
    pendentes: tuple[str, ...]

    @property
    def ha_trabalho_pendente(self) -> bool:
        return len(self.pendentes) > 0
