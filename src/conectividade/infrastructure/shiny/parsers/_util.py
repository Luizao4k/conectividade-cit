"""Helper interno compartilhado pelos parsers de frame."""
from __future__ import annotations

from conectividade.infrastructure.shiny.exceptions import FrameInvalidoError


def texto(
    valores: dict[str, object],
    chave: str,
) -> str | None:
    valor = valores.get(chave)

    if valor is None:
        return None

    if not isinstance(valor, str):
        raise FrameInvalidoError(
            f"Esperava uma string em {chave!r}, recebeu {type(valor).__name__}: {valor!r}"
        )

    return str(valor)
