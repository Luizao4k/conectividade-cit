"""Divide a lista de INEPs entre múltiplas instâncias rodando em paralelo."""
from __future__ import annotations

from conectividade.aplicacao.portas import RepositorioIneps


class RepositorioIneposParticionado:
    """
    Decorator sobre outro `RepositorioIneps` que devolve só a fatia de
    INEPs que cabe a esta instância, quando o processamento é dividido
    entre várias instâncias rodando em paralelo (ver
    `docs/LOTE_OPERACIONAL.md`).

    Implementa a mesma porta `RepositorioIneps` que envolve — o caso de
    uso (`ProcessarLoteUseCase`) não tem nenhuma noção de que existe
    particionamento, só recebe a lista já filtrada.

    Particionamento intercalado (round-robin): o INEP de índice `i` (na
    ordem em que aparece no CSV, entre os válidos) cabe à instância onde
    `i % total_particoes == indice_particao`. Isso tende a distribuir
    melhor eventuais trechos mais lentos do arquivo entre as instâncias
    do que dividir em blocos contínuos.
    """

    def __init__(
        self,
        repositorio: RepositorioIneps,
        *,
        total_particoes: int,
        indice_particao: int,
    ) -> None:
        if total_particoes < 1:
            raise ValueError(f"total_particoes precisa ser >= 1 (recebido: {total_particoes}).")

        if not (0 <= indice_particao < total_particoes):
            raise ValueError(
                f"indice_particao precisa estar entre 0 e {total_particoes - 1} "
                f"(recebido: {indice_particao})."
            )

        self._repositorio = repositorio
        self._total_particoes = total_particoes
        self._indice_particao = indice_particao

    def carregar(self) -> list[str]:
        """Carrega a lista completa do repositório envolvido e devolve só esta fatia."""
        todos_os_ineps = self._repositorio.carregar()

        return [
            inep
            for indice, inep in enumerate(todos_os_ineps)
            if indice % self._total_particoes == self._indice_particao
        ]
