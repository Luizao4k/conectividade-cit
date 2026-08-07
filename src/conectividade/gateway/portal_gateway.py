"""
Adapter que implementa a porta `ConsultaEscolaGateway` utilizando o
cliente do portal Conectividade na Educação.

Toda a comunicação com Playwright, WebSocket e protocolo Shiny é
delegada ao `ShinyClient`.
"""

from __future__ import annotations

from collections.abc import Sequence

from conectividade.application.ports import ConsultaEscolaGateway
from conectividade.domain.consulta_escola import ConsultaEscola
from conectividade.infrastructure.shiny.shiny_client import ShinyClient


class PortalConectividadeGateway(ConsultaEscolaGateway):
    """
    Implementação da porta de consulta utilizando o portal
    Conectividade na Educação.
    """

    def __init__(self, client: ShinyClient) -> None:
        self._client = client

    def consultar(
        self,
        inep: str,
    ) -> ConsultaEscola:
        """
        Consulta uma escola pelo código INEP.
        """
        return self._client.consultar(inep)

    def consultar_lote(
        self,
        ineps: Sequence[str],
    ) -> list[ConsultaEscola]:
        """
        Consulta vários códigos INEP utilizando a mesma sessão.
        """
        return [
            self.consultar(inep)
            for inep in ineps
        ]
