"""
Cliente responsável pela comunicação com o portal via protocolo Shiny
(WebSocket), usado pela API pública da biblioteca
(`conectividade.criar_consulta_service`).

Este é o adapter concreto por trás da porta `ConsultaEscolaGateway`
(através de `PortalConectividadeGateway`, em `gateway/portal_gateway.py`):
envia o INEP para o input do Shiny, escuta os frames do WebSocket via
`WebSocketListener`, roteia cada frame para o parser certo
(`RoteadorDeFrames`) e acumula o resultado em `AgregadorDeConsulta` até a
consulta estar completa ou estourar o timeout.

Nota: este NÃO é o mecanismo usado pelo processamento em lote via CSV
(`conectividade.lote`), que consulta o portal fazendo *polling* direto de
`Shiny.shinyapp.$values` em vez de interceptar frames de WebSocket — ver
`docs/ARQUITETURA.md` para a justificativa de manter os dois mecanismos.
"""

from __future__ import annotations

import logging
import time
from dataclasses import replace as dataclasses_replace
from typing import TYPE_CHECKING

from conectividade.domain.consulta_escola import ConsultaEscola
from conectividade.domain.exceptions import (
    AplicacaoShinyEncerradaError,
    RespostaIncompletaError,
)
from conectividade.infrastructure.shiny.aggregator import AgregadorDeConsulta
from conectividade.infrastructure.shiny.frame_parser import (
    decodificar_envelope,
    parse_mensagem_bruta,
    parse_mensagem_fechamento,
)
from conectividade.infrastructure.shiny.frame_bruto import FrameBruto
from conectividade.infrastructure.shiny.frame_router import RoteadorDeFrames
from conectividade.infrastructure.websocket.websocket_listener import WebSocketListener

if TYPE_CHECKING:
    from playwright.sync_api import Page

logger = logging.getLogger(__name__)

_TIMEOUT_PADRAO_SEGUNDOS = 120.0
_TIMEOUT_CONEXAO_SHINY_SEGUNDOS = 90.0
_TIMEOUT_CONFIRMACAO_INPUT_SEGUNDOS = 10.0
_INTERVALO_POLLING_SEGUNDOS = 0.1

# Campos de escola realmente utilizados pelo domínio (só para o log de
# depuração de frames — não afeta o roteamento em si, que é feito pelo
# `RoteadorDeFrames`).
_CAMPOS_ESCOLA = frozenset(
    {
        "nome_escola",
        "uf_escola",
        "dependencia_escola",
        "estudantes_escola",
        "medicoes_escola",
        "max_95_down",
        "vel_adequada",
    }
)


class ShinyClient:
    """Cliente responsável pela comunicação com o portal via protocolo Shiny."""

    def __init__(
        self,
        page: Page,
        *,
        timeout_segundos: float = _TIMEOUT_PADRAO_SEGUNDOS,
        roteador: RoteadorDeFrames | None = None,
    ) -> None:
        self._page = page
        self._timeout_segundos = timeout_segundos
        self._roteador = roteador or RoteadorDeFrames()
        self._listener = WebSocketListener(page)

    def consultar(self, inep: str) -> ConsultaEscola:
        """Consulta uma escola pelo código INEP e devolve o agregado de domínio."""
        agregador = AgregadorDeConsulta(inep)

        self._listener.registrar(
            frame_recebido=lambda frame: self._processar_frame(frame, agregador)
        )

        self._aguardar_shiny_pronto()
        self._enviar_inep(inep)
        self._aguardar_conclusao(agregador)

        return agregador.montar()

    def _aguardar_shiny_pronto(self) -> None:
        """Aguarda o Shiny estabelecer conexão de WebSocket com o servidor."""
        inicio = time.monotonic()

        while time.monotonic() - inicio < _TIMEOUT_CONEXAO_SHINY_SEGUNDOS:
            estado = self._page.evaluate(
                """
                () => ({
                    shiny: !!window.Shiny,
                    initialized: window.Shiny?.initialized,
                    app: !!window.Shiny?.shinyapp,
                    connected: window.Shiny?.shinyapp?.isConnected?.(),
                    socket: window.Shiny?.shinyapp?.$socket?.readyState ?? null,
                })
                """
            )
            logger.debug("Estado do Shiny: %s", estado)

            if estado["connected"] is True and estado["socket"] == 1:
                logger.debug("Shiny conectado.")
                return

            self._page.wait_for_timeout(1000)

        raise TimeoutError(
            f"Shiny não conectou em {_TIMEOUT_CONEXAO_SHINY_SEGUNDOS:.0f} segundos."
        )

    def _enviar_inep(self, inep: str) -> None:
        """Preenche o campo de INEP e confirma que o Shiny recebeu o valor."""
        campo = self._page.locator("#inep_plano")
        campo.wait_for(state="visible", timeout=int(_TIMEOUT_CONFIRMACAO_INPUT_SEGUNDOS * 1000))

        campo.click()
        campo.fill("")
        campo.press_sequentially(inep, delay=120)

        estado = self._page.evaluate(
            """
            () => ({
                dom: document.querySelector("#inep_plano")?.value,
                shiny: Shiny.shinyapp?.$inputValues?.inep_plano,
                socket: Shiny.shinyapp?.$socket?.readyState,
            })
            """
        )
        logger.debug("Estado do input após preenchimento: %s", estado)

        try:
            self._page.wait_for_function(
                "() => Shiny.shinyapp && Shiny.shinyapp.$busyCount > 0",
                timeout=5000,
            )
            logger.debug("Shiny iniciou o processamento.")
        except Exception:
            logger.debug("busyCount não mudou dentro do tempo esperado; prosseguindo mesmo assim.")

    def _processar_frame(self, texto: str, agregador: AgregadorDeConsulta) -> None:
        """Callback do WebSocket: decodifica, normaliza e roteia cada mensagem do frame."""
        logger.debug("Frame bruto recebido (%d bytes): %.200s", len(texto), texto)

        try:
            for mensagem in decodificar_envelope(texto):
                fechamento = parse_mensagem_fechamento(mensagem)
                if fechamento is not None:
                    logger.debug(
                        "Frame de fechamento: code=%s reason=%r", fechamento.code, fechamento.reason
                    )
                    agregador.registrar_fechamento(fechamento)
                    continue

                frame = parse_mensagem_bruta(mensagem)
                if frame is None:
                    continue

                frame = _normalizar_valores_html(frame)

                if frame.valores:
                    logger.debug(
                        "Frame com campos de escola: %s",
                        sorted(_CAMPOS_ESCOLA.intersection(frame.valores.keys())),
                    )

                for evento in self._roteador.rotear(frame):
                    agregador.registrar(evento)
        except Exception:
            logger.exception("Falha ao processar frame recebido do Shiny.")

    def _aguardar_conclusao(self, agregador: AgregadorDeConsulta) -> None:
        """
        Espera até `agregador.completo` ficar True, cedendo periodicamente o
        controle para o Playwright processar eventos de WebSocket pendentes.
        """
        limite = time.monotonic() + self._timeout_segundos

        while time.monotonic() < limite:
            if agregador.fechamento_anormal is not None:
                fechamento = agregador.fechamento_anormal
                raise AplicacaoShinyEncerradaError(
                    "A aplicação Shiny do portal encerrou durante a consulta "
                    f"ao INEP {agregador.inep!r} "
                    f"(code={fechamento.code}, reason={fechamento.reason!r})."
                )

            if agregador.completo:
                return

            self._page.wait_for_timeout(int(_INTERVALO_POLLING_SEGUNDOS * 1000))

        raise RespostaIncompletaError(
            f"A consulta ao INEP {agregador.inep!r} não foi concluída em "
            f"{self._timeout_segundos:.1f}s."
        )


def _normalizar_valores_html(frame: FrameBruto) -> FrameBruto:
    """Substitui valores `{"html": ..., ...}` pelo texto do HTML, sem remover campos."""
    if not frame.valores:
        return frame

    valores_normalizados = {
        chave: (valor["html"] if isinstance(valor, dict) and "html" in valor else valor)
        for chave, valor in frame.valores.items()
    }
    return dataclasses_replace(frame, valores=valores_normalizados)
