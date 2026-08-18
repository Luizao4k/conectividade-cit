"""Espera pela conexão de WebSocket do runtime Shiny estar pronta."""
from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.sync_api import Page

logger = logging.getLogger(__name__)


class AguardadorConexaoShiny:
    """Aguarda o Shiny estabelecer a conexão de WebSocket com o servidor."""

    def __init__(self, page: Page, *, timeout_segundos: float, intervalo_polling: float) -> None:
        self._page = page
        self._timeout_segundos = timeout_segundos
        self._intervalo_polling = intervalo_polling

    def aguardar(self) -> None:
        """
        Bloqueia até o Shiny estar conectado.

        Raises:
            TimeoutError: Se a conexão não for estabelecida dentro do timeout.
        """
        logger.info("Aguardando conexão do Shiny...")

        inicio = time.monotonic()

        while time.monotonic() - inicio < self._timeout_segundos:
            if self._conectado():
                logger.info("Shiny conectado.")
                return

            self._page.wait_for_timeout(int(self._intervalo_polling * 1000))

        raise TimeoutError(f"Shiny não conectou em {self._timeout_segundos:.0f} segundos.")

    def _conectado(self) -> bool:
        """Verifica se o WebSocket do Shiny está conectado (readyState == OPEN)."""
        try:
            estado = self._page.evaluate(
                """
                () => ({
                    shiny: !!window.Shiny,
                    app: !!window.Shiny?.shinyapp,
                    socket: window.Shiny?.shinyapp?.$socket?.readyState ?? null,
                })
                """
            )
        except Exception as exc:
            if "Execution context was destroyed" in str(exc):
                return False
            raise

        return bool(estado["shiny"] and estado["app"] and estado["socket"] == 1)
