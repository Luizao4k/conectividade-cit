"""Envio de um código INEP para o input reativo do Shiny."""
from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from conectividade.lote.infraestrutura.shiny_polling.leitura_reativa import LeitorValoresReativos

if TYPE_CHECKING:
    from playwright.sync_api import Page

logger = logging.getLogger(__name__)

_SELETOR_CAMPO_INEP = "#inep_plano"
_INTERVALO_CONFIRMACAO_SEGUNDOS = 0.2


class EnviadorInep:
    """Preenche o campo de INEP do portal e confirma que o Shiny recebeu o valor."""

    def __init__(
        self,
        page: Page,
        leitor: LeitorValoresReativos,
        *,
        timeout_segundos: float,
    ) -> None:
        self._page = page
        self._leitor = leitor
        self._timeout_segundos = timeout_segundos

    def enviar(self, inep: str) -> None:
        """
        Envia o INEP para o input do Shiny e aguarda a confirmação de que
        tanto o DOM quanto o estado reativo do Shiny refletem o novo valor.

        Raises:
            TimeoutError: Se o Shiny não confirmar o valor dentro do timeout.
        """
        logger.info("Enviando INEP: %s", inep)

        campo = self._page.locator(_SELETOR_CAMPO_INEP)
        campo.wait_for(state="visible", timeout=10_000)
        campo.fill(inep)

        self._page.evaluate(
            """
            (inep) => {
                Shiny.setInputValue(
                    "inep_plano",
                    inep,
                    { priority: "event" }
                );
            }
            """,
            inep,
        )

        self._aguardar_confirmacao(inep)

    def _aguardar_confirmacao(self, inep: str) -> None:
        inicio = time.monotonic()

        while time.monotonic() - inicio < self._timeout_segundos:
            try:
                valor_no_dom = self._page.locator(_SELETOR_CAMPO_INEP).input_value()
                valor_no_shiny = self._leitor.ler_input_inep()
            except Exception as exc:
                if "Execution context was destroyed" in str(exc):
                    self._page.wait_for_timeout(int(_INTERVALO_CONFIRMACAO_SEGUNDOS * 1000))
                    continue
                raise

            if valor_no_dom == inep and valor_no_shiny == inep:
                logger.debug("INEP confirmado no DOM e no Shiny: %s", inep)
                return

            self._page.wait_for_timeout(int(_INTERVALO_CONFIRMACAO_SEGUNDOS * 1000))

        raise TimeoutError(f"Shiny não confirmou o INEP {inep}.")
