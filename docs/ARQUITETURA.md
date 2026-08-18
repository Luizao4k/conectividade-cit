# Arquitetura

## Visão geral

O projeto segue **Clean Architecture** (regra de dependência: camadas
externas dependem das internas, nunca o contrário) em torno de um único
propósito: consultar o portal Conectividade na Educação em lote, a
partir de um CSV de INEPs, com suporte a retomada e a execução
paralela.

```
src/conectividade/
├── dominio/            entidades e value objects (DadosEscolaLote,
│                        ResultadoConsultaLote, StatusConsultaLote, ...)
├── aplicacao/           caso de uso (ProcessarLoteUseCase) + portas (Protocol)
└── infraestrutura/      implementações concretas das portas:
    ├── browser.py                     abre/fecha uma sessão persistente do Chrome
    ├── csv_ineps_repositorio.py
    ├── csv_resultados_repositorio.py
    ├── particionamento.py
    ├── merge_resultados.py
    ├── cli.py                         composition root
    └── shiny_polling/                 consulta ao portal por polling
```

Não existe API pública própria neste pacote — o ponto de entrada é
sempre o CLI (`conectividade-lote`, definido em `infraestrutura/cli.py`).

## Por que polling, e não escutar o WebSocket do Shiny

O portal é uma aplicação Shiny (R): os dados de cada INEP chegam ao
navegador via WebSocket, em frames que o servidor envia conforme cada
componente reativo termina de calcular. Em vez de interceptar esses
frames (o que exige decodificar o protocolo interno do Shiny e rotear
cada frame para o parser certo), a estratégia adotada aqui é mais
direta: ler `Shiny.shinyapp.$values` periodicamente (`page.evaluate`)
até os dados pararem de mudar — ver
[`docs/LOTE_OPERACIONAL.md`](LOTE_OPERACIONAL.md#o-algoritmo-de-estabilização)
para o algoritmo completo.

Essa abordagem é operacionalmente mais simples de rodar e de depurar
(o operador acompanha o progresso no terminal, em uma sessão de Chrome
visível), o que importa para um processo em lote de longa duração que
alguém acompanha manualmente.

## Camadas (regra de dependência)

A dependência aponta sempre para dentro:

```
infraestrutura  →  aplicação  →  domínio
      ↑
      └── nunca o contrário: domínio e aplicação não importam infraestrutura
```

- **Domínio** (`dominio/`): entidades, value objects e regras de
  negócio puras. Sem I/O, sem Playwright, sem CSV. Pode ser testado
  sem navegador.
- **Aplicação** (`aplicacao/`): o caso de uso
  (`ProcessarLoteUseCase`) que orquestra o domínio através de
  **portas** (`Protocol`s definidos em `aplicacao/portas.py`) —
  interfaces que a infraestrutura implementa. A aplicação não sabe se
  uma porta é implementada com Playwright, CSV, ou um objeto de teste.
- **Infraestrutura** (`infraestrutura/`): implementações
  concretas das portas — Playwright, CSV, console. É a única camada
  que conhece bibliotecas externas.

### Portas e inversão de dependência

`ProcessarLoteUseCase` depende de `Protocol`s, nunca de uma classe
concreta:

```
ProcessarLoteUseCase
      depende de
        ├── RepositorioIneps (Protocol)          ← implementado por RepositorioIneposCsv
        ├── RepositorioResultadosLote (Protocol) ← implementado por RepositorioResultadosLoteCsv
        └── ConsultorEscolaPortal (Protocol)     ← implementado por ConsultorEscolaPortalPolling
```

Isso é o que permite testar o caso de uso inteiro sem abrir um
navegador: basta passar um objeto qualquer com os métodos certos (ver
["Testando sem navegador"](#testando-sem-navegador) abaixo).

## Composition root

`infraestrutura/cli.py` (`main`) é o único ponto do sistema onde
as peças concretas são instanciadas e conectadas às portas — nenhuma
outra parte do código faz isso.

Quando o lote roda particionado entre várias instâncias (ver
[`docs/LOTE_OPERACIONAL.md#rodando-em-paralelo`](LOTE_OPERACIONAL.md#rodando-em-paralelo)),
`RepositorioIneposParticionado` (`infraestrutura/particionamento.py`)
entra como um *decorator* sobre `RepositorioIneps` — implementa a mesma
porta que envolve, então `ProcessarLoteUseCase` não sabe (nem precisa
saber) que existe particionamento. É o composition root quem decide se
o repositório de INEPs é usado puro ou decorado.

## Fluxo de dados

```
RepositorioIneposCsv.carregar()                       → lista de INEPs
  (decorado por RepositorioIneposParticionado, se houver particionamento)
RepositorioResultadosLoteCsv.carregar_processados()   → checkpoint
                  │
                  ▼
        ProcessarLoteUseCase.planejar()  → PlanoExecucaoLote (pendentes)
                  │
    (para cada INEP pendente, em sequência, na mesma sessão de Chrome)
                  ▼
        ConsultorEscolaPortalPolling._recarregar()  → page.reload() + reconfirma conexão do Shiny
                  │
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
do algoritmo de estabilização, o motivo do recarregamento por consulta,
e o particionamento entre instâncias paralelas.

## Testando sem navegador

Como domínio e aplicação não dependem de Playwright, é possível
exercitar toda a lógica de negócio (checkpoint, propagação de estado
entre consultas, contagem do resumo final) com objetos de teste
simples (`Protocol`s não exigem herança — qualquer objeto com os
métodos certos serve):

```python
class ConsultorFalso:
    def consultar(self, inep, assinatura_anterior):
        return ResultadoConsultaLote(inep=inep, status=StatusConsultaLote.SUCESSO, ...)

resumo = use_case.executar(plano, consultor=ConsultorFalso(), notificador=None)
```
