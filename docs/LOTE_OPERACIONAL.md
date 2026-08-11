# Processamento em lote (CLI)

Consulta uma lista de INEPs lida de um CSV, em uma única sessão de
navegador, salvando cada resultado imediatamente — com suporte a
retomar um lote interrompido a qualquer momento.

## Executando

```bash
conectividade-lote
# equivalente a:
python -m conectividade.lote.infraestrutura.cli
```

O comando:

1. Lê `src/conectividade/dados/ineps.csv` (coluna obrigatória: `inep`).
2. Lê `src/conectividade/dados/resultados/resultado_lote.csv` para
   descobrir quais INEPs já têm resultado salvo (checkpoint).
3. Se não sobrar nenhum INEP pendente, informa e encerra **sem abrir o
   navegador**.
4. Caso contrário, abre o Chrome e pede para você confirmar que o
   ambiente está pronto (proxy configurado, se necessário):

   ```
   Chrome aberto.
   Configure o proxy manualmente (caso necessário).
   Pressione ENTER após configurar o proxy/carregar a página...
   ```

5. Navega até o portal (se ainda não estiver nele) e aguarda o Shiny
   conectar.
6. Consulta cada INEP pendente, em sequência, imprimindo o resultado e
   salvando a linha correspondente no CSV **imediatamente** após cada
   consulta.
7. Ao final (ou se você interromper com `Ctrl+C`), imprime um resumo
   com a contagem por status.

## Arquivos

### Entrada — `dados/ineps.csv`

```csv
inep
12345678
87654321
```

- Precisa ter uma coluna chamada `inep`.
- Linhas com `.0` no final (comum em exportações do Excel) são
  normalizadas automaticamente (`12345678.0` → `12345678`).
- Linhas com valor não numérico são ignoradas, com aviso no log.

### Saída / checkpoint — `dados/resultados/resultado_lote.csv`

```csv
inep,status,tempo,nome_escola,uf_escola,dependencia_escola,estudantes_escola,estudantes_escola_maior_turno,vel_adequada,status_medidor,vel_download,vel_upload,latencia,jitter,perda_pacote,nro_medicoes,medicoes_escola,max_95_down
12345678,sucesso,34.12,Escola Exemplo,Município: X - Y,Gestão: Municipal,Número de estudantes: 120,...,...
```

- Cada linha é gravada (e sincronizada em disco) assim que aquele INEP
  termina de ser processado — interromper o processo a qualquer
  momento não perde progresso.
- **Qualquer INEP com uma linha neste arquivo é considerado
  "processado"** ao rodar o comando de novo — inclusive os que deram
  `timeout` ou `erro`. Para reprocessar uma falha, apague a linha
  correspondente deste CSV antes de rodar de novo.
- Os valores de cada campo (exceto `inep`, `status`, `tempo`) são o
  texto tal como veio do portal, sem conversão de tipo — o mesmo
  formato que o portal usa para exibir, incluindo prefixos como
  `"Município: "` ou `"Gestão: "`. Isso preserva compatibilidade com
  arquivos de resultado já existentes; se for necessário separar
  esses campos em tipos nativos (ex.: `município` e `uf` como colunas
  separadas), isso deve ser feito como uma etapa de pós-processamento
  do CSV, não mudando este contrato.

### Status possíveis

| `status` | Significado |
|---|---|
| `sucesso` | Dados capturados e estabilizados. |
| `nao_encontrado` | O portal informou que o INEP não é reconhecido. |
| `timeout` | O portal não respondeu (ou não estabilizou) em até 60s. |
| `erro` | Falha inesperada durante a consulta (ex.: o Shiny não confirmou o recebimento do INEP em 10s). |

## O algoritmo de estabilização

Este é o núcleo do processamento em lote, e a razão de ele existir como
um mecanismo separado da consulta individual (ver
[`ARQUITETURA.md`](ARQUITETURA.md#por-que-dois-mecanismos-de-consulta)).

**O problema**: para não pagar o custo de abrir um navegador por INEP,
o lote reaproveita a mesma página do Shiny para centenas de consultas
seguidas. Isso significa que, ao enviar um novo INEP, os dados
exibidos na tela ainda são os do INEP anterior por um tempo — e o
Shiny não avisa "prontinho, atualizei tudo". É preciso *inferir* isso
observando o estado reativo.

**A estratégia** (`lote/infraestrutura/shiny_polling/deteccao_estabilizacao.py`):
a cada `intervalo_polling` segundos (padrão 0.5s), lê-se
`Shiny.shinyapp.$values` e calcula-se uma **assinatura** (tupla com
todos os campos relevantes). A resposta só é aceita como definitiva
quando a assinatura:

1. É diferente da assinatura da consulta **anterior** bem-sucedida no
   mesmo lote (prova de que os dados realmente mudaram); **e**
2. Permanece **idêntica** por `tempo_estabilizacao` segundos seguidos
   (padrão 5s) — prova de que o Shiny já terminou de recalcular todos
   os componentes reativos, não só o primeiro a responder.

```
Envia INEP
    │
    ▼
INEP não encontrado? ──sim──► status = nao_encontrado
    │ não
    ▼
Shiny já registrou este INEP como input atual? ──não──► aguarda e tenta de novo
    │ sim
    ▼
Lê Shiny.$values
    │
    ▼
Tem nome de escola (dado válido)? ──não──► "dados anteriores foram limpos", aguarda
    │ sim
    ▼
Assinatura == assinatura da consulta anterior? ──sim──► "dados antigos ainda na tela", aguarda
    │ não
    ▼
Assinatura mudou desde a última leitura? ──sim──► reinicia o cronômetro de estabilidade, aguarda
    │ não (está parado)
    ▼
Parado há >= tempo_estabilizacao? ──não──► aguarda
    │ sim
    ▼
status = sucesso
```

Se nenhum destes critérios for satisfeito em até `timeout_resposta`
segundos (padrão 60s), o resultado é `timeout`.

Os limiares de tempo estão centralizados em
`lote/infraestrutura/config.py` (`LimitesDeTempo`), com os mesmos
valores já validados em produção:

| Limite | Padrão | Papel |
|---|---|---|
| `timeout_conexao_shiny` | 90s | Espera inicial pela conexão de WebSocket do Shiny. |
| `timeout_confirmacao_inep` | 10s | Espera pela confirmação de que o Shiny recebeu o INEP enviado. |
| `timeout_resposta` | 60s | Espera total pela estabilização da resposta a um INEP. |
| `intervalo_polling` | 0.5s | Intervalo entre leituras sucessivas de `$values`. |
| `tempo_estabilizacao` | 5s | Tempo mínimo sem mudança para considerar os dados definitivos. |

## Testando sem navegador

`ProcessarLoteUseCase` (a orquestração do lote) não depende de
Playwright — só das portas `RepositorioIneps`, `RepositorioResultadosLote`
e `ConsultorEscolaPortal` (`lote/aplicacao/portas.py`). Isso permite
testar toda a lógica de checkpoint, propagação de assinatura entre
consultas e contagem do resumo final com objetos de teste simples, sem
tocar em CSV nem em navegador:

```python
class ConsultorFalso:
    def consultar(self, inep, assinatura_anterior):
        return ResultadoConsultaLote(inep=inep, status=StatusConsultaLote.SUCESSO, ...)

use_case = ProcessarLoteUseCase(
    repositorio_ineps=repo_ineps_falso,
    repositorio_resultados=repo_resultados_falso,
)
plano = use_case.planejar()
resumo = use_case.executar(plano, consultor=ConsultorFalso())
```
