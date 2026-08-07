"""
Gerencia o ciclo de vida do navegador Playwright.

Esta classe é responsável por:

- iniciar o Playwright;
- abrir o navegador;
- criar uma página;
- autenticar no proxy corporativo;
- acessar o portal.

Após a inicialização, disponibiliza uma instância de `Page`
pronta para uso pelas demais camadas da aplicação.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from playwright.sync_api import sync_playwright

if TYPE_CHECKING:
    from playwright.sync_api import Browser as PlaywrightBrowser
    from playwright.sync_api import BrowserContext
    from playwright.sync_api import Page
    from playwright.sync_api import Playwright


class Browser:
    """
    Gerencia uma sessão do navegador Playwright.
    """

    def __init__(
        self,
        *,
        url_portal: str,
        headless: bool = False,
    ) -> None:
        self._url_portal = url_portal
        self._headless = headless

        self._playwright: Playwright | None = None
        self._browser: PlaywrightBrowser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    def __enter__(self) -> Page:
        """
        Inicializa o navegador e retorna uma página pronta para uso.
        """

        self._playwright = sync_playwright().start()

        self._browser = self._playwright.chromium.launch(
            headless=self._headless,
        )

        self._context = self._browser.new_context()

        self._page = self._context.new_page()

        #self._autenticar_proxy()

        self._acessar_portal()

        return self._page

    def __exit__(
        self,
        exc_type: object,
        exc: object,
        tb: object,
    ) -> None:
        """
        Finaliza todos os recursos do Playwright.
        """

        if self._context is not None:
            self._context.close()

        if self._browser is not None:
            self._browser.close()

        if self._playwright is not None:
            self._playwright.stop()

        #def _autenticar_proxy(self) -> None:

        #Realiza a autenticação no proxy corporativo.

        #Raises:
            #ProxyAuthenticationError:
                #Se a autenticação não puder ser concluída.


        #assert self._page is not None

    def _acessar_portal(self) -> None:
        """
        Navega até o portal Conectividade na Educação.

        TODO:
            Mover para cá a lógica já existente no projeto.
        """

        assert self._page is not None

        self._page.goto(self._url_portal)
