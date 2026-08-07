"""
Entidade de domínio: dados cadastrais e de identificação de uma escola.

Este tipo não sabe nada sobre Shiny, WebSocket ou os textos brutos do
portal (ex.: "Município: Porto Velho - Rondonia"). A tradução desse
formato para estes campos tipados acontece na camada de infraestrutura
(ver `infrastructure/shiny/mapeadores.py`), que funciona como uma camada
anticorrupção entre o formato do portal e o domínio.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Escola:
    """Dados cadastrais de uma escola, já em tipos nativos do Python."""

    nome: str
    municipio: str
    uf: str
    dependencia_administrativa: str
    quantidade_estudantes: int
    ano_censo: int
    quantidade_medicoes: int
    percentual_95_download: float
    velocidade_adequada_mbps: float
