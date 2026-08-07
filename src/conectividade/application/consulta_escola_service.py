"""
Caso de uso principal: consultar dados de escola(s) por código INEP.

Esta classe é a interface pública do módulo (`consulta_service.consultar(inep)`).
Ela não sabe nada sobre Playwright, WebSocket ou o protocolo Shiny — só
conhece a porta `ConsultaEscolaGateway`, injetada no construtor. Trocar a
infraestrutura inteira (ex.: usar uma API oficial no futuro, se o portal
vier a ter uma) não exige mudar nenhuma linha desta classe.
"""
from __future__ import annotations

import re
from collections.abc import Sequence

from conectividade.application.ports import ConsultaEscolaGateway
from conectividade.domain.consulta_escola import ConsultaEscola

_PADRAO_INEP = re.compile(r"^\d{8}$")


class ConsultaEscolaService:
    """Serviço de aplicação para consulta de escolas por código INEP."""

    def __init__(self, gateway: ConsultaEscolaGateway) -> None:
        self._gateway = gateway

    def consultar(self, inep: str) -> ConsultaEscola:
        """
        Consulta uma escola pelo código INEP.

        Raises:
            ValueError: Se `inep` não tiver o formato esperado (8 dígitos).
            EscolaNaoEncontradaError: Se o portal não retornar dados para o INEP.
            RespostaIncompletaError: Se o portal não responder dentro do timeout.
        """
        self._validar_inep(inep)
        return self._gateway.consultar(inep)

    def consultar_lote(self, ineps: Sequence[str]) -> list[ConsultaEscola]:
        """Consulta várias escolas em sequência, uma consulta por INEP."""
        for inep in ineps:
            self._validar_inep(inep)
        return self._gateway.consultar_lote(ineps)

    @staticmethod
    def _validar_inep(inep: str) -> None:
        if not _PADRAO_INEP.fullmatch(inep):
            raise ValueError(
                f"Código INEP inválido: {inep!r} (deve ter 8 dígitos numéricos)."
            )
