"""
Configuração do processamento em lote: URL do portal, caminhos padrão de
dados e limites de tempo do algoritmo de espera/estabilização.

Os valores abaixo são exatamente os que já estavam fixos no antigo
`main.py` — mantidos como constantes nomeadas (em vez de "números
mágicos" espalhados pelo código) para facilitar ajuste futuro sem caçar
onde cada um é usado.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

URL_PORTAL: str = "https://conectividadenaeducacao.nic.br/#sua-escola"

# Diretório de dados do pacote: `src/conectividade/dados/`.
_BASE_DIR = Path(__file__).resolve().parents[2]
DIRETORIO_DADOS: Path = _BASE_DIR / "dados"
ARQUIVO_INEPS_PADRAO: Path = DIRETORIO_DADOS / "ineps.csv"
DIRETORIO_RESULTADOS: Path = DIRETORIO_DADOS / "resultados"
ARQUIVO_RESULTADOS_PADRAO: Path = DIRETORIO_RESULTADOS / "resultado_lote.csv"


@dataclass(frozen=True, slots=True)
class LimitesDeTempo:
    """Limites de tempo (em segundos) do algoritmo de espera e estabilização."""

    timeout_conexao_shiny: float = 90.0
    """Tempo máximo aguardando o Shiny estabelecer conexão de WebSocket."""

    timeout_confirmacao_inep: float = 10.0
    """Tempo máximo aguardando o Shiny confirmar o recebimento do INEP enviado."""

    timeout_resposta: float = 60.0
    """Tempo máximo aguardando a resposta completa do portal para um INEP."""

    intervalo_polling: float = 0.5
    """Intervalo entre verificações sucessivas durante as esperas acima."""

    tempo_estabilizacao: float = 5.0
    """
    Tempo que os dados retornados precisam permanecer inalterados
    (mesma assinatura) antes de serem considerados estáveis e aceitos
    como resultado final.
    """


LIMITES_PADRAO = LimitesDeTempo()
