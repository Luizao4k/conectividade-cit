# src/conectividade/infrastructure/shiny/shiny_client.py

from __future__ import annotations

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
from conectividade.infrastructure.shiny.frame_router import RoteadorDeFrames
from conectividade.infrastructure.websocket.websocket_listener import (
    WebSocketListener,
)

if TYPE_CHECKING:
    from playwright.sync_api import Page


_TIMEOUT_PADRAO = 120.0
_INTERVALO_POLLING = 0.1

# Campos realmente utilizados pelo domínio
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
    """
    Cliente responsável pela comunicação com o portal via protocolo Shiny.
    """

    def __init__(
        self,
        page: Page,
        *,
        timeout_segundos: float = _TIMEOUT_PADRAO,
        roteador: RoteadorDeFrames | None = None,
    ) -> None:
        self._page = page
        self._timeout = timeout_segundos
        self._roteador = roteador or RoteadorDeFrames()
        self._listener = WebSocketListener(page)
        self._debug = True

    def consultar(self, inep: str) -> ConsultaEscola:
        print("[CLIENTE]", __file__)

        agregador = AgregadorDeConsulta(inep)

        self._listener.registrar(
            frame_recebido=lambda frame: self._processar_frame(
                frame,
                agregador
            )
        )

        self._aguardar_shiny_pronto()

        self._enviar_inep(inep)

        self._aguardar_conclusao(agregador)

        return agregador.montar()

    def _aguardar_shiny_pronto(self) -> None:
        inicio = time.monotonic()

        while time.monotonic() - inicio < 90:

            estado = self._page.evaluate(
                """
                () => ({
                    shiny: !!window.Shiny,
                    initialized: window.Shiny?.initialized,
                    app: !!window.Shiny?.shinyapp,
                    connected: window.Shiny?.shinyapp?.isConnected?.(),
                    socket: window.Shiny?.shinyapp?.$socket?.readyState ?? null,
                    inputValues: window.Shiny?.shinyapp?.$inputValues
                })
                """
            )

            print("[SHINY STATUS]", estado)

            if (
                estado["connected"] is True
                and estado["socket"] == 1
            ):
                print("[SHINY OK]")
                return

            self._page.wait_for_timeout(1000)

        raise TimeoutError(
            "Shiny não conectou em 90 segundos"
        )

    def _enviar_inep(self, inep: str) -> None:
        campo = self._page.locator("#inep_plano")

        # Aguarda o campo existir
        campo.wait_for(state="visible", timeout=10000)

        # Garante foco
        campo.click()

        # Limpa completamente
        campo.fill("")

        # Digita como um usuário
        campo.press_sequentially(
            inep,
            delay=120,
        )
        print(
            self._page.evaluate(
                """
                () => ({
                    dom:
                    document.querySelector("#inep_plano")?.value,

                    shiny:
                    Shiny.shinyapp?.$inputValues?.inep_plano,

                    socket:
                    Shiny.shinyapp?.$socket?.readyState
                })
                """
            )
        )

        if self._debug:
            estado = self._page.evaluate("""
            () => ({
                input: document.getElementById("inep_plano").value,
                shiny: Shiny.shinyapp?.$inputValues?.inep_plano,
                busy: Shiny.shinyapp?.$busyCount,
                socketReady: Shiny.shinyapp?.$socket?.readyState
            })
            """)

            print("[INPUT]", estado)

        # Aguarda a aplicação reagir
        try:
            self._page.wait_for_function(
                "() => Shiny.shinyapp && Shiny.shinyapp.$busyCount > 0",
                timeout=5000,
            )

            if self._debug:
                print("[DEBUG] Shiny iniciou o processamento.")

        except Exception:
            if self._debug:
                print("[DEBUG] busyCount não mudou.")

    def _processar_frame(
        self,
        texto: str,
        agregador: AgregadorDeConsulta,
    ) -> None:
        print(
            "[FRAME BRUTO]",
            len(texto),
            repr(texto[:200]),
            flush=True,
        )

        try:
            for mensagem in decodificar_envelope(texto):

                fechamento = parse_mensagem_fechamento(mensagem)
                if fechamento is not None:
                    if self._debug:
                        print(
                            "[FECHAMENTO]",
                            f"code={fechamento.code} reason={fechamento.reason!r}",
                        )
                    agregador.registrar_fechamento(fechamento)
                    continue

                frame = parse_mensagem_bruta(mensagem)
                if frame is None:
                    continue

                if frame.valores:

                    # apenas para log
                    valores_resumo = {}

                    for chave, valor in frame.valores.items():
                        if chave not in _CAMPOS_ESCOLA:
                            continue

                        if isinstance(valor, dict) and "html" in valor:
                            valores_resumo[chave] = valor["html"]
                        else:
                            valores_resumo[chave] = valor

                    if self._debug and valores_resumo:
                        print(
                            "[FRAME]",
                            ", ".join(sorted(valores_resumo.keys())),
                        )

                # Apenas normaliza html -> string, sem remover campos
                if frame.valores:

                    valores_normalizados = {}

                    for chave, valor in frame.valores.items():

                        if isinstance(valor, dict) and "html" in valor:
                            valores_normalizados[chave] = valor["html"]
                        else:
                            valores_normalizados[chave] = valor

                    frame = dataclasses_replace(
                        frame,
                        valores=valores_normalizados,
                    )

                for evento in self._roteador.rotear(frame):
                    agregador.registrar(evento)

        except Exception:
            import traceback
            traceback.print_exc()

    def _aguardar_conclusao(
        self,
        agregador: AgregadorDeConsulta,
    ) -> None:

        limite = time.monotonic() + self._timeout

        while time.monotonic() < limite:

            if agregador.fechamento_anormal is not None:
                fechamento = agregador.fechamento_anormal
                raise AplicacaoShinyEncerradaError(
                    f"A aplicação Shiny do portal encerrou durante a "
                    f"consulta ao INEP {agregador.inep!r} "
                    f"(code={fechamento.code}, reason={fechamento.reason!r})."
                )

            if agregador.completo:
                return

            self._page.wait_for_timeout(
                _INTERVALO_POLLING * 1000
            )

        raise RespostaIncompletaError(
            f"A consulta ao INEP {agregador.inep!r} "
            f"não foi concluída em {self._timeout:.1f}s."
        )
