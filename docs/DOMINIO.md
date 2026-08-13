# Domínio

## Linguagem ubíqua

| Termo | Significado |
|---|---|
| **INEP** | Código de identificação de uma escola no censo escolar. Identidade usada em toda consulta ao portal. |
| **Portal** | O site *Conectividade na Educação*, uma aplicação Shiny (R). |
| **Frame** | Uma mensagem individual recebida pelo WebSocket do Shiny. |
| **Consulta** | O processo de enviar um INEP ao portal e coletar os dados retornados. |
| **Estabilização** | (só no contexto de lote) O momento em que os dados exibidos pelo portal param de mudar entre leituras sucessivas, indicando que a resposta para o INEP atual está completa. |
| **Checkpoint** | (só no contexto de lote) O conjunto de INEPs que já têm um resultado salvo, usado para retomar um lote interrompido sem repetir trabalho. |

## Bounded context: Consulta individual

### Aggregate root — `ConsultaEscola` (`domain/consulta_escola.py`)

Representa o resultado completo de uma consulta a um INEP. É o único
tipo que o restante da aplicação deveria manipular — nunca `Escola`,
`Conectividade` ou `Provedores` isoladamente.

```
ConsultaEscola
├── inep: str
├── escola: Escola                        (obrigatório)
├── conectividade: Conectividade | None    (ausente se a escola não tem medição)
├── provedores: Provedores | None
└── erros: tuple[ErroConsulta, ...]        (erros que o próprio portal reportou)
```

Invariante exposta: `possui_medidor_ativo` só é `True` quando existe
`conectividade` **e** `conectividade.medidor_ativo` é `True` — ver
código para o motivo (escola pode ter conectividade reportada com
medidor desligado).

### Entidade — `Escola` (`domain/escola.py`)

Dados cadastrais já tipados (nome, município, UF, dependência
administrativa, quantidade de estudantes, ano do censo, etc.) — o
portal envia esses campos como texto livre (ex.:
`"Município: Porto Velho - Rondonia"`); a tradução para campos tipados
acontece em `infrastructure/shiny/mapeadores.py`, que funciona como uma
**camada anticorrupção** entre o formato do portal e o domínio. O
domínio nunca vê o texto bruto.

### Value Objects

- **`Conectividade`** (`domain/conectividade.py`): métricas de
  qualidade de conexão (perda de pacote, jitter, latência, velocidades
  de upload/download, plano estimado, se o medidor está ativo).
- **`Provedores`** (`domain/provedores.py`): provedores atuando no
  estabelecimento e na região onde ele fica.
- **`ErroConsulta`** (`domain/erro_consulta.py`): um erro que o próprio
  portal reportou para um componente específico durante a consulta.

### Exceções de domínio (`domain/exceptions.py`)

| Exceção | Quando é levantada |
|---|---|
| `EscolaNaoEncontradaError` | Nenhuma escola encontrada para o INEP. |
| `RespostaIncompletaError` | O portal não enviou os frames esperados dentro do timeout. |
| `AplicacaoShinyEncerradaError` | O servidor encerrou a aplicação Shiny no meio da consulta (crash, `code != 1000`). |

Todas herdam de `ConsultaEscolaError`.

## Bounded context: Processamento em lote

Este contexto modela um problema diferente: não "o que é uma escola",
mas "como saber que a resposta para o INEP atual — e não sobras do
INEP anterior na mesma sessão de navegador — já chegou por completo".

### `DadosEscolaLote` (`lote/dominio/dados_escola.py`)

Value Object com os mesmos campos que o CSV de resultados grava,
**mantidos como texto cru** (só sem o wrapper `{"html": ...}` do
Shiny) — ao contrário de `Escola`, não há parsing para tipos nativos
aqui, porque isso mudaria o contrato do arquivo `resultado_lote.csv`
já em uso.

Expõe duas regras de negócio usadas pelo algoritmo de estabilização:

- `possui_nome_valido`: indica que já existe um nome de escola não
  vazio — sinal de que os dados chegaram (mesmo que ainda instáveis).
- `assinatura`: tupla com todos os campos, na ordem canônica — dois
  snapshots são "os mesmos dados" quando têm assinaturas iguais.
- `possui_provedor_informado`: indica que o portal retornou pelo menos
  um dos dois campos de provedor (`provedoresSIMET_regiao` ou
  `provedor_do_estabelecimento`) — nem toda escola tem provedor
  cadastrado, e a ausência não é tratada como erro.

### `ResultadoConsultaLote` e `StatusConsultaLote` (`lote/dominio/resultado_consulta.py`)

```
StatusConsultaLote = SUCESSO | NAO_ENCONTRADO | TIMEOUT | ERRO
```

- `SUCESSO`: os dados estabilizaram e foram capturados.
- `NAO_ENCONTRADO`: o portal informou que o INEP não é reconhecido.
- `TIMEOUT`: o portal não respondeu (ou não estabilizou) dentro do
  tempo limite.
- `ERRO`: qualquer falha inesperada durante a consulta (ex.: o Shiny
  não confirmou o recebimento do INEP enviado).

### `PlanoExecucaoLote` (`lote/dominio/plano_execucao.py`)

Resultado de cruzar a lista completa de INEPs com o checkpoint. Um
INEP é considerado "já processado" **independentemente do status**
salvo anteriormente — inclusive `timeout` ou `erro`. Reexecutar o lote
não tenta essas falhas de novo automaticamente; para reprocessar, é
preciso remover as linhas correspondentes do CSV de resultados.

### `ResumoLote` (`lote/dominio/resumo_lote.py`)

Contagem de resultados por status ao final de uma execução — usado só
para o relatório final impresso ao operador.
