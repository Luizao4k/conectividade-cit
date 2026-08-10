"""
Decodifica o texto cru recebido do WebSocket do Shiny em `FrameBruto`s tipados.

O Shiny roda sobre o protocolo SockJS, que empacota mensagens com um
prefixo de um caractere. O que interessa aqui é o prefixo `a`, que marca
um "array de mensagens" — ex.: `a["C2#0|m|{...}"]`, podendo conter mais
de uma mensagem no mesmo frame de WebSocket. Cada mensagem dentro do
array segue, por sua vez, o formato `TAG#CONTADOR|m|JSON` do Shiny.

Por isso a decodificação acontece em duas etapas:

1. `decodificar_envelope`: abre o envelope SockJS e devolve as mensagens
   individuais (strings) contidas nele.
2. `parse_mensagem_bruta`: decodifica uma dessas mensagens individuais em
   um `FrameBruto`.

Esta é a fronteira do sistema com o mundo externo (texto não confiável).
Por isso ambas as funções são deliberadamente tolerantes: texto que não
seguir o protocolo esperado (heartbeats, aberturas/fechamentos de conexão
SockJS, etc.) resulta em lista vazia / `None`, nunca em exceção — quem
decide o que fazer com um frame não reconhecido é o chamador
(tipicamente: ignorar).
"""
from __future__ import annotations

import json
from typing import TypeGuard

from conectividade.infrastructure.shiny.frame_bruto import FrameBruto, FrameFechamento


def decodificar_envelope(texto_recebido: str) -> list[str]:
    """
    Abre o envelope SockJS `a[...]` e devolve as mensagens individuais nele.

    Retorna lista vazia para qualquer outro tipo de frame SockJS (`o`, `h`,
    `c`, ou um `a[...]` malformado) — esses não carregam mensagens do Shiny.
    """
    if not texto_recebido.startswith("a"):
        return []

    elementos = _json_ou_none(texto_recebido[1:])
    if not isinstance(elementos, list):
        return []

    return [elemento for elemento in elementos if isinstance(elemento, str)]


def parse_mensagem_bruta(mensagem: str) -> FrameBruto | None:
    """
    Converte uma mensagem individual do Shiny (ex.: `"C2#0|m|{...}"`,
    já fora do envelope SockJS) em um `FrameBruto`. Retorna `None` se a
    mensagem não seguir o protocolo `TAG#CONTADOR|m|JSON`.
    """
    cabecalho, separador, corpo = mensagem.partition("|m|")
    if not separador:
        return None

    tag, _, contador_str = cabecalho.partition("#")

    payload = _json_ou_none(corpo)
    if not isinstance(payload, dict):
        return None

    return FrameBruto(
        tag=tag,
        contador=int(contador_str) if contador_str.isdigit() else -1,
        valores=_dict_de_str_ou_vazio(payload.get("values", {})),
        erros=_dict_de_str_ou_vazio(payload.get("errors", {})),
        recalculando=_dict_de_str_ou_none(payload.get("recalculating")),
    )


def parse_mensagem_fechamento(mensagem: str) -> FrameFechamento | None:
    """
    Converte uma mensagem individual de fechamento (ex.:
    `"34#0|c|{\"code\":4503,\"reason\":\"...\"}"`) em um `FrameFechamento`.
    Retorna `None` se a mensagem não for desse tipo (`|c|`) ou se o corpo
    não tiver o formato esperado.
    """
    _cabecalho, separador, corpo = mensagem.partition("|c|")
    if not separador:
        return None

    payload = _json_ou_none(corpo)
    if not isinstance(payload, dict):
        return None

    codigo = payload.get("code")
    motivo = payload.get("reason")
    if not isinstance(codigo, int) or not isinstance(motivo, str):
        return None

    return FrameFechamento(code=codigo, reason=motivo)


def _json_ou_none(texto: str) -> object:
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        return None


def _e_dict_de_str(valor: object) -> TypeGuard[dict[str, object]]:
    return isinstance(valor, dict) and all(isinstance(chave, str) for chave in valor)


def _dict_de_str_ou_vazio(valor: object) -> dict[str, object]:
    return valor if _e_dict_de_str(valor) else {}


def _dict_de_str_ou_none(valor: object) -> dict[str, object] | None:
    return valor if _e_dict_de_str(valor) else None
