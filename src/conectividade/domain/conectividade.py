"""
Value Object: métricas de qualidade da conexão de internet de uma escola.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Conectividade:
    """Métricas de qualidade de conexão medidas na escola."""

    quantidade_medicoes: int
    perda_pacote_percentual: float
    jitter_ms: float
    latencia_ms: float
    velocidade_upload_mbps: float
    velocidade_download_mbps: float
    plano_estimado_mbps: float
    medidor_ativo: bool
