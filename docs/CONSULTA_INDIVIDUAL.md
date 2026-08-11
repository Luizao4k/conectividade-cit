# Consulta individual (API pública da biblioteca)

Mecanismo de consulta pensado para ser **importado por outro sistema
Python** — não é um script interativo. Consulta um ou mais INEPs
interceptando os frames de WebSocket do Shiny em tempo real.

## Uso

```python
from conectividade import criar_consulta_service
from conectividade.infrastructure.browser import Browser

URL_PORTAL = "https://conectividadenaeducacao.nic.br/#sua-escola"

with Browser(url_portal=URL_PORTAL, headless=False) as browser:
    # Se seu ambiente precisar de um passo manual antes de navegar
    # (ex.: configurar um proxy corporativo), faça-o aqui, e então:
    browser.abrir_portal()

    consulta_service = criar_consulta_service(browser.page)

    resultado = consulta_service.consultar("15001156")
    print(resultado.escola.nome, resultado.escola.municipio)

    resultados = consulta_service.consultar_lote(["15001156", "11000222"])
```

> Para consultar **muitos** INEPs de um CSV, com acompanhamento manual
> e retomada automática em caso de interrupção, use o
> [CLI de lote](LOTE_OPERACIONAL.md) em vez desta API — ele resolve um
> problema de estabilização que esta API não precisa resolver (ver
> [`ARQUITETURA.md`](ARQUITETURA.md#por-que-dois-mecanismos-de-consulta)).

## `ConsultaEscolaService`

- **`consultar(inep: str) -> ConsultaEscola`** — consulta um único
  INEP. Valida o formato do INEP (8 dígitos) antes de qualquer chamada
  de rede.
- **`consultar_lote(ineps: Sequence[str]) -> list[ConsultaEscola]`** —
  consulta vários INEPs em sequência, reaproveitando a mesma página.

### Erros possíveis

| Exceção | Causa |
|---|---|
| `ValueError` | INEP com formato inválido (não são 8 dígitos numéricos). |
| `EscolaNaoEncontradaError` | O portal não retornou dados para o INEP. |
| `RespostaIncompletaError` | O portal não completou a resposta dentro do timeout (`timeout_segundos`, padrão 120s — configurável em `criar_consulta_service`). |
| `AplicacaoShinyEncerradaError` | O servidor encerrou a aplicação Shiny no meio da consulta (ex.: crash da aplicação). |

Todas (exceto `ValueError`) herdam de `ConsultaEscolaError`, exportada
em `conectividade`.

## `ConsultaEscola` (o que você recebe de volta)

```python
resultado.inep                          # str
resultado.escola.nome                   # str
resultado.escola.municipio              # str
resultado.escola.uf                     # str
resultado.escola.dependencia_administrativa
resultado.escola.quantidade_estudantes  # int
resultado.escola.ano_censo              # int

resultado.conectividade                 # Conectividade | None
resultado.conectividade.velocidade_download_mbps
resultado.conectividade.latencia_ms
resultado.possui_medidor_ativo          # bool

resultado.provedores                    # Provedores | None
resultado.provedores.provedor_estabelecimento  # tuple[str, ...]

resultado.erros                         # tuple[ErroConsulta, ...]
```

Ver [`docs/DOMINIO.md`](DOMINIO.md) para a descrição completa de cada
tipo.

## Como funciona por baixo dos panos

1. `Browser` abre uma sessão persistente do Chrome (perfil salvo em
   `./perfil_chrome` por padrão).
2. `criar_consulta_service` monta um `ShinyClient` sobre a página e o
   conecta a um `ConsultaEscolaService` através do gateway
   `PortalConectividadeGateway`.
3. Ao chamar `.consultar(inep)`:
   - `ShinyClient` aguarda o WebSocket do Shiny conectar;
   - envia o INEP para o input `#inep_plano`;
   - escuta todos os frames recebidos via `WebSocketListener`;
   - cada frame passa por `RoteadorDeFrames`, que testa **todos** os
     parsers (`EscolaFrameParser`, `ConectividadeFrameParser`,
     `ProvedoresFrameParser`) — um mesmo frame pode conter campos de
     mais de um domínio;
   - os DTOs resultantes são acumulados em `AgregadorDeConsulta` até
     ficar `completo` (todos os dados obrigatórios chegaram) ou até
     estourar o timeout;
   - `mapeadores.py` converte os DTOs (texto bruto do portal) nas
     entidades de domínio tipadas.
4. O roteamento é feito pelo **conteúdo** do frame (conjunto de chaves
   dentro de `values`), não pela tag sequencial do Shiny (`C2`, `C9`,
   ...) — essas tags são um contador interno que não é garantido
   estável entre consultas.

## Depuração

Todos os componentes desta camada usam o módulo `logging` padrão do
Python (nenhum `print` de depuração ficou no código de produção). Para
ver o passo a passo de uma consulta:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```
