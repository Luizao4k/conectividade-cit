"""
Adapter de infraestrutura que consulta o portal fazendo *polling* direto
de `Shiny.shinyapp.$values`, em vez de interceptar frames de WebSocket.

Ver `docs/LOTE_OPERACIONAL.md` para o racional desta estratégia (mais
simples de operar em lote, ao custo de ler o estado reativo por
amostragem em vez de reagir a cada frame).
"""
from __future__ import annotations
