"""
Cliente responsável por observar conexões WebSocket abertas pela página.

Este componente encapsula a integração com os eventos WebSocket do
Playwright, notificando um callback sempre que um frame de texto for
recebido.

Ele não conhece o protocolo Shiny nem interpreta mensagens.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, cast, Any

if TYPE_CHECKING:
    from playwright.sync_api import Page, WebSocket

FrameRecebidoCallback = Callable[[str], None]


class WebSocketClient:
    """
    Observa conexões WebSocket abertas por uma página Playwright.
    """

    def __init__(self, page: Page) -> None:
        self._page = page

    def registrar_listener(
        self,
        callback: FrameRecebidoCallback,
    ) -> None:
        """
        Registra um callback para todos os frames recebidos.

        Args:
            callback:
                Função chamada sempre que um frame de texto for recebido.
        """

        def _ao_abrir_websocket(ws: WebSocket) -> None:
            # O Playwright suporta o evento "framereceived" em tempo de execução,
            # porém os stubs de tipagem ainda não o expõem.
            websocket = cast(Any, ws)

            websocket.on(
                "framereceived",
                callback,
            )

        self._page.on(
            "websocket",
            _ao_abrir_websocket,
        )
