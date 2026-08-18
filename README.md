# Conectividade na Educação — Consulta em Lote por INEP

Consulta em massa o portal **Conectividade na Educação**
(conectividadenaeducacao.nic.br) a partir de uma lista de códigos INEP
em CSV, automatizando a navegação, o envio de cada INEP e a leitura dos
dados retornados (dados cadastrais da escola, métricas de
conectividade e provedores). Cada resultado é salvo imediatamente, com
retomada automática em caso de interrupção, e o processamento pode ser
dividido entre várias instâncias rodando em paralelo para acelerar
lotes grandes.

## Instalação

Requer Python 3.11+.

```bash
pip install -e .
python -m playwright install chromium
```

## Uso rápido

```bash
# 1. Preencha src/conectividade/dados/ineps.csv com uma coluna "inep"
# 2. Rode:
conectividade-lote
# (equivalente a: python -m conectividade.infraestrutura.cli)
```

O comando abre o Chrome, pede para você confirmar que o proxy/página
está pronta, e então consulta cada INEP pendente, salvando cada
resultado imediatamente em `dados/resultados/resultado_lote.csv`. Se
for interrompido, rodar de novo retoma de onde parou.

## Rodando em paralelo

Para lotes grandes, divida o trabalho entre várias instâncias:

```bash
# terminal 1
conectividade-lote --particoes 2 --indice-particao 0

# terminal 2
conectividade-lote --particoes 2 --indice-particao 1
```

E combine os resultados no final:

```bash
conectividade-lote-merge \
    --saida dados/resultados/resultado_lote.csv \
    dados/resultados/resultado_lote_parte0.csv \
    dados/resultados/resultado_lote_parte1.csv
```

Veja [`docs/LOTE_OPERACIONAL.md`](docs/LOTE_OPERACIONAL.md) para o
formato dos arquivos, o algoritmo de estabilização e o detalhe do
particionamento.

## Documentação

- [`docs/ARQUITETURA.md`](docs/ARQUITETURA.md) — visão geral das
  camadas (Clean Architecture / DDD) e a regra de dependência.
- [`docs/DOMINIO.md`](docs/DOMINIO.md) — linguagem ubíqua, entidades e
  invariantes de negócio.
- [`docs/LOTE_OPERACIONAL.md`](docs/LOTE_OPERACIONAL.md) — o CLI de
  processamento em lote: formato dos CSVs, algoritmo de estabilização,
  execução em paralelo.

## Desenvolvimento

```bash
pip install -e ".[dev]"
mypy src
```

## Status

✅ Processamento em lote via CSV, com retomada automática
✅ Execução paralela (particionamento intercalado + merge de resultados)
🚧 Cobertura de testes automatizados
🚧 Observabilidade operacional (métricas/alertas de execução do lote)

## Licença

Projeto interno, desenvolvido por Luiz Paulo, destinado ao
processamento automatizado de dados da plataforma Conectividade
Educação.
