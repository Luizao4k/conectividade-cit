"""
Parser do frame de provedores.

Exemplo de `values` reconhecido por este parser:

    {
        "provedoresSIMET_regiao": "V Tal, Globofiber Telecom, Candeias Net Telecom Comunicacoes Ltda",
        "provedor_do_estabelecimento": "Globofiber Telecom, Candeias Net Telecom Comunicacoes Ltda"
    }
"""
from __future__ import annotations

from conectividade.infrastructure.shiny.dtos import ProvedoresFrameDTO
from conectividade.infrastructure.shiny.parsers._util import texto

_CHAVES_ESPERADAS = frozenset({"provedoresSIMET_regiao", "provedor_do_estabelecimento"})


class ProvedoresFrameParser:
    """Reconhece e converte o frame com os provedores da escola e da região."""

    def reconhece(self, valores: dict[str, object]) -> bool:
        match = bool(_CHAVES_ESPERADAS.intersection(valores.keys()))
        print("[PARSER ESCOLA]", match, valores.keys())
        return match

    def parse(self, valores: dict[str, object]) -> ProvedoresFrameDTO:
        return ProvedoresFrameDTO(
            provedores_regiao=texto(valores, "provedoresSIMET_regiao"),
            provedor_estabelecimento=texto(valores, "provedor_do_estabelecimento"),
        )
