# src/conectividade/infrastructure/websocket/websocket_listener.py

from __future__ import annotations

import logging
from typing import Callable, Optional

from playwright.sync_api import Page

logger = logging.getLogger(__name__)


class WebSocketListener:
    """Captura todos os WebSockets da página, ativos ou futuros."""

    def __init__(self, page: Page) -> None:
        self._page = page
        self._frame_recebido: Optional[Callable[[str], None]] = None
        self._debug = True
        self._ws_list = []  # Armazena todos os sockets capturados

        # Registra o handler antes que qualquer WebSocket seja criado
        self._page.on("websocket", self._on_websocket_created)

    def _on_websocket_created(self, ws) -> None:
        """Armazena o socket e, se já houver callback, anexa o listener."""
        if self._debug:
            print(f"[DEBUG] WebSocket detectado: {ws.url}")
        self._ws_list.append(ws)

        # Se o callback já foi registrado, conecta imediatamente
        if self._frame_recebido is not None:
            ws.on("framereceived", self._on_frame_received)

    def _on_frame_received(self, payload: str) -> None:
        """Encaminha a mensagem para o callback externo."""
        if self._debug:
            print(f"[DEBUG] Frame recebido: {payload[:100]}...")
        if self._frame_recebido:
            try:
                self._frame_recebido(payload)
            except Exception as e:
                print(f"[ERRO] No callback do frame: {e}")
                import traceback
                traceback.print_exc()

    def registrar(self, frame_recebido: Callable[[str], None]) -> None:
        """
        Define o callback e anexa listeners a todos os WebSockets
        já capturados.
        """
        self._frame_recebido = frame_recebido

        for ws in self._ws_list:
            if self._debug:
                print(f"[DEBUG] Registrando listener no socket existente: {ws.url}")
            ws.on("framereceived", self._on_frame_received)
