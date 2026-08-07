# src/conectividade/infrastructure/shiny/frame_router.py

from __future__ import annotations

from collections.abc import Sequence
from typing import Any
import json
import logging
from datetime import datetime

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
    """
    Roteia frames brutos para o parser especializado correspondente.
    """

    def __init__(
        self, 
        parsers: Sequence[ParserDeFrame[Any]] | None = None,
        debug: bool = True
    ) -> None:
        self._parsers = tuple(parsers) if parsers is not None else _PARSERS_PADRAO
        self._debug = debug
        self._contador_frames = 0
        
    def rotear(self, frame: FrameBruto) -> list[FrameProcessado]:
        """Converte um `FrameBruto` em zero ou mais `FrameProcessado`."""
        self._contador_frames += 1
        
        if self._debug:
            print(f"\n{'='*60}")
            print(f"[ROTEADOR] Frame #{self._contador_frames} - {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
            print(f"  Tag: {frame.tag}")
            print(f"  Tem erros: {bool(frame.erros)}")
            print(f"  Tem valores: {bool(frame.valores)}")
            
            if frame.erros:
                print(f"  Erros: {json.dumps(frame.erros, ensure_ascii=False)[:200]}")
            
            if frame.valores:
                print(f"  Chaves nos valores: {list(frame.valores.keys())}")
                # Mostra estrutura resumida
                for key, value in list(frame.valores.items())[:3]:
                    if isinstance(value, dict):
                        print(f"    {key}: dict com {len(value)} chaves - {list(value.keys())}")
                    elif isinstance(value, list):
                        print(f"    {key}: list com {len(value)} itens")
                        if value and isinstance(value[0], dict):
                            print(f"      Primeiro item: {list(value[0].keys())}")
                    else:
                        print(f"    {key}: {type(value).__name__} = {str(value)[:50]}")

        # Verifica erros
        if frame.erros:
            if self._debug:
                print(f"  [DECISÃO] Frame com erros -> criar DTO de erro")
            return [
                _dto_de_erro(origem, corpo) for origem, corpo in frame.erros.items()
            ]

        # Sem valores, ignora
        if not frame.valores:
            if self._debug:
                print(f"  [DECISÃO] Frame sem valores -> ignorar")
            return []

        # Tenta cada parser
        for i, parser in enumerate(self._parsers):
            parser_nome = parser.__class__.__name__
            
            if self._debug:
                print(f"  [TESTANDO] Parser {i+1}/{len(self._parsers)}: {parser_nome}")
            
            try:
                if parser.reconhece(frame.valores):

                    if self._debug:
                        print(f"  [MATCH] {parser_nome} reconheceu o frame!")
                    
                    resultado = parser.parse(frame.valores)
                    
                    if self._debug:
                        print(f"  [RESULTADO] {type(resultado).__name__}: {resultado}")
                    
                    return [resultado]
                else:
                    if self._debug:
                        print(f"  [NO MATCH] {parser_nome} NÃO reconheceu")
                        
            except Exception as e:
                if self._debug:
                    print(f"  [ERRO] {parser_nome} falhou: {e}")
                    import traceback
                    traceback.print_exc()

        # Nenhum parser reconheceu
        if self._debug:
            print(f"  [DECISÃO] Nenhum parser reconheceu -> ignorar")
            
            # Mostra estrutura detalhada para diagnóstico
            print(f"\n  [DEBUG] Estrutura completa do frame:")
            print(f"  {json.dumps(frame.valores, ensure_ascii=False, indent=2)[:1000]}")
            
            # Verifica se tem campos que deveriam ser reconhecidos
            campos_importantes = ['inep', 'escola', 'data', 'result', 'values']
            encontrados = [c for c in campos_importantes if c in frame.valores]
            if encontrados:
                print(f"  [AVISO] Campos importantes encontrados mas não reconhecidos: {encontrados}")
                print(f"  Verifique se os parsers estão configurados para esses campos")

        return []


def _dto_de_erro(origem: str, corpo: object) -> ErroFrameDTO:
    mensagem = corpo.get("message") if isinstance(corpo, dict) else None
    return ErroFrameDTO(
        origem=origem,
        mensagem=mensagem if isinstance(mensagem, str) else str(corpo),
    )
