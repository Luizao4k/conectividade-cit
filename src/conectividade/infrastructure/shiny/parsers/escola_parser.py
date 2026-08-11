"""
Parser do frame principal da consulta por INEP: dados cadastrais da escola.

Exemplo de `values` reconhecido por este parser:

    {
        "nome_escola": "Escola Emeief Pequenos Talentos",
        "uf_escola": "Município: Porto Velho - Rondonia",
        "dependencia_escola": "Gestão: Municipal",
        "estudantes_escola": "Número de estudantes: 211 (Censo 2025)",
        "medicoes_escola": "1830",
        "max_95_down": "94",
        "vel_adequada": "Velocidade adequada: 211Mbit/s"
    }
"""
from __future__ import annotations

import logging

from conectividade.infrastructure.shiny.dtos import EscolaFrameDTO
from conectividade.infrastructure.shiny.parsers._util import texto

logger = logging.getLogger(__name__)

_CHAVES_ESPERADAS = frozenset(
    {
        "nome_escola",
        "uf_escola",
        "dependencia_escola",
        "estudantes_escola",
        "medicoes_escola",
        "max_95_down",
        "vel_adequada",
    }
)


class EscolaFrameParser:
    """Reconhece e converte o frame com os dados cadastrais da escola."""

    def reconhece(self, valores: dict[str, object]) -> bool:
        match = bool(_CHAVES_ESPERADAS.intersection(valores.keys()))
        logger.debug("EscolaFrameParser reconhece=%s chaves=%s", match, list(valores.keys()))
        return match

    def parse(self, valores: dict[str, object]) -> EscolaFrameDTO:
        return EscolaFrameDTO(
            nome_escola=texto(valores, "nome_escola"),
            uf_escola=texto(valores, "uf_escola"),
            dependencia_escola=texto(valores, "dependencia_escola"),
            estudantes_escola=texto(valores, "estudantes_escola"),
            medicoes_escola=texto(valores, "medicoes_escola"),
            max_95_down=texto(valores, "max_95_down"),
            vel_adequada=texto(valores, "vel_adequada"),
        )
