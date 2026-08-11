"""
Ponto de entrada do processamento em lote (composition root).

Equivalente ao antigo `python -m conectividade.main`, agora como:

    python -m conectividade.lote.infraestrutura.cli

Esta é a única camada que conhece TODAS as peças concretas (Browser,
Playwright, CSV) e as conecta: nenhuma outra camada do `lote` sabe da
existência umas das outras além das portas em `aplicacao/portas.py`.
"""
from __future__ import annotations

import logging

from conectividade.infrastructure.browser import Browser
from conectividade.lote.aplicacao.processar_lote_use_case import ProcessarLoteUseCase
from conectividade.lote.infraestrutura import config
from conectividade.lote.infraestrutura.csv_ineps_repositorio import RepositorioIneposCsv
from conectividade.lote.infraestrutura.csv_resultados_repositorio import (
    RepositorioResultadosLoteCsv,
)
from conectividade.lote.infraestrutura.notificacao_console import NotificadorConsoleLote
from conectividade.lote.infraestrutura.shiny_polling.aguardador_conexao import (
    AguardadorConexaoShiny,
)
from conectividade.lote.infraestrutura.shiny_polling.consultor import (
    ConsultorEscolaPortalPolling,
)

_TIMEOUT_NAVEGACAO_MS = 120_000
_DOMINIO_PORTAL = "conectividadenaeducacao.nic.br"


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    print("=== CONSULTA DE INEPS EM LOTE ===")

    repositorio_ineps = RepositorioIneposCsv(config.ARQUIVO_INEPS_PADRAO)
    repositorio_resultados = RepositorioResultadosLoteCsv(config.ARQUIVO_RESULTADOS_PADRAO)
    notificador = NotificadorConsoleLote(config.ARQUIVO_RESULTADOS_PADRAO)

    use_case = ProcessarLoteUseCase(
        repositorio_ineps=repositorio_ineps,
        repositorio_resultados=repositorio_resultados,
    )

    plano = use_case.planejar()

    print(f"Total de INEPs no CSV: {plano.total_ineps}")
    if plano.ja_processados:
        print(f"INEPs já processados: {plano.ja_processados}")
        print(f"INEPs restantes: {len(plano.pendentes)}")
    else:
        print("Nenhum resultado anterior encontrado.")

    if not plano.ha_trabalho_pendente:
        print("\n[OK] Todos os INEPs já foram processados.")
        print(f"Resultados: {config.ARQUIVO_RESULTADOS_PADRAO}")
        return

    with Browser(url_portal=config.URL_PORTAL, headless=False) as browser:
        print("\nChrome aberto.")
        print("Configure o proxy manualmente (caso necessário).")
        input("Pressione ENTER após configurar o proxy/carregar a página...")

        page = browser.page
        print(f"\nURL atual: {page.url}")

        if _DOMINIO_PORTAL not in page.url:
            print("\nAbrindo portal...")
            page.goto(
                config.URL_PORTAL,
                wait_until="domcontentloaded",
                timeout=_TIMEOUT_NAVEGACAO_MS,
            )

        aguardador = AguardadorConexaoShiny(
            page,
            timeout_segundos=config.LIMITES_PADRAO.timeout_conexao_shiny,
            intervalo_polling=config.LIMITES_PADRAO.intervalo_polling,
        )
        aguardador.aguardar()

        consultor = ConsultorEscolaPortalPolling(page, limites=config.LIMITES_PADRAO)

        resumo = use_case.executar(plano, consultor=consultor, notificador=notificador)

    notificador.resumo_final(resumo)


if __name__ == "__main__":
    main()
