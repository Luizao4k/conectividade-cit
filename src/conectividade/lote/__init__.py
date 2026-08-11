"""
Bounded context de processamento em lote.

Consulta vários códigos INEP lidos de um CSV contra o portal
Conectividade na Educação, em uma única sessão de navegador, salvando
cada resultado incrementalmente (com suporte a retomar um lote
interrompido).

Este é um mecanismo de consulta **diferente** do usado pela API pública
do pacote (`conectividade.criar_consulta_service`): em vez de interceptar
frames de WebSocket, aqui a estratégia é fazer *polling* direto de
`Shiny.shinyapp.$values` até os dados estabilizarem. Veja
`docs/ARQUITETURA.md` para a justificativa de manter os dois mecanismos
lado a lado.

Uso (equivalente ao antigo `python -m conectividade.main`):

    python -m conectividade.lote.infraestrutura.cli
"""
from __future__ import annotations

__all__: list[str] = []
