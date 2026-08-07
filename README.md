# Conectividade Educação - Cliente Shiny WebSocket

Módulo de consulta ao portal **Conectividade na Educação**, por código
INEP, encapsulando toda a comunicação com o portal (navegador, proxy,
WebSocket, protocolo Shiny) atrás de uma interface simples e reutilizável.

## Uso

```python
from conectividade import criar_consulta_service

consulta_service = criar_consulta_service(page)

resultado = consulta_service.consultar("15001156")

resultados = consulta_service.consultar_lote(["15001156", "11000222"])

```


## Instalação

Requer Python 3.11+.

```bash
pip install -e .
python -m playwright install chromium
```

## Arquitetura Atual

```O fluxo de processamento segue o modelo:

                 Navegador Chrome
                        |
                        |
                  Aplicação Shiny
                        |
                        |
                   WebSocket
                        |
                        v
              Shiny WebSocket Client
                        |
                        v
                Frame Decoder
                        |
                        v
                Frame Router
                        |
          +-------------+-------------+
          |             |             |
          v             v             v
     EscolaParser  Conectividade  Provedores
          |
          v
     EscolaFrameDTO
          |
          v
     ConsultaEscola
```

### Por que rotear pelo conteúdo, e não pela tag do frame

As tags (`C2`, `C9`, `CE`...) são um contador sequencial interno do
Shiny — no seu próprio levantamento, elas não são garantidas estáveis
entre consultas (dependem de que outros elementos reativos do painel
disparam antes). Por isso o `RoteadorDeFrames` decide pelo **conjunto de
chaves** dentro de `values` (ex.: um frame com `nome_escola` +
`uf_escola` + ... só pode ser o frame de escola), o que o torna
independente dessa numeração.

# Funcionamento

## Inicialização

O cliente inicia o navegador e aguarda a configuração do ambiente:

Chrome aberto.
Configure o proxy manualmente.
Pressione ENTER após configurar o proxy...

Após a configuração, inicia a navegação para a aplicação Shiny.

## Conexão WebSocket

A aplicação estabelece comunicação através de:

wss://conectividadenaeducacao.nic.br/sockjs/.../websocket

Após a conexão:

Shiny:
{
    initialized: true,
    connected: true,
    socketReady: 1
}

O cliente passa a interceptar os frames enviados pelo servidor.

Processamento dos Frames

Cada mensagem recebida pelo WebSocket contém eventos ou valores retornados pelo Shiny.

Exemplos:

Evento de processamento
{
    "busy":"busy"
}

Indica que a aplicação iniciou um processamento.

Atualização de componente
{
    "recalculating":{
        "name":"nome_escola",
        "status":"recalculating"
    }
}

Indica atualização de um componente reativo.

## Dados de negócio

Exemplo:

{
    "values":{
        "nome_escola":"Escola E M E I F Sao Jose",
        "uf_escola":"Município: Juruti - Para",
        "estudantes_escola":
        "Número de estudantes: 54"
    }
}

Esse frame é processado pelo:

EscolaFrameParser

Gerando:

EscolaFrameDTO(
    nome_escola="Escola E M E I F Sao Jose",
    uf_escola="Município: Juruti - Para",
    estudantes_escola=54
)
Componentes Principais
WebSocket Client

Responsável por:

conexão com servidor Shiny;
captura dos frames;
controle do socket;
envio dos inputs.
Frame Router

Responsável pela distribuição dos frames recebidos.

Exemplo:

Frame recebido
       |
       v
Frame Router
       |
       +---- EscolaParser
       |
       +---- MedicaoParser
       |
       +---- ProvedorParser
## Parsers

Os parsers transformam estruturas Shiny em objetos de domínio.

Atualmente:

EscolaFrameParser
ConectividadeFrameParser
ProvedoresFrameParser

## Testes

Este projeto ainda não tem testes automatizados.

# Status Atual

✅ Comunicação WebSocket funcional
✅ Captura de frames Shiny
✅ Parser de escola funcional
✅ Extração de dados cadastrais
✅ Extração de dados de medição

## Em evolução:

🚧 Agregação de estado
🚧 Classificação dinâmica de frames
🚧 Cobertura de testes
🚧 Observabilidade operacional

# Licença

Projeto interno, desenvolvido por Luiz Paulo destinado ao processamento automatizado de dados da plataforma Conectividade Educação.