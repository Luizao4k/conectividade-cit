"""
Roteia frames brutos do Shiny para o(s) parser(es) especializado(s)
correspondente(s).

Ver `README.md` / `docs/CONSULTA_INDIVIDUAL.md` para a explicação de por
que o roteamento é feito pelo *conteúdo* do frame (conjunto de chaves em
`values`), e não pela tag sequencial do Shiny.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any

from conectividade.infrastructure.shiny.dtos import ErroFrameDTO, FrameProcessado
from conectividade.infrastructure.shiny.frame_bruto import FrameBruto
from conectividade.infrastructure.shiny.parsers.base import ParserDeFrame
from conectividade.infrastructure.shiny.parsers.conectividade_parser import (
    ConectividadeFrameParser,
)
from conectividade.infrastructure.shiny.parsers.escola_parser import EscolaFrameParser
from conectividade.infrastructure.shiny.parsers.provedores_parser import ProvedoresFrameParser

logger = logging.getLogger(__name__)

_PARSERS_PADRAO: tuple[ParserDeFrame[Any], ...] = (
    EscolaFrameParser(),
    ConectividadeFrameParser(),
    ProvedoresFrameParser(),
)


class RoteadorDeFrames:
    """Roteia frames brutos para o parser especializado correspondente."""

    def __init__(self, parsers: Sequence[ParserDeFrame[Any]] | None = None) -> None:
        self._parsers = tuple(parsers) if parsers is not None else _PARSERS_PADRAO
        self._contador_frames = 0

    def rotear(self, frame: FrameBruto) -> list[FrameProcessado]:
        """Converte um `FrameBruto` em zero ou mais `FrameProcessado`."""
        self._contador_frames += 1
        logger.debug(
            "Frame #%d recebido (tag=%s, tem_erros=%s, tem_valores=%s, chaves=%s)",
            self._contador_frames,
            frame.tag,
            bool(frame.erros),
            bool(frame.valores),
            list(frame.valores.keys()) if frame.valores else [],
        )

        if frame.erros:
            return [_dto_de_erro(origem, corpo) for origem, corpo in frame.erros.items()]

        if not frame.valores:
            return []

        # Tenta cada parser. Um mesmo frame pode conter campos de mais de um
        # domínio ao mesmo tempo (ex.: dados de escola e de conectividade
        # misturados) — por isso TODOS os parsers são testados, não só o
        # primeiro que reconhecer. Parar no primeiro match descartava
        # silenciosamente os campos dos outros domínios presentes no frame.
        resultados: list[FrameProcessado] = []

        for parser in self._parsers:
            nome_parser = parser.__class__.__name__
            try:
                if not parser.reconhece(frame.valores):
                    continue
            except Exception:
                logger.exception("Parser %s falhou ao tentar reconhecer o frame.", nome_parser)
                continue

            try:
                resultados.append(parser.parse(frame.valores))
            except Exception:
                logger.exception("Parser %s reconheceu o frame, mas falhou ao convertê-lo.", nome_parser)

        if not resultados:
            logger.debug(
                "Nenhum parser reconheceu o frame #%d. Chaves: %s",
                self._contador_frames,
                list(frame.valores.keys()),
            )

        return resultados


def _dto_de_erro(origem: str, corpo: object) -> ErroFrameDTO:
    mensagem = corpo.get("message") if isinstance(corpo, dict) else None
    return ErroFrameDTO(
        origem=origem,
        mensagem=mensagem if isinstance(mensagem, str) else str(corpo),
    )
