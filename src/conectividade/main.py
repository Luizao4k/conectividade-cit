# NO TOPO DO ARQUIVO, ANTES DE QUALQUER IMPORTAÇÃO
print("=== Módulo conectividade.main carregado ===", flush=True)

from conectividade.factory import criar_consulta_service
from conectividade.infrastructure.browser.browser import Browser

URL_PORTAL = "https://conectividadenaeducacao.nic.br/#sua-escola"

def main() -> None:
    print(">>> Iniciando main()", flush=True)
    try:
        with Browser(url_portal=URL_PORTAL, headless=False) as browser:
            print("Chrome aberto.", flush=True)
            print("Configure o proxy manualmente.")
            input("Pressione ENTER após configurar o proxy...")

            page = browser.page
            page.on("websocket", lambda ws: print("WEBSOCKET:", ws.url))

            consulta_service = criar_consulta_service(page)

            print("Iniciando navegação...")
            page.goto(
                URL_PORTAL,
                wait_until="load",
                timeout=120000,
            )

            print("HTML recebido")
            print("URL:", page.url)

            page.screenshot(path="portal_debug.png", full_page=True)
            print("Shiny:", page.evaluate("() => typeof window.Shiny"))
            print(
                page.evaluate("""
                () => ({
                    initialized: !!window.Shiny?.shinyapp,
                    connected: !!window.Shiny?.shinyapp?.$socket,
                    socketReady: window.Shiny?.shinyapp?.$socket?.readyState
                })
                """)
            )

            page.wait_for_timeout(5000)
            resultado = consulta_service.consultar("15001156",)
            print(resultado)

            input("ENTER para fechar...")
    except Exception as e:
        print(f"ERRO FATAL: {e}", flush=True)
        import traceback
        traceback.print_exc()
        input("Pressione ENTER para sair...")

if __name__ == "__main__":
    main()
