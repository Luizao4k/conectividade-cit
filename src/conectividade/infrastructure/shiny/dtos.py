"""
DTOs (Data Transfer Objects): representam, de forma tipada, o conteúdo de
`values` de cada tipo de frame relevante — ainda no formato bruto do
portal (strings com prefixos como "Município: ..." ou números em formato
brasileiro "39,9"). A tradução para os tipos de domínio (Escola,
Conectividade, Provedores) acontece em `mapeadores.py`.

Manter esses DTOs separados dos tipos de domínio é o que permite que o
formato do Shiny mude (ex.: o portal trocar o texto de "Gestão: Municipal"
por outra coisa) sem que `Escola`, `Conectividade` e o restante da
aplicação percebam — só o mapeador correspondente muda.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EscolaFrameDTO:
    """Espelha o frame com os dados cadastrais da escola (ex.: tag "C2" na consulta principal)."""

    nome_escola: str | None = None
    uf_escola: str | None = None
    dependencia_escola: str | None = None
    estudantes_escola: str | None = None
    medicoes_escola: str | None = None
    max_95_down: str | None = None
    vel_adequada: str | None = None


@dataclass(frozen=True, slots=True)
class ConectividadeFrameDTO:
    """Espelha o frame com as métricas de qualidade da conexão."""

    nro_medicoes: str | None = None
    perda_pacote: str | None = None
    jitter: str | None = None
    latencia: str | None = None
    vel_upload: str | None = None
    vel_download: str | None = None
    plano_estimado: str | None = None
    status_medidor: str | None = None


@dataclass(frozen=True, slots=True)
class ProvedoresFrameDTO:
    """Espelha o frame com os provedores da escola e da região."""

    provedores_regiao: str | None = None
    provedor_estabelecimento: str | None = None


@dataclass(frozen=True, slots=True)
class ErroFrameDTO:
    """Representa um erro reportado pelo portal para um componente específico."""

    origem: str 
    mensagem: str


FrameProcessado = EscolaFrameDTO | ConectividadeFrameDTO | ProvedoresFrameDTO | ErroFrameDTO
"""União de todos os DTOs que o Frame Router pode produzir a partir de um frame."""
