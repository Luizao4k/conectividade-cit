"""
Gerencia uma sessão persistente do Google Chrome utilizando Playwright.

O navegador utiliza um perfil persistente para reutilizar cookies,
autenticação e demais dados da sessão já existente.

Responsabilidades:
    - iniciar o Playwright;
    - abrir um contexto persistente do Chrome;
    - disponibilizar uma página pronta para uso;
    - acessar o portal Conectividade na Educação;
    - encerrar corretamente todos os recursos.

Esta classe não conhece WebSocket, protocolo Shiny ou regras de negócio.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from playwright.sync_api import sync_playwright

if TYPE_CHECKING:
    from playwright.sync_api import (
        BrowserContext,
        Page,
        Playwright,
    )


class Browser:
    """Gerencia uma sessão persistente do navegador."""

    def __init__(
        self,
        *,
        url_portal: str,
        user_data_dir: str | Path = "./perfil_chrome",
        channel: str = "chrome",
        headless: bool = False,
        timeout_ms: int = 30_000,
    ) -> None:
        self._url_portal = url_portal
        self._user_data_dir = str(user_data_dir)
        self._channel = channel
        self._headless = headless
        self._timeout_ms = timeout_ms

        self._playwright: Playwright | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    @property
    def page(self) -> Page:
        """Retorna a página ativa."""

        if self._page is None:
            raise RuntimeError("O navegador ainda não foi iniciado.")

        return self._page

    @property
    def context(self) -> BrowserContext:
        """Retorna o contexto persistente."""

        if self._context is None:
            raise RuntimeError("O navegador ainda não foi iniciado.")

        return self._context

    def __enter__(self) -> Browser:
        """
        Inicializa o navegador e devolve a instância pronta para uso.

        Não navega até o portal automaticamente: quem decide quando (e se)
        navegar é o chamador — ver `abrir_portal()` — porque em alguns
        fluxos operacionais (ex.: configuração manual de proxy corporativo
        antes de qualquer requisição) a navegação precisa esperar um passo
        manual do operador.
        """

        self._iniciar_playwright()
        self._abrir_contexto()
        self._obter_pagina()
        self._configurar_pagina()

        return self

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        """Encerra todos os recursos utilizados."""

        if self._context is not None:
            self._context.close()

        if self._playwright is not None:
            self._playwright.stop()

    def _iniciar_playwright(self) -> None:
        """Inicializa o Playwright."""

        self._playwright = sync_playwright().start()

    def _abrir_contexto(self) -> None:
        """Abre um contexto persistente do Chrome."""

        assert self._playwright is not None

        self._context = (
            self._playwright.chromium.launch_persistent_context(
                user_data_dir=self._user_data_dir,
                channel=self._channel,
                headless=self._headless,
            )
        )

    def _obter_pagina(self) -> None:
        """Obtém a página principal do navegador."""

        assert self._context is not None

        if self._context.pages:
            self._page = self._context.pages[0]
        else:
            self._page = self._context.new_page()

    def _configurar_pagina(self) -> None:
        """Aplica configurações padrão da página."""

        self.page.set_default_timeout(
            self._timeout_ms,
        )

    def abrir_portal(self) -> None:
        """
        Navega até o portal configurado.

        Caso o navegador já esteja na URL correta, evita um novo
        carregamento. Útil para consumidores da biblioteca que não
        precisam de nenhum passo manual (ex.: proxy) antes de navegar —
        para fluxos operacionais com esse passo manual, veja
        `infrastructure/browser/browser.py` usado a partir de `lote/cli.py`,
        que controla a navegação explicitamente.
        """

        if self.page.url != self._url_portal:
            self.page.goto(
                self._url_portal,
                wait_until="domcontentloaded",
            )

        self.page.wait_for_load_state("networkidle")

        self._aguardar_runtime_shiny_carregado()

    def _aguardar_runtime_shiny_carregado(self) -> None:
        """
        Aguarda o script do runtime Shiny estar carregado na página.

        Isto verifica apenas que `window.Shiny` existe — não que o
        WebSocket já está conectado. Para essa garantia mais forte
        (necessária antes de enviar um INEP), veja
        `lote/infrastructure/shiny_polling/aguardador_conexao.py`.
        """

        self.page.wait_for_function(
            "() => typeof window.Shiny !== 'undefined'"
        )

    def nova_pagina(self) -> Page:
        """Cria uma nova página utilizando o mesmo contexto."""

        return self.context.new_page()

    def recarregar(self) -> None:
        """Recarrega a página atual e aguarda o runtime Shiny carregar."""

        self.page.reload(
            wait_until="domcontentloaded",
        )

        self._aguardar_runtime_shiny_carregado()
