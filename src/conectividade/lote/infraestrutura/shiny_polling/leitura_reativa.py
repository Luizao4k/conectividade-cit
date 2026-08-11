"""Leitura direta do estado reativo do Shiny (`Shiny.shinyapp.$values`)."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from playwright.sync_api import Page


class LeitorValoresReativos:
    """
    Lê `Shiny.shinyapp.$values` diretamente da página.

    Durante uma reação do Shiny, o contexto JavaScript da página pode ser
    destruído temporariamente (ex.: navegação parcial de componentes
    reativos) — nesse caso a leitura é tratada como "ainda sem dados"
    (`{}`) em vez de propagar o erro, já que o chamador está em um laço de
    polling e vai tentar de novo na próxima iteração.
    """

    def __init__(self, page: Page) -> None:
        self._page = page

    def ler(self) -> dict[str, Any]:
        try:
            valores = self._page.evaluate(
                """
                () => {
                    return window.Shiny
                        ?.shinyapp
                        ?.$values ?? {};
                }
                """
            )
        except Exception as exc:
            if "Execution context was destroyed" in str(exc):
                return {}
            raise

        return valores if isinstance(valores, dict) else {}

    def ler_input_inep(self) -> str:
        """Retorna o valor de `inep_plano` atualmente registrado no Shiny."""
        try:
            valor = self._page.evaluate(
                """
                () => {
                    return window.Shiny
                        ?.shinyapp
                        ?.$inputValues
                        ?.inep_plano ?? "";
                }
                """
            )
        except Exception as exc:
            if "Execution context was destroyed" in str(exc):
                return ""
            raise

        return str(valor)
