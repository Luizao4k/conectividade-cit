"""
Representa uma mensagem do protocolo WebSocket do Shiny já decodificada
em suas três partes, mas ainda sem interpretação de negócio nenhuma.

O formato bruto recebido no WebSocket é uma string como:

    a["C2#0|m|{"errors":{},"values":{...}}"]

Ou seja: um array JSON com um único elemento string, no formato
`TAG#CONTADOR|m|JSON`. `FrameBruto` é o resultado de decodificar isso —
o próximo passo (rotear/parsear) fica em `frame_router.py` e nos parsers.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FrameBruto:
    """Uma mensagem do Shiny já decodificada, mas ainda no formato bruto do portal."""

    tag: str
    """Identificador sequencial atribuído pelo Shiny (ex.: "C2"). Não é estável
    entre consultas — não deve ser usado para decidir o tipo do frame."""

    contador: int
    """Contador incremental do Shiny (a parte após "#"). Útil só para depuração."""

    valores: dict[str, object]
    """Conteúdo de `payload["values"]`, ou `{}` se ausente."""

    erros: dict[str, object]
    """Conteúdo de `payload["errors"]`, ou `{}` se ausente."""

    recalculando: dict[str, object] | None
    """Conteúdo de `payload["recalculating"]`, quando o frame é apenas um
    aviso de início/fim de processamento (sem dado de negócio)."""


@dataclass(frozen=True, slots=True)
class FrameFechamento:
    """Representa um frame de fechamento do socket SockJS (`TAG#CONTADOR|c|JSON`).

    O Shiny usa esse tipo de frame para avisar que o socket vai fechar —
    seja um fechamento normal (código 1000) ou porque a aplicação no
    servidor caiu/reiniciou (ex.: código 4503, "The application
    unexpectedly exited"). Diferente de `FrameBruto`, não carrega dados
    de negócio: só o motivo do fechamento.
    """

    code: int
    reason: str
