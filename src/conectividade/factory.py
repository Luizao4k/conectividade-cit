"""
Composição da aplicação (Dependency Injection): monta o
`ConsultaEscolaService` já ligado à implementação real (Shiny sobre uma
página já aberta com Playwright), sem que o código cliente precise
conhecer `ShinyClient`, `RoteadorDeFrames` ou qualquer outro detalhe de
infraestrutura — só chama `consulta_service.consultar(inep)`.

Esta fábrica recebe uma `Page` já pronta (navegador aberto, proxy
configurado, portal carregado) em vez de abrir o navegador ela mesma.
Isso é proposital: quem abre e fecha o navegador (`Browser`, em
`infrastructure/browser/browser.py`) é o composition root da aplicação
cliente desta biblioteca, porque esse processo costuma incluir um passo
manual (ex.: configurar um proxy corporativo) que não faz sentido morar
dentro de uma fábrica de serviço. Veja `docs/CONSULTA_INDIVIDUAL.md`
para um exemplo completo de uso.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from conectividade.application.consulta_escola_service import ConsultaEscolaService
from conectividade.gateway.portal_gateway import PortalConectividadeGateway
from conectividade.infrastructure.shiny.frame_router import RoteadorDeFrames
from conectividade.infrastructure.shiny.shiny_client import ShinyClient

if TYPE_CHECKING:
    from playwright.sync_api import Page


def criar_consulta_service(
    page: Page,
    *,
    timeout_segundos: float = 15.0,
    roteador: RoteadorDeFrames | None = None,
) -> ConsultaEscolaService:
    """
    Cria um `ConsultaEscolaService` pronto para uso, ligado a uma página
    de navegador já aberta e autenticada no portal.

    Args:
        page: Página do Playwright já com o portal carregado (ex.:
            `browser.page`, após `Browser` ter sido aberto e o proxy
            configurado — ver `docs/CONSULTA_INDIVIDUAL.md`).
        timeout_segundos: Tempo máximo de espera pelos frames de resposta
            de cada consulta.
        roteador: Roteador de frames customizado (opcional; útil em
            testes, para injetar parsers diferentes dos padrão).
    """
    client = ShinyClient(page, timeout_segundos=timeout_segundos, roteador=roteador)
    gateway = PortalConectividadeGateway(client)
    return ConsultaEscolaService(gateway=gateway)
