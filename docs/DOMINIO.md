# Domínio

## Linguagem ubíqua

| Termo | Significado |
|---|---|
| **INEP** | Código de identificação de uma escola no censo escolar. Identidade usada em toda consulta ao portal. |
| **Portal** | O site *Conectividade na Educação*, uma aplicação Shiny (R). |
| **Lote** | O conjunto de INEPs de um CSV a processar em uma execução. |
| **Estabilização** | O momento em que os dados exibidos pelo portal param de mudar entre leituras sucessivas de `Shiny.shinyapp.$values`, indicando que a resposta para o INEP atual está completa. |
| **Checkpoint** | O conjunto de INEPs que já têm um resultado salvo, usado para retomar um lote interrompido sem repetir trabalho. |
| **Partição** | Uma fatia do lote atribuída a uma instância específica, quando o processamento é dividido entre várias instâncias em paralelo. |

Este projeto modela um problema específico: não "o que é uma escola",
mas "como saber que a resposta do portal para o INEP atual já chegou
por completo e é confiável".

## `DadosEscolaLote` (`dominio/dados_escola.py`)

Value Object com os campos que o CSV de resultados grava — nome da
escola, localização, métricas de conectividade, provedores etc. —
**mantidos como texto cru** (só sem o wrapper `{"html": ...}` do
Shiny), no mesmo formato que o portal usa para exibir (incluindo
prefixos como `"Município: "` ou `"Gestão: "`). Não há parsing para
tipos nativos: isso preserva o contrato do arquivo `resultado_lote.csv`
já em uso.

Expõe as regras de negócio usadas pelo algoritmo de estabilização:

- `possui_nome_valido`: indica que já existe um nome de escola não
  vazio — sinal de que os dados chegaram (mesmo que ainda instáveis).
- `assinatura`: tupla com todos os campos, na ordem canônica — dois
  snapshots são "os mesmos dados" quando têm assinaturas iguais.
- `possui_provedor_informado`: indica que o portal retornou pelo menos
  um dos dois campos de provedor (`provedoresSIMET_regiao` ou
  `provedor_do_estabelecimento`) — nem toda escola tem provedor
  cadastrado, e a ausência não é tratada como erro.

## `ResultadoConsultaLote` e `StatusConsultaLote` (`dominio/resultado_consulta.py`)

```
StatusConsultaLote = SUCESSO | NAO_ENCONTRADO | TIMEOUT | ERRO
```

- `SUCESSO`: os dados estabilizaram e foram capturados.
- `NAO_ENCONTRADO`: o portal informou que o INEP não é reconhecido.
- `TIMEOUT`: o portal não respondeu (ou não estabilizou) dentro do
  tempo limite.
- `ERRO`: qualquer falha inesperada durante a consulta (ex.: o Shiny
  não confirmou o recebimento do INEP enviado).

## `PlanoExecucaoLote` (`dominio/plano_execucao.py`)

Resultado de cruzar a lista completa de INEPs (já filtrada pela
partição desta instância, se houver) com o checkpoint. Um INEP é
considerado "já processado" **independentemente do status** salvo
anteriormente — inclusive `timeout` ou `erro`. Reexecutar o lote não
tenta essas falhas de novo automaticamente; para reprocessar, é
preciso remover as linhas correspondentes do CSV de resultados.

## `ResumoLote` (`dominio/resumo_lote.py`)

Contagem de resultados por status ao final de uma execução — usado só
para o relatório final impresso ao operador.
