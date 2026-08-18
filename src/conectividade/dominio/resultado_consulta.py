"""
Resultado de uma consulta individual dentro do processamento em lote.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from conectividade.dominio.dados_escola import DadosEscolaLote


class StatusConsultaLote(str, Enum):
    """
    Desfecho possível de uma consulta em lote.

    Os valores (strings) são exatamente os que já eram gravados na coluna
    `status` do CSV de resultados — preservados para não quebrar
    compatibilidade com `resultado_lote.csv` existentes.
    """

    SUCESSO = "sucesso"
    NAO_ENCONTRADO = "nao_encontrado"
    TIMEOUT = "timeout"
    ERRO = "erro"


@dataclass(frozen=True, slots=True)
class ResultadoConsultaLote:
    """Resultado de uma consulta a um único INEP dentro de um lote."""

    inep: str
    status: StatusConsultaLote
    dados: DadosEscolaLote = field(default_factory=DadosEscolaLote)
    tempo_segundos: float = 0.0

    @property
    def sucesso(self) -> bool:
        return self.status is StatusConsultaLote.SUCESSO

    @property
    def assinatura(self) -> tuple[object, ...]:
        """Assinatura dos dados desta consulta (delegado a `DadosEscolaLote`)."""
        return self.dados.assinatura
