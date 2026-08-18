"""
Consulta em lote ao portal Conectividade na Educação por código INEP.

Uso (ver `docs/LOTE_OPERACIONAL.md` para o guia completo):

    python -m conectividade.infraestrutura.cli --particoes 2 --indice-particao 0
    python -m conectividade.infraestrutura.cli --particoes 2 --indice-particao 1
    # ou, após `pip install -e .`:
    conectividade-lote --particoes 2 --indice-particao 0

Este pacote não expõe uma API pública própria — o ponto de entrada é o
CLI de lote (`conectividade.infraestrutura.cli`). Veja
`docs/ARQUITETURA.md` e `docs/LOTE_OPERACIONAL.md`.
"""
from __future__ import annotations
