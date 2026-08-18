"""
Ponto de entrada do processamento em lote (composition root).

Equivalente ao antigo `python -m conectividade.main`, agora como:

    python -m conectividade.infraestrutura.cli
    # ou, após `pip install -e .`:
    conectividade-lote

Esta é a única camada que conhece TODAS as peças concretas (Browser,
Playwright, CSV) e as conecta: nenhuma outra camada do `lote` sabe da
existência umas das outras além das portas em `aplicacao/portas.py`.

Rodando várias instâncias em paralelo (ver
`docs/LOTE_OPERACIONAL.md#rodando-em-paralelo`):

    conectividade-lote --particoes 2 --indice-particao 0   # terminal 1
    conectividade-lote --particoes 2 --indice-particao 1   # terminal 2
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

from conectividade.infraestrutura.browser import Browser
from conectividade.aplicacao.portas import RepositorioIneps
from conectividade.aplicacao.processar_lote_use_case import ProcessarLoteUseCase
from conectividade.infraestrutura import config
from conectividade.infraestrutura.csv_ineps_repositorio import RepositorioIneposCsv
from conectividade.infraestrutura.csv_resultados_repositorio import (
    RepositorioResultadosLoteCsv,
)
from conectividade.infraestrutura.notificacao_console import NotificadorConsoleLote
from conectividade.infraestrutura.particionamento import RepositorioIneposParticionado
from conectividade.infraestrutura.shiny_polling.aguardador_conexao import (
    AguardadorConexaoShiny,
)
from conectividade.infraestrutura.shiny_polling.consultor import (
    ConsultorEscolaPortalPolling,
)

_TIMEOUT_NAVEGACAO_MS = 120_000
_DOMINIO_PORTAL = "conectividadenaeducacao.nic.br"


def _parse_argumentos(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="conectividade-lote",
        description="Consulta em lote de INEPs no portal Conectividade na Educação.",
    )
    parser.add_argument(
        "--particoes",
        type=int,
        default=1,
        metavar="N",
        help="Número total de instâncias rodando em paralelo (padrão: 1, sem particionamento).",
    )
    parser.add_argument(
        "--indice-particao",
        type=int,
        default=0,
        metavar="I",
        help="Índice desta instância entre as instâncias, começando em 0 (padrão: 0).",
    )
    parser.add_argument(
        "--arquivo-ineps",
        type=Path,
        default=config.ARQUIVO_INEPS_PADRAO,
        help="CSV de entrada com a coluna 'inep' (padrão: %(default)s). "
        "Compartilhado entre todas as instâncias — cada uma filtra sua própria fatia.",
    )
    parser.add_argument(
        "--arquivo-resultados",
        type=Path,
        default=None,
        help="CSV de saída desta instância. Padrão: derivado automaticamente da "
        "partição (resultado_lote.csv sem particionamento, resultado_lote_parteN.csv com).",
    )
    parser.add_argument(
        "--perfil-chrome",
        type=Path,
        default=None,
        help="Diretório do perfil do Chrome desta instância. Padrão: derivado "
        "automaticamente da partição — cada instância PRECISA de um perfil próprio.",
    )

    args = parser.parse_args(argv)

    if args.particoes < 1:
        parser.error("--particoes precisa ser >= 1.")

    if not (0 <= args.indice_particao < args.particoes):
        parser.error(f"--indice-particao precisa estar entre 0 e {args.particoes - 1}.")

    return args


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    args = _parse_argumentos(argv)

    arquivo_resultados = args.arquivo_resultados or config.arquivo_resultados_para_particao(
        args.indice_particao, args.particoes
    )
    perfil_chrome = args.perfil_chrome or config.perfil_chrome_para_particao(
        args.indice_particao, args.particoes
    )

    print("=== CONSULTA DE INEPS EM LOTE ===")
    if args.particoes > 1:
        print(f"Partição {args.indice_particao + 1}/{args.particoes} (intercalada)")
    print(f"INEPs: {args.arquivo_ineps}")
    print(f"Resultados desta instância: {arquivo_resultados}")
    print(f"Perfil do Chrome: {perfil_chrome}")

    repositorio_ineps: RepositorioIneps = RepositorioIneposCsv(args.arquivo_ineps)
    if args.particoes > 1:
        repositorio_ineps = RepositorioIneposParticionado(
            repositorio_ineps,
            total_particoes=args.particoes,
            indice_particao=args.indice_particao,
        )

    repositorio_resultados = RepositorioResultadosLoteCsv(arquivo_resultados)
    notificador = NotificadorConsoleLote(arquivo_resultados)

    use_case = ProcessarLoteUseCase(
        repositorio_ineps=repositorio_ineps,
        repositorio_resultados=repositorio_resultados,
    )

    plano = use_case.planejar()

    print(f"\nTotal de INEPs nesta instância: {plano.total_ineps}")
    if plano.ja_processados:
        print(f"INEPs já processados: {plano.ja_processados}")
        print(f"INEPs restantes: {len(plano.pendentes)}")
    else:
        print("Nenhum resultado anterior encontrado (nesta instância).")

    if not plano.ha_trabalho_pendente:
        print("\n[OK] Todos os INEPs desta instância já foram processados.")
        print(f"Resultados: {arquivo_resultados}")
        return

    with Browser(headless=False, user_data_dir=perfil_chrome) as browser:
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
