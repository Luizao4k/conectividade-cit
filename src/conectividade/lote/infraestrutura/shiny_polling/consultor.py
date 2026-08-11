"""Implementação de `ConsultorEscolaPortal` usando a estratégia de polling."""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

from conectividade.lote.dominio.dados_escola import DadosEscolaLote
from conectividade.lote.dominio.resultado_consulta import ResultadoConsultaLote
from conectividade.lote.infraestrutura.config import LimitesDeTempo
from conectividade.lote.infraestrutura.shiny_polling.deteccao_estabilizacao import (
    DetectorEstabilizacao,
)
from conectividade.lote.infraestrutura.shiny_polling.envio_inep import EnviadorInep
from conectividade.lote.infraestrutura.shiny_polling.leitura_reativa import LeitorValoresReativos

if TYPE_CHECKING:
    from playwright.sync_api import Page


class ConsultorEscolaPortalPolling:
    """
    Consulta um INEP no portal enviando o valor ao input do Shiny e
    esperando os dados reativos (`Shiny.shinyapp.$values`) estabilizarem.

    Implementa a porta `ConsultorEscolaPortal` (ver `lote/aplicacao/portas.py`).
    Uma instância opera sobre uma única página já conectada ao portal —
    reaproveitada para todo o lote, sem recarregar a cada INEP.
    """

    def __init__(self, page: Page, *, limites: LimitesDeTempo) -> None:
        leitor = LeitorValoresReativos(page)

        self._enviador = EnviadorInep(page, leitor, timeout_segundos=limites.timeout_confirmacao_inep)
        self._detector = DetectorEstabilizacao(
            page,
            leitor,
            timeout_resposta=limites.timeout_resposta,
            intervalo_polling=limites.intervalo_polling,
            tempo_estabilizacao=limites.tempo_estabilizacao,
        )

    def consultar(
        self,
        inep: str,
        assinatura_anterior: tuple[object, ...] | None,
    ) -> ResultadoConsultaLote:
        """Envia o INEP e aguarda a resposta estabilizar, devolvendo o resultado tipado."""
        inicio = time.monotonic()

        self._enviador.enviar(inep)
        status, valores = self._detector.aguardar(inep, assinatura_anterior)

        tempo_segundos = time.monotonic() - inicio

        return ResultadoConsultaLote(
            inep=inep,
            status=status,
            dados=DadosEscolaLote.a_partir_de_valores_brutos(valores),
            tempo_segundos=tempo_segundos,
        )
