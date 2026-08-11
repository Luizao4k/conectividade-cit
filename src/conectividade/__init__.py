"""
Módulo de consulta ao portal Conectividade na Educação.

Uso:

    from conectividade import criar_consulta_service
    from conectividade.infrastructure.browser import Browser

    with Browser(url_portal=URL_PORTAL, headless=False) as browser:
        browser.abrir_portal()  # ou navegue manualmente, se houver um passo de proxy
        consulta_service = criar_consulta_service(browser.page)

        resultado = consulta_service.consultar("15001156")
        resultados = consulta_service.consultar_lote(["15001156", "11000222"])

Veja `docs/CONSULTA_INDIVIDUAL.md` para o guia completo.
"""
from __future__ import annotations

from conectividade.application.consulta_escola_service import ConsultaEscolaService
from conectividade.domain.conectividade import Conectividade
from conectividade.domain.consulta_escola import ConsultaEscola
from conectividade.domain.erro_consulta import ErroConsulta
from conectividade.domain.escola import Escola
from conectividade.domain.exceptions import (
    ConsultaEscolaError,
    EscolaNaoEncontradaError,
    RespostaIncompletaError,
)
from conectividade.domain.provedores import Provedores
from conectividade.factory import criar_consulta_service

__all__ = [
    "criar_consulta_service",
    "ConsultaEscolaService",
    "ConsultaEscola",
    "Escola",
    "Conectividade",
    "Provedores",
    "ErroConsulta",
    "ConsultaEscolaError",
    "EscolaNaoEncontradaError",
    "RespostaIncompletaError",
]
