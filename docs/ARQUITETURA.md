# Arquitetura

## Visão geral

O projeto segue **Clean Architecture**, organizada em torno
de dois *bounded contexts* (DDD) que compartilham a mesma base de
código, mas resolvem problemas diferentes:

```
src/conectividade/
├── domain/            ┐
├── application/        │  Bounded context: CONSULTA INDIVIDUAL
├── gateway/             │  (API pública da biblioteca)
├── infrastructure/     ┘
│   ├── browser/         (compartilhado pelos dois contextos)
│   ├── websocket/        \
│   └── shiny/             > só usados pela consulta individual
├── factory.py             /
├── __init__.py           (API pública: criar_consulta_service)
│
└── lote/               ┐
    ├── dominio/          │  Bounded context: PROCESSAMENTO EM LOTE
    ├── aplicacao/         │  (CLI operacional via CSV)
    └── infraestrutura/  ┘
```

### Por que dois mecanismos de consulta?

Historicamente o projeto tinha duas implementações concorrentes: uma
biblioteca orientada a eventos (intercepta frames de WebSocket) e um
script de lote que fazia *polling* direto do estado reativo do Shiny
(`Shiny.shinyapp.$values`). São estratégias genuinamente diferentes
para o mesmo problema, com trade-offs distintos:

| | WebSocket (`infrastructure/shiny`) | Polling (`lote/infraestrutura/shiny_polling`) |
|---|---|---|
| Reage a | Cada frame recebido | Snapshot do estado a cada N ms |
| Overhead | Baixo (orientado a evento) | Mais chamadas `page.evaluate` |
| Robustez a mudança de tags internas do Shiny | Alta (roteia pelo conteúdo) | Alta (não depende de tags) |
| Detecta "dados antigos ainda na tela" entre consultas sucessivas | Não precisava até hoje (uma consulta por sessão) | Sim — é o problema central do lote, que reaproveita a mesma página para todos os INEPs |
| Operação | Programática (biblioteca) | Interativa (operador acompanha no terminal) |

O processamento em lote precisa reaproveitar a mesma sessão de Chrome
para centenas de INEPs seguidos (abrir um navegador por INEP seria
proibitivamente lento), o que introduz um problema que a consulta
individual não tem: como saber que os dados na tela já são os do INEP
**atual**, e não sobras do INEP anterior? O algoritmo de estabilização
em `lote/infraestrutura/shiny_polling/deteccao_estabilizacao.py` existe
justamente para isso — ver
[`docs/LOTE_OPERACIONAL.md`](LOTE_OPERACIONAL.md).

Em vez de forçar os dois problemas a compartilhar uma única
implementação (o que arriscaria comportamento sutilmente diferente do
já validado em produção), o refactor manteve os dois mecanismos como
bounded contexts separados, cada um com seu próprio domínio,
aplicação e infraestrutura — compartilhando apenas o que é
genuinamente comum (a classe `Browser`, que só abre/fecha o navegador
e não sabe nada de Shiny).

## Camadas (regra de dependência)

Em cada bounded context, a dependência aponta sempre para dentro:

```
infraestrutura  →  aplicação  →  domínio
      ↑                              
      └── nunca o contrário: domínio e aplicação não importam infraestrutura
```

- **Domínio** (`domain/` e `lote/dominio/`): entidades, value objects e
  regras de negócio puras. Sem I/O, sem Playwright, sem CSV. Pode ser
  testado sem navegador.
- **Aplicação** (`application/` e `lote/aplicacao/`): casos de uso que
  orquestram o domínio através de **portas** (`Protocol`s) — interfaces
  que a infraestrutura implementa. A aplicação não sabe se a porta é
  implementada com Playwright, um mock de teste, ou outra coisa.
- **Infraestrutura** (`infrastructure/` e `lote/infraestrutura/`):
  implementações concretas das portas — Playwright, WebSocket, CSV,
  console. É a única camada que conhece bibliotecas externas.
- **Gateway** (`gateway/`, só no contexto de consulta individual): o
  adapter que implementa a porta de domínio `ConsultaEscolaGateway`
  usando `ShinyClient`. Existe como camada própria (em vez de dentro de
  `infrastructure/`) para deixar explícito que é *a* porta de saída do
  domínio — não apenas mais um detalhe de infraestrutura.

### Portas e inversão de dependência

Cada caso de uso depende de `Protocol`s definidos por ele mesmo (ex.:
`lote/aplicacao/portas.py`), nunca de uma classe concreta de
infraestrutura. Isso é o que permite testar `ProcessarLoteUseCase` (ou
`ConsultaEscolaService`) inteiramente sem abrir um navegador: basta
passar um objeto qualquer com os métodos certos.

```
ProcessarLoteUseCase
      depende de
        ├── RepositorioIneps (Protocol)        ← implementado por RepositorioIneposCsv
        ├── RepositorioResultadosLote (Protocol) ← implementado por RepositorioResultadosLoteCsv
        └── ConsultorEscolaPortal (Protocol)     ← implementado por ConsultorEscolaPortalPolling
```

## Composition root

Cada bounded context tem um único ponto onde as peças concretas de
infraestrutura são instanciadas e conectadas às portas:

- Consulta individual: `factory.py` (`criar_consulta_service`).
- Lote: `lote/infraestrutura/cli.py` (`main`).

## Fluxo de dados — consulta individual

```
Navegador Chrome
      │
      ▼
Aplicação Shiny (WebSocket)
      │
      ▼
WebSocketListener               (infrastructure/websocket)
      │
      ▼
ShinyClient                     (infrastructure/shiny)
      │  decodifica envelope, normaliza HTML
      ▼
RoteadorDeFrames                (infrastructure/shiny/frame_router.py)
      │
      ├──► EscolaFrameParser ─────► EscolaFrameDTO
      ├──► ConectividadeFrameParser ► ConectividadeFrameDTO
      └──► ProvedoresFrameParser ──► ProvedoresFrameDTO
                  │
                  ▼
        AgregadorDeConsulta        (acumula até `completo`)
                  │
                  ▼
           mapeadores.py            (DTO → entidades de domínio)
                  │
                  ▼
            ConsultaEscola          (entidade de domínio)
```

Cada frame é testado contra **todos** os parsers (não só o primeiro que
reconhecer), porque um mesmo frame pode conter campos de mais de um
domínio simultaneamente — parar no primeiro match descartaria
silenciosamente os demais campos.

## Fluxo de dados — processamento em lote

```
RepositorioIneposCsv.carregar()          → lista de INEPs
RepositorioResultadosLoteCsv.carregar_processados() → checkpoint
                  │
                  ▼
        ProcessarLoteUseCase.planejar()  → PlanoExecucaoLote (pendentes)
                  │
    (para cada INEP pendente, em sequência, na mesma página)
                  ▼
        EnviadorInep.enviar(inep)         → preenche o input do Shiny
                  │
                  ▼
        DetectorEstabilizacao.aguardar()  → espera os $values estabilizarem
                  │
                  ▼
        DadosEscolaLote.a_partir_de_valores_brutos(...)
                  │
                  ▼
        RepositorioResultadosLoteCsv.salvar(...)  → grava a linha no CSV
```

Veja [`docs/LOTE_OPERACIONAL.md`](LOTE_OPERACIONAL.md) para o detalhe
do algoritmo de estabilização.

## Testando sem navegador

Como domínio e aplicação não dependem de Playwright, é possível
exercitar toda a lógica de negócio com objetos de teste simples
(`Protocol`s não exigem herança — qualquer objeto com os métodos certos
serve):

```python
class ConsultorFalso:
    def consultar(self, inep, assinatura_anterior):
        return ResultadoConsultaLote(inep=inep, status=StatusConsultaLote.SUCESSO, ...)

resumo = use_case.executar(plano, consultor=ConsultorFalso(), notificador=None)
```
