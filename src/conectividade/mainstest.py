"""
Teste de integração para leitura dos dados reativos do Shiny.

Fluxo:
1. Abre o Chrome com perfil persistente.
2. Permite configurar o proxy manualmente.
3. Acessa o portal Conectividade na Educação.
4. Aguarda o Shiny estabelecer conexão.
5. Envia um código INEP.
6. Aguarda a resposta reativa do Shiny.
7. Lê Shiny.shinyapp.$values.
8. Normaliza os valores.
9. Exibe os dados da escola.

Este arquivo é um teste de integração/debug.
Ele não utiliza: FrameRouter, WebSocketListener, ShinyClient, AgregadorDeConsulta.
A finalidade é validar a leitura direta dos valores reativos do Shiny.
"""

from __future__ import annotations

import time
from typing import Any

from conectividade.infrastructure.browser.browser import Browser

# --------------------------------------------------------------------------
# CONFIGURAÇÃO
# --------------------------------------------------------------------------
INEP = "15001156"
URL_PORTAL = "https://conectividadenaeducacao.nic.br/#sua-escola"

TIMEOUT_SHINY = 90.0
TIMEOUT_DADOS = 120.0
INTERVALO_POLLING = 1.0

# --------------------------------------------------------------------------
# CAMPOS
# --------------------------------------------------------------------------
CAMPOS_ESCOLA = (
    "nome_escola",
    "uf_escola",
    "dependencia_escola",
    "estudantes_escola",
    "estudantes_escola_maior_turno",
    "vel_adequada",
    "status_medidor",
    "vel_download",
    "vel_upload",
    "latencia",
    "jitter",
    "perda_pacote",
    "nro_medicoes",
    "medicoes_escola",
    "max_95_down",
)


# --------------------------------------------------------------------------
# SHINY
# --------------------------------------------------------------------------
def ler_shiny_values(page) -> dict[str, Any]:
    """
    Lê Shiny.shinyapp.$values.
    Durante a reação ao envio do INEP, o contexto JavaScript pode ser
    destruído temporariamente. Nesses casos, retorna {} para continuar o polling.
    """
    try:
        valores = page.evaluate(
            """
            () => {
                const values = window.Shiny
                    ?.shinyapp
                    ?.$values;
                return values ?? {};
            }
            """
        )
    except Exception as exc:
        mensagem = str(exc)
        if "Execution context was destroyed" in mensagem:
            return {}
        raise

    if not isinstance(valores, dict):
        return {}
    return valores


def shiny_esta_conectado(page) -> bool:
    """Verifica se o runtime Shiny está conectado ao servidor."""
    try:
        estado = page.evaluate(
            """
            () => ({
                shiny: !!window.Shiny,
                app: !!window.Shiny?.shinyapp,
                socket: window.Shiny
                    ?.shinyapp
                    ?.$socket
                    ?.readyState ?? null
            })
            """
        )
    except Exception as exc:
        if "Execution context was destroyed" in str(exc):
            return False
        raise

    return bool(
        estado["shiny"]
        and estado["app"]
        and estado["socket"] == 1
    )


def aguardar_shiny(page) -> None:
    """Aguarda o Shiny estabelecer conexão via WebSocket."""
    print("\nAguardando conexão do Shiny...")
    inicio = time.monotonic()
    
    while time.monotonic() - inicio < TIMEOUT_SHINY:
        if shiny_esta_conectado(page):
            print("[OK] Shiny conectado.")
            return
        page.wait_for_timeout(int(INTERVALO_POLLING * 1000))

    raise TimeoutError(
        f"Shiny não estabeleceu conexão em {TIMEOUT_SHINY:.0f} segundos."
    )


# --------------------------------------------------------------------------
# INEP
# --------------------------------------------------------------------------
def enviar_inep(page, inep: str) -> None:
    """
    Envia o código INEP para o input do Shiny.
    Preenche via DOM e dispara o evento reativo explicitamente via Shiny.setInputValue().
    """
    print(f"\nEnviando INEP: {inep}")
    campo = page.locator("#inep_plano")
    campo.wait_for(state="visible", timeout=10_000)
    campo.fill(inep)

    page.evaluate(
        """
        (inep) => {
            Shiny.setInputValue(
                "inep_plano",
                inep,
                { priority: "event" }
            );
        }
        """,
        inep,
    )

    estado = page.evaluate(
        """
        () => ({
            dom: document.querySelector("#inep_plano")?.value ?? "",
            shiny: Shiny?.shinyapp?.$inputValues?.inep_plano ?? "",
            socket: Shiny?.shinyapp?.$socket?.readyState ?? null
        })
        """
    )
    print("[INPUT]", estado)


# --------------------------------------------------------------------------
# DADOS
# --------------------------------------------------------------------------
def dados_prontos(valores: dict[str, Any]) -> bool:
    """
    Verifica se os dados básicos e o estado de medição já carregaram.
    """
    tem_dados_basicos = all(
        valores.get(campo)
        for campo in ("nome_escola", "uf_escola", "dependencia_escola")
    )
    
    # Se nem os dados básicos chegaram, continua esperando
    if not tem_dados_basicos:
        return False

    # Se a escola tem vel_download preenchida OU se o Shiny declarou nro_medicoes,
    # consideremos pronto.
    medicoes = valores.get("nro_medicoes")
    vel_down = valores.get("vel_download")

    # Retorna True se a velocidade já foi populada OU se explicitamente não há medições (ex: 0 medições)
    return vel_down is not None or medicoes is not None


def aguardar_dados(page) -> dict[str, Any]:
    """
    Aguarda a hidratação completa dos valores reativos no Shiny.
    """
    print("\nAguardando dados da escola...")
    inicio = time.monotonic()
    
    valores_finais = {}
    
    while time.monotonic() - inicio < TIMEOUT_DADOS:
        valores = ler_shiny_values(page)
        if valores:
            valores_finais = valores
            if dados_prontos(valores):
                print("[OK] Dados da escola carregados com sucesso em Shiny.$values.")
                return valores
                
        page.wait_for_timeout(int(INTERVALO_POLLING * 1000))

    print("⚠️ Timeout atingido. Retornando últimos dados obtidos do Shiny...")
    return valores_finais
# --------------------------------------------------------------------------
# NORMALIZAÇÃO
# --------------------------------------------------------------------------
def normalizar_valor(valor: Any) -> Any:
    """
    Normaliza um valor retornado por Shiny.$values.
    Caso seja um dicionário contendo HTML (ex: {'html': '246,3', 'deps': []}),
    extrai apenas a string do payload.
    """
    if isinstance(valor, dict):
        if "html" in valor:
            return valor["html"]
        return valor
    return valor


def extrair_dados_escola(valores: dict[str, Any]) -> dict[str, Any]:
    """Extrai e normaliza somente os campos relevantes de medição da escola."""
    return {
        campo: normalizar_valor(valores.get(campo))
        for campo in CAMPOS_ESCOLA
    }


# --------------------------------------------------------------------------
# SAÍDA
# --------------------------------------------------------------------------
def imprimir_dados(dados: dict[str, Any]) -> None:
    """Exibe os dados extraídos no terminal."""
    print("\n" + "=" * 80)
    print("DADOS DE CONECTIVIDADE DA ESCOLA (NIC.br)")
    print("=" * 80)
    for campo, valor in dados.items():
        print(f"{campo:<40} => {valor}")
    print("=" * 80)


# --------------------------------------------------------------------------
# MAIN
# --------------------------------------------------------------------------
def main() -> None:
    """Executa o teste de integração."""
    print("=== TESTE DE LEITURA REATIVA DO SHINY.$VALUES ===")
    
    with Browser(url_portal=URL_PORTAL, headless=False) as browser:
        print("\nChrome aberto.")
        print("Configure o proxy manualmente (caso necessário).")
        input("Pressione ENTER após configurar o proxy/carregar a página...")

        page = browser.page
        print("\nURL atual:", page.url)

        # Navegação inicial se necessário
        if "conectividadenaeducacao.nic.br" not in page.url:
            print("\nAbrindo portal...")
            page.goto(
                URL_PORTAL,
                wait_until="domcontentloaded",
                timeout=120_000,
            )

        # 1. Aguarda inicialização do Shiny
        aguardar_shiny(page)

        # 2. Envia INEP
        enviar_inep(page, INEP)

        # 3. Aguarda resposta reativa no $values
        valores = aguardar_dados(page)

        # 4. Extrai e normaliza
        dados = extrair_dados_escola(valores)

        # 5. Exibe resultado
        imprimir_dados(dados)

        print("\n[SUCESSO] Teste de extração concluído!")
        input("\nPressione ENTER para fechar o navegador...")


if __name__ == "__main__":
    main()