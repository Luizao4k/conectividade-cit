"""
Value Object: provedores de internet associados a uma escola e à região dela.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Provedores:
    """Provedores atuando no estabelecimento e na região onde ele fica."""

    provedores_regiao: tuple[str, ...]
    provedor_estabelecimento: tuple[str, ...]
