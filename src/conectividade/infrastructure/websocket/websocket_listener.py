"""
Captura todos os WebSockets abertos por uma página Playwright, ativos ou
futuros, e encaminha os frames recebidos para um callback externo.

Diferente de um simples `page.on("websocket", ...)`, este componente lida
com o caso em que o WebSocket é aberto *antes* de o callback de negócio
estar pronto para ser registrado (ex.: durante a montagem de outros
componentes da aplicação): os sockets já vistos ficam guardados e recebem
o listener assim que `registrar()` é chamado.

Esta classe não conhece o protocolo Shiny nem interpreta mensagens — só
observa e repassa.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from playwright.sync_api import Page, WebSocket

logger = logging.getLogger(__name__)

FrameRecebidoCallback = Callable[[str], None]


class WebSocketListener:
    """Captura todos os WebSockets da página, ativos ou futuros."""

    def __init__(self, page: Page) -> None:
        self._page = page
        self._frame_recebido: FrameRecebidoCallback | None = None
        self._sockets_capturados: list[WebSocket] = []

        # Registra o handler antes que qualquer WebSocket seja criado.
        self._page.on("websocket", self._ao_criar_websocket)

    def registrar(self, frame_recebido: FrameRecebidoCallback) -> None:
        """
        Define o callback de frames e o anexa a todos os WebSockets já
        capturados até este momento (e, via `_ao_criar_websocket`, aos que
        vierem a ser abertos depois).
        """
        self._frame_recebido = frame_recebido

        for socket in self._sockets_capturados:
            logger.debug("Registrando listener no socket existente: %s", socket.url)
            socket.on("framereceived", self._ao_receber_frame)

    def _ao_criar_websocket(self, ws: Any) -> None:
        """Guarda o socket e, se já houver callback, anexa o listener imediatamente."""
        websocket = cast("WebSocket", ws)

        logger.debug("WebSocket detectado: %s", websocket.url)
        self._sockets_capturados.append(websocket)

        if self._frame_recebido is not None:
            websocket.on("framereceived", self._ao_receber_frame)

    def _ao_receber_frame(self, payload: str) -> None:
        """Encaminha a mensagem recebida para o callback externo."""
        logger.debug("Frame recebido (%d bytes): %.100s...", len(payload), payload)

        if self._frame_recebido is None:
            return

        try:
            self._frame_recebido(payload)
        except Exception:
            logger.exception("Falha ao processar frame recebido do WebSocket.")
