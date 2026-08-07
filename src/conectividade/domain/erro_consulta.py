"""
Value Object: um erro reportado pelo portal durante o processamento de uma consulta.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ErroConsulta:
    """Um erro reportado pelo portal para uma parte específica da consulta."""

    origem: str
    """Identificador do componente do portal que gerou o erro (ex.: nome do gráfico)."""

    mensagem: str
