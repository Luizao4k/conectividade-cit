"""
Parser do frame de qualidade da conexão.

Exemplo de `values` reconhecido por este parser:

    {
        "nro_medicoes": "1826",
        "perda_pacote": "0",
        "jitter": "0,1",
        "latencia": "39,9",
        "vel_upload": "85,6",
        "vel_download": "86,6",
        "plano_estimado": "103,38",
        "status_medidor": "Medidor ativo"
    }
"""
from __future__ import annotations

from conectividade.infrastructure.shiny.dtos import ConectividadeFrameDTO
from conectividade.infrastructure.shiny.parsers._util import texto

_CHAVES_ESPERADAS = frozenset(
    {
        "nro_medicoes",
        "perda_pacote",
        "jitter",
        "latencia",
        "vel_upload",
        "vel_download",
        "plano_estimado",
        "status_medidor",
    }
)


class ConectividadeFrameParser:
    """Reconhece e converte o frame com as métricas de qualidade da conexão."""

    def reconhece(self, valores: dict[str, object]) -> bool:
        return _CHAVES_ESPERADAS.issubset(valores.keys())

    def parse(self, valores: dict[str, object]) -> ConectividadeFrameDTO:
        return ConectividadeFrameDTO(
            nro_medicoes=texto(valores, "nro_medicoes"),
            perda_pacote=texto(valores, "perda_pacote"),
            jitter=texto(valores, "jitter"),
            latencia=texto(valores, "latencia"),
            vel_upload=texto(valores, "vel_upload"),
            vel_download=texto(valores, "vel_download"),
            plano_estimado=texto(valores, "plano_estimado"),
            status_medidor=texto(valores, "status_medidor"),
        )
