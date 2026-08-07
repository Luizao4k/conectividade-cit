# debug_agregador.py

from playwright.sync_api import sync_playwright
from conectividade.infrastructure.shiny.shiny_client import ShinyClient
import logging
import json

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def testar_consulta():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        # Vai para o portal
        page.goto("https://conectividadenaeducacao.nic.br/#sua-escola")
        
        # Aguarda o Shiny carregar
        page.wait_for_selector(".shiny-bound-input", timeout=10000)
        
        # Habilita o logging do WebSocket
        page.evaluate("""
            () => {
                window._mensagens_ws = [];
                const originalSend = WebSocket.prototype.send;
                WebSocket.prototype.send = function(data) {
                    window._mensagens_ws.push({type: 'sent', data: data});
                    return originalSend.call(this, data);
                };
                
                // Captura mensagens recebidas
                const originalAddEventListener = WebSocket.prototype.addEventListener;
                WebSocket.prototype.addEventListener = function(type, listener) {
                    if (type === 'message') {
                        const wrapped = function(event) {
                            window._mensagens_ws.push({type: 'received', data: event.data});
                            return listener(event);
                        };
                        return originalAddEventListener.call(this, type, wrapped);
                    }
                    return originalAddEventListener.call(this, type, listener);
                };
            }
        """)
        
        # Cria o cliente
        client = ShinyClient(page, timeout_segundos=30)
        
        try:
            # Faz a consulta
            logger.info("Iniciando consulta...")
            resultado = client.consultar("15001156")
            
            logger.info(f"Resultado obtido: {json.dumps(resultado.dados, ensure_ascii=False, indent=2)}")
            
            # Mostra todas as mensagens capturadas
            mensagens = page.evaluate("() => window._mensagens_ws || []")
            logger.info(f"Total de mensagens capturadas: {len(mensagens)}")
            
            for i, msg in enumerate(mensagens[:10]):  # Mostra as primeiras 10
                logger.info(f"Mensagem {i+1}: {msg['type']} - {msg['data'][:200]}")
                
        except Exception as e:
            logger.error(f"Erro: {e}", exc_info=True)
            
        finally:
            input("Pressione ENTER para fechar...")
            browser.close()

if __name__ == "__main__":
    testar_consulta()
