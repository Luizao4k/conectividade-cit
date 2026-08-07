"""
Porta (interface) que a camada de aplicação depende — e que a
infraestrutura implementa. É esta interface que permite trocar
Playwright/Shiny por qualquer outra implementação (ou por um dublê em
teste) sem tocar em `ConsultaEscolaService`.

Sendo um `Protocol`, a tipagem é estrutural: qualquer classe com estes
dois métodos serve, sem precisar herdar de nada.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from conectividade.domain.consulta_escola import ConsultaEscola


class ConsultaEscolaGateway(Protocol):
    def consultar(self, inep: str) -> ConsultaEscola:
        """Consulta uma única escola pelo código INEP."""

    def consultar_lote(self, ineps: Sequence[str]) -> list[ConsultaEscola]:
        """Consulta várias escolas, uma consulta por INEP."""
