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
inep,status,tempo,nome_escola,uf_escola,dependencia_escola,estudantes_escola,estudantes_escola_maior_turno,vel_adequada,status_medidor,vel_download,vel_upload,latencia,jitter,perda_pacote,nro_medicoes,medicoes_escola,max_95_down,provedoresSIMET_regiao,provedor_do_estabelecimento
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
- **Exceção**: `provedoresSIMET_regiao` e `provedor_do_estabelecimento`
  passam por uma limpeza leve do HTML do portal — o rótulo estático
  ("Provedor(es) da Escola", "Provedor(es) na região") é descartado e
  só os nomes dos provedores ficam no CSV, sem tags HTML. Nem toda
  escola tem provedor cadastrado; nesse caso a coluna fica vazia (não é
  um erro).

### Por que cada consulta recarrega a página

O portal não limpa alguns dos seus valores reativos entre consultas
que reaproveitam a mesma sessão — o caso mais visível é
`provedor_do_estabelecimento`: quando uma escola não tem provedor
cadastrado, o Shiny simplesmente não recalcula aquele valor, e ele
permanece na tela com o valor da consulta anterior. Sem tratamento,
isso faria uma escola sem provedor aparecer no CSV com o provedor de
outra escola — um dado errado, não apenas incompleto.

Em vez de tentar detectar caso a caso quais campos foram realmente
atualizados (uma solução por heurística, sujeita a falsos positivos e
negativos), `ConsultorEscolaPortalPolling` recarrega a página do
portal antes de cada INEP (`page.reload()` + reconfirmação de que o
Shiny reconectou). Cada consulta começa de uma sessão genuinamente
vazia — não existe "dado de consulta anterior" para vazar, em nenhum
campo, não só nos de provedor. O algoritmo de estabilização trata toda
consulta como se fosse a primeira do lote.

**O custo dessa correção é tempo**: recarregar a página e esperar o
WebSocket do Shiny reconectar acontece **antes** da espera normal de
estabilização (5s), então o tempo médio por INEP aumenta em relação a
reaproveitar a mesma sessão para o lote inteiro. Em compensação, todo
campo vazio no resultado é genuinamente vazio — nunca uma sobra de
outra escola.

> **Nota de migração**: se você já tinha um `resultado_lote.csv` gerado
> antes das colunas `provedoresSIMET_regiao`/`provedor_do_estabelecimento`
> existirem, o cabeçalho desse arquivo **não** será reescrito
> automaticamente (o código só escreve cabeçalho para arquivo novo). Ou
> seja: linhas gravadas a partir de agora terão 2 colunas a mais do que
> o cabeçalho já escrito, desalinhando o CSV. Antes de rodar o lote de
> novo sobre um arquivo antigo, renomeie-o (ex.:
> `resultado_lote.csv` → `resultado_lote.antigo.csv`) para começar um
> arquivo novo com o cabeçalho atualizado, ou adicione manualmente as
> duas colunas vazias ao cabeçalho existente.

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

**O problema**: mesmo com a página recarregada a cada INEP (ver seção
acima), os componentes reativos do Shiny não chegam todos de uma vez —
cada um (nome da escola, velocidade, provedores...) é recalculado e
enviado ao navegador de forma independente e assíncrona. O Shiny não
avisa "prontinho, todos os componentes terminaram" — é preciso
*inferir* isso observando o estado reativo parar de mudar.

**A estratégia** (`lote/infraestrutura/shiny_polling/deteccao_estabilizacao.py`):
a cada `intervalo_polling` segundos (padrão 0.5s), lê-se
`Shiny.shinyapp.$values` e calcula-se uma **assinatura** (tupla com
todos os campos relevantes). A resposta só é aceita como definitiva
quando a assinatura permanece **idêntica** por `tempo_estabilizacao`
segundos seguidos (padrão 5s) — prova de que o Shiny já terminou de
recalcular todos os componentes reativos, não só o primeiro a
responder.

> O detector também sabe lidar com o caso de uma sessão **não**
> recarregada entre consultas (comparando com a assinatura da consulta
> anterior) — hoje esse ramo nunca é exercitado, porque
> `ConsultorEscolaPortalPolling` sempre recarrega antes de consultar,
> mas a lógica continua correta caso uma futura implementação volte a
> reaproveitar a sessão.

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
Tem nome de escola (dado válido)? ──não──► "dados ainda carregando", aguarda
    │ sim
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

## Rodando em paralelo

Com lotes grandes (ex.: ~1000 INEPs a ~20s cada ≈ 5,5h em sequência),
dá para dividir o trabalho entre várias instâncias do CLI rodando ao
mesmo tempo, cada uma com sua própria sessão de Chrome. Não há nenhuma
mudança no algoritmo de estabilização em si — cada instância consulta
seu próprio recorte de INEPs de forma totalmente independente das
demais.

```bash
# terminal 1
conectividade-lote --particoes 2 --indice-particao 0

# terminal 2
conectividade-lote --particoes 2 --indice-particao 1
```

Com essas duas flags:

- `--arquivo-ineps` pode continuar apontando para o **mesmo**
  `ineps.csv` nas duas instâncias — cada uma filtra sua própria fatia
  automaticamente, não é preciso pré-dividir o arquivo.
- `--arquivo-resultados` e `--perfil-chrome` são derivados
  automaticamente por partição (`resultado_lote_parte0.csv`,
  `resultado_lote_parte1.csv`, `perfil_chrome_parte0`,
  `perfil_chrome_parte1`, ...) — cada instância **precisa** de um
  perfil de Chrome próprio (dois processos não podem compartilhar o
  mesmo diretório de perfil ao mesmo tempo) e de um arquivo de saída
  próprio (para não haver duas instâncias escrevendo no mesmo CSV ao
  mesmo tempo, o que arriscaria corromper linhas). Se quiser escolher
  os caminhos manualmente, use `--arquivo-resultados` e
  `--perfil-chrome` explicitamente.
- Sem `--particoes` (ou com `--particoes 1`), o comportamento é
  idêntico ao de antes — nenhuma mudança para quem usa uma única
  instância.

### Particionamento intercalado (round-robin)

`RepositorioIneposParticionado` divide a lista pelo índice de cada
INEP na ordem em que aparece no CSV: o INEP de índice `i` cabe à
instância onde `i % particoes == indice_particao`. Ou seja, com 2
partições, a instância 0 pega os INEPs 1º, 3º, 5º... e a instância 1
pega o 2º, 4º, 6º... Isso tende a distribuir melhor eventuais trechos
mais lentos do arquivo entre as instâncias do que dividir em blocos
contínuos (ex.: primeira metade / segunda metade).

Cada instância mantém seu próprio checkpoint, no seu próprio arquivo
de resultado — interromper uma delas não afeta a outra, e rodar de
novo só aquela instância retoma de onde parou, normalmente.

### Combinando os resultados no final

Depois que as instâncias terminarem, combine os CSVs de cada uma em um
único arquivo com `conectividade-lote-merge`:

```bash
conectividade-lote-merge \
    --saida dados/resultados/resultado_lote.csv \
    dados/resultados/resultado_lote_parte0.csv \
    dados/resultados/resultado_lote_parte1.csv
```

Como o particionamento é intercalado e disjunto, não há risco de
duplicar INEPs — o utilitário só valida que todos os arquivos de
origem têm exatamente as mesmas colunas antes de combinar (evita um
CSV desalinhado se um dos arquivos vier de uma versão diferente do
sistema).

### O que considerar antes de escalar além de 2 instâncias

- **Recursos da máquina**: cada Chrome headful consome uma quantidade
  razoável de RAM. Se a máquina ficar sob carga pesada, o próprio
  tempo de estabilização (que é de relógio, não adaptativo) pode
  piorar, aumentando a taxa de `timeout`.
- **Proxy/rede compartilhada**: se houver algum limite por IP ou por
  sessão no portal ou no proxy corporativo, isso só aparece na prática
  — vale observar a taxa de `erro`/`timeout` com 2 instâncias antes de
  ir para mais.
- **Confirmação manual**: o `Pressione ENTER...` continua sendo por
  instância — com mais instâncias, mais janelas para confirmar
  manualmente no início.
