"""Implementação de `ConsultorEscolaPortal` usando a estratégia de polling."""
from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from conectividade.dominio.dados_escola import DadosEscolaLote
from conectividade.dominio.resultado_consulta import ResultadoConsultaLote
from conectividade.infraestrutura.config import LimitesDeTempo
from conectividade.infraestrutura.shiny_polling.aguardador_conexao import (
    AguardadorConexaoShiny,
)
from conectividade.infraestrutura.shiny_polling.deteccao_estabilizacao import (
    DetectorEstabilizacao,
)
from conectividade.infraestrutura.shiny_polling.envio_inep import EnviadorInep
from conectividade.infraestrutura.shiny_polling.leitura_reativa import LeitorValoresReativos

if TYPE_CHECKING:
    from playwright.sync_api import Page

logger = logging.getLogger(__name__)

_TIMEOUT_RECARREGAR_MS = 60_000


class ConsultorEscolaPortalPolling:
    """
    Consulta um INEP no portal enviando o valor ao input do Shiny e
    esperando os dados reativos (`Shiny.shinyapp.$values`) estabilizarem.

    Implementa a porta `ConsultorEscolaPortal` (ver `aplicacao/portas.py`).

    Recarrega a página antes de cada consulta, para que cada INEP comece
    de uma sessão Shiny genuinamente vazia. Isso existe porque o portal
    não limpa todos os seus valores reativos entre consultas — sem
    recarregar, um campo que o Shiny não recalcula para o INEP atual
    (ex.: provedor, quando a escola não tem nenhum cadastrado) permanece
    com o valor da consulta anterior na mesma sessão, sendo salvo como
    se fosse informação real desta escola. Recarregar troca esse
    problema por um tempo maior por consulta (ver
    `docs/LOTE_OPERACIONAL.md`), mas garante que todo campo vazio é
    genuinamente vazio, nunca uma sobra de uma consulta anterior.
    """

    def __init__(self, page: Page, *, limites: LimitesDeTempo) -> None:
        self._page = page

        leitor = LeitorValoresReativos(page)

        self._aguardador_conexao = AguardadorConexaoShiny(
            page,
            timeout_segundos=limites.timeout_conexao_shiny,
            intervalo_polling=limites.intervalo_polling,
        )
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
        """
        Recarrega a página, envia o INEP e aguarda a resposta estabilizar.

        `assinatura_anterior` é ignorado deliberadamente: como a página é
        recarregada antes de cada consulta, nunca existe "dado de uma
        consulta anterior" nesta sessão para comparar — toda consulta é
        tratada como a primeira.
        """
        inicio = time.monotonic()

        self._recarregar()

        self._enviador.enviar(inep)
        status, valores = self._detector.aguardar(inep, None)

        tempo_segundos = time.monotonic() - inicio

        return ResultadoConsultaLote(
            inep=inep,
            status=status,
            dados=DadosEscolaLote.a_partir_de_valores_brutos(valores),
            tempo_segundos=tempo_segundos,
        )

    def _recarregar(self) -> None:
        logger.info("Recarregando a página para iniciar uma sessão Shiny nova...")

        self._page.reload(wait_until="domcontentloaded", timeout=_TIMEOUT_RECARREGAR_MS)
        self._aguardador_conexao.aguardar()

