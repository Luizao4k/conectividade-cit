"""
Combina os CSVs de resultado gerados por múltiplas instâncias do lote
(uma por partição) em um único arquivo.

Uso:

    conectividade-lote-merge --saida dados/resultados/resultado_lote.csv \\
        dados/resultados/resultado_lote_parte0.csv \\
        dados/resultados/resultado_lote_parte1.csv

Não deduplica linhas: assume que os arquivos de origem vêm de partições
disjuntas (ver `RepositorioIneposParticionado`) — se dois arquivos
tiverem uma linha para o mesmo INEP, ambas são mantidas no arquivo
final, e cabe a quem for consumir o resultado decidir o que fazer com
isso (normalmente sinal de que as partições não eram realmente
disjuntas, o que vale investigar).
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path


def combinar(arquivos_origem: list[Path], arquivo_saida: Path) -> int:
    """
    Concatena os CSVs de `arquivos_origem` em `arquivo_saida`.

    Valida que todos os arquivos de origem compartilham exatamente o
    mesmo cabeçalho antes de combinar — cabeçalhos diferentes geralmente
    indicam que os arquivos vêm de versões diferentes do sistema (ex.:
    um já tem a coluna de provedores e outro não), o que produziria um
    CSV combinado com colunas desalinhadas.

    Retorna o total de linhas de dados escritas (sem contar o cabeçalho).

    Raises:
        ValueError: Se nenhum arquivo de origem for informado, ou se os
            cabeçalhos dos arquivos de origem não forem idênticos.
    """
    if not arquivos_origem:
        raise ValueError("Nenhum arquivo de origem informado.")

    cabecalho_esperado: list[str] | None = None
    linhas: list[dict[str, str]] = []

    for arquivo in arquivos_origem:
        with arquivo.open("r", encoding="utf-8-sig", newline="") as arquivo_csv:
            leitor = csv.DictReader(arquivo_csv)

            if cabecalho_esperado is None:
                cabecalho_esperado = leitor.fieldnames if leitor.fieldnames else []
            elif list(leitor.fieldnames or []) != cabecalho_esperado:
                raise ValueError(
                    f"{arquivo} tem colunas diferentes dos demais arquivos de origem "
                    "— confirme que todos vêm da mesma versão do sistema antes de combinar."
                )

            linhas.extend(leitor)

    assert cabecalho_esperado is not None  # garantido pelo `if not arquivos_origem` acima

    arquivo_saida.parent.mkdir(parents=True, exist_ok=True)

    with arquivo_saida.open("w", encoding="utf-8-sig", newline="") as arquivo_csv:
        escritor = csv.DictWriter(arquivo_csv, fieldnames=cabecalho_esperado)
        escritor.writeheader()
        escritor.writerows(linhas)

    return len(linhas)


def _parse_argumentos(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="conectividade-lote-merge",
        description="Combina os CSVs de resultado de múltiplas partições do lote em um único arquivo.",
    )
    parser.add_argument(
        "origens",
        nargs="+",
        type=Path,
        help="Arquivos CSV de resultado a combinar (ex.: resultado_lote_parte0.csv resultado_lote_parte1.csv).",
    )
    parser.add_argument(
        "--saida",
        type=Path,
        required=True,
        help="Arquivo CSV final combinado.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_argumentos(argv)
    total = combinar(args.origens, args.saida)
    print(f"{total} linhas combinadas em: {args.saida}")


if __name__ == "__main__":
    main()
