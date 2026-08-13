# Conectividade na Educação — Cliente de Consulta por INEP

Consulta o portal **Conectividade na Educação** (conectividadenaeducacao.nic.br)
por código INEP, automatizando a navegação, o envio do INEP e a leitura
dos dados retornados pelo portal (dados cadastrais da escola e métricas
de conectividade).

O projeto expõe **duas formas de consulta**, pensadas para dois usos
diferentes — ver [`docs/ARQUITETURA.md`](docs/ARQUITETURA.md) para o
racional de manter as duas:

| | Biblioteca (consulta individual) | CLI de lote (`conectividade-lote`) |
|---|---|---|
| Uso típico | Integrar a consulta em outro sistema Python | Rodar uma consulta em massa a partir de um CSV, com acompanhamento manual |
| Mecanismo | Escuta os frames de WebSocket do Shiny | Faz *polling* do estado reativo do Shiny |
| Entrada | Um INEP (ou lista) passado em código | Um CSV (`dados/ineps.csv`) |
| Saída | Objetos de domínio (`ConsultaEscola`) | CSV de resultados, com retomada automática |
| Documentação | [`docs/CONSULTA_INDIVIDUAL.md`](docs/CONSULTA_INDIVIDUAL.md) | [`docs/LOTE_OPERACIONAL.md`](docs/LOTE_OPERACIONAL.md) |

## Instalação

Requer Python 3.11+.

```bash
pip install -e .
python -m playwright install chromium
```

## Uso rápido — biblioteca

```python
from conectividade import criar_consulta_service

consulta_service = criar_consulta_service(page)  # `page` = playwright.sync_api.Page

resultado = consulta_service.consultar("15001156")
resultados = consulta_service.consultar_lote(["15001156", "11000222"])
```

Veja [`docs/CONSULTA_INDIVIDUAL.md`](docs/CONSULTA_INDIVIDUAL.md) para
como abrir o navegador, tratamento de erros e o formato dos objetos
retornados.

## Uso rápido — CLI de lote

```bash
# 1. Preencha src/conectividade/dados/ineps.csv com uma coluna "inep"
# 2. Rode:
conectividade-lote
# (equivalente a: python -m conectividade.lote.infraestrutura.cli)
```

O comando abre o Chrome, pede para você confirmar que o proxy/página
está pronta, e então consulta cada INEP pendente, salvando cada
resultado imediatamente em `dados/resultados/resultado_lote.csv`. Se
for interrompido, rodar de novo retoma de onde parou. Veja
[`docs/LOTE_OPERACIONAL.md`](docs/LOTE_OPERACIONAL.md) para o formato
dos arquivos e o algoritmo de estabilização.

## Documentação

- [`docs/ARQUITETURA.md`](docs/ARQUITETURA.md) — visão geral das
  camadas (Clean Architecture / DDD), regra de dependência e por que
  existem dois mecanismos de consulta.
- [`docs/DOMINIO.md`](docs/DOMINIO.md) — linguagem ubíqua, entidades e
  invariantes de negócio.
- [`docs/CONSULTA_INDIVIDUAL.md`](docs/CONSULTA_INDIVIDUAL.md) — a API
  pública da biblioteca (protocolo Shiny via WebSocket).
- [`docs/LOTE_OPERACIONAL.md`](docs/LOTE_OPERACIONAL.md) — o CLI de
  processamento em lote (polling + CSV).



## Status

✅ Consulta individual via WebSocket (biblioteca)
✅ Processamento em lote via CSV, com retomada automática (CLI)
🚧 Cobertura de testes automatizados
🚧 Observabilidade operacional (métricas/alertas de execução do lote)

## Licença

Projeto interno, desenvolvido por Luiz Paulo, destinado ao
processamento automatizado de dados da plataforma Conectividade
Educação.
