"""Resumo agregado de uma execução do processamento em lote."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from conectividade.lote.dominio.resultado_consulta import ResultadoConsultaLote, StatusConsultaLote


@dataclass(frozen=True, slots=True)
class ResumoLote:
    """Contagem de resultados por status ao final de uma execução do lote."""

    total_processado: int
    sucessos: int
    nao_encontrados: int
    timeouts: int
    erros: int

    @classmethod
    def a_partir_de(cls, resultados: Sequence[ResultadoConsultaLote]) -> "ResumoLote":
        return cls(
            total_processado=len(resultados),
            sucessos=sum(r.status is StatusConsultaLote.SUCESSO for r in resultados),
            nao_encontrados=sum(r.status is StatusConsultaLote.NAO_ENCONTRADO for r in resultados),
            timeouts=sum(r.status is StatusConsultaLote.TIMEOUT for r in resultados),
            erros=sum(r.status is StatusConsultaLote.ERRO for r in resultados),
        )
