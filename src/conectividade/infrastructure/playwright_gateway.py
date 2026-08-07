"""
Adapter de infraestrutura: implementa `ConsultaEscolaGateway` usando
Playwright (navegador) + WebSocket (protocolo Shiny/SockJS).

O que este arquivo assume que você já tem resolvido no seu projeto atual
(navegação, autenticação no proxy, acesso ao portal) está isolado nos
métodos `_inicializar_navegador`, `_autenticar_proxy` e `_acessar_portal`,
marcados com TODO — é só colar a lógica já validada ali dentro.

O que é NOVO e está implementado por completo aqui é a ponte entre "uma
mensagem crua chegou no WebSocket" e "tenho um `ConsultaEscola` tipado":
decodificar o envelope SockJS, rotear cada mensagem para o parser certo,
acumular no `AgregadorDeConsulta` e devolver o agregado de domínio assim
que a consulta estiver completa (ou estourar o timeout).
"""
from __future__ import annotations

import time
from collections.abc import Sequence
from typing import TYPE_CHECKING

from conectividade.domain.consulta_escola import ConsultaEscola
from conectividade.domain.exceptions import RespostaIncompletaError
from conectividade.infrastructure.shiny.aggregator import AgregadorDeConsulta
from conectividade.infrastructure.shiny.frame_parser import (
    decodificar_envelope,
    parse_mensagem_bruta,
)
from conectividade.infrastructure.shiny.frame_router import RoteadorDeFrames

if TYPE_CHECKING:
    from playwright.sync_api import Page, WebSocket

_TIMEOUT_PADRAO_SEGUNDOS = 15.0
_INTERVALO_POLLING_SEGUNDOS = 0.1


class PortalConectividadeGateway:
    """
    Implementação de `ConsultaEscolaGateway` que fala com o portal
    Conectividade na Educação via navegador (Playwright) e WebSocket (Shiny).

    O roteador de frames é injetável (Dependency Injection): passe uma
    instância customizada de `RoteadorDeFrames` (ex.: com parsers extras
    em teste) se precisar.
    """

    def __init__(
        self,
        *,
        url_portal: str,
        timeout_segundos: float = _TIMEOUT_PADRAO_SEGUNDOS,
        roteador: RoteadorDeFrames | None = None,
    ) -> None:
        self._url_portal = url_portal
        self._timeout_segundos = timeout_segundos
        self._roteador = roteador if roteador is not None else RoteadorDeFrames()

    def consultar(self, inep: str) -> ConsultaEscola:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            pagina = self._preparar_pagina(playwright)
            return self._consultar_na_pagina(pagina, inep)

    def consultar_lote(self, ineps: Sequence[str]) -> list[ConsultaEscola]:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            pagina = self._preparar_pagina(playwright)
            return [self._consultar_na_pagina(pagina, inep) for inep in ineps]

    def _preparar_pagina(self, playwright: object) -> "Page":
        navegador = self._inicializar_navegador(playwright)
        pagina = navegador.new_page()
        self._autenticar_proxy(pagina)
        self._acessar_portal(pagina)
        return pagina

    def _consultar_na_pagina(self, pagina: "Page", inep: str) -> ConsultaEscola:
        agregador = AgregadorDeConsulta(inep=inep)

        def _ao_receber_frame(texto_recebido: str) -> None:
            for mensagem in decodificar_envelope(texto_recebido):
                frame = parse_mensagem_bruta(mensagem)
                if frame is None:
                    continue
                for processado in self._roteador.rotear(frame):
                    agregador.registrar(processado)

        def _ao_abrir_websocket(ws: "WebSocket") -> None:
            ws.on("framereceived", _ao_receber_frame)

        pagina.on("websocket", _ao_abrir_websocket)

        pagina.evaluate(
            "(inep) => Shiny.setInputValue('inep_plano', inep, {priority: 'event'})",
            inep,
        )

        self._aguardar_conclusao(pagina, agregador)

        return agregador.montar()

    def _aguardar_conclusao(self, pagina: "Page", agregador: AgregadorDeConsulta) -> None:
        """
        Espera até `agregador.completo` ficar True, cedendo periodicamente
        o controle para o Playwright processar eventos de WebSocket
        pendentes (via `wait_for_timeout`), ou estoura o timeout.

        Valide esta estratégia de espera no seu ambiente real: o
        importante é garantir que os eventos `framereceived` continuem
        sendo processados enquanto este laço roda.
        """
        limite = time.monotonic() + self._timeout_segundos
        while time.monotonic() < limite:
            if agregador.completo:
                return
            pagina.wait_for_timeout(_INTERVALO_POLLING_SEGUNDOS * 1000)

        raise RespostaIncompletaError(
            f"Consulta ao INEP {agregador.inep!r} não recebeu frames suficientes "
            f"dentro do timeout de {self._timeout_segundos}s."
        )

    # --- Pontos a preencher com a lógica já validada do seu projeto atual ---

    def _inicializar_navegador(self, playwright: object) -> object:
        """TODO: colar aqui a inicialização de navegador já validada (browser, contexto, etc.)."""
        raise NotImplementedError(
            "Substitua por: playwright.chromium.launch(...) já validado no seu projeto atual."
        )

    def _autenticar_proxy(self, pagina: "Page") -> None:
        """TODO: colar aqui a autenticação no proxy corporativo já validada."""
        raise NotImplementedError

    def _acessar_portal(self, pagina: "Page") -> None:
        """TODO: colar aqui a navegação até o portal (ex.: pagina.goto(self._url_portal))."""
        raise NotImplementedError
