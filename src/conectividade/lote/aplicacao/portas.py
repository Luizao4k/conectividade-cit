"""
Portas (interfaces) que o caso de uso de processamento em lote depende.

Como em `conectividade.application.ports`, são `Protocol`s: qualquer
classe com os métodos certos serve como implementação, sem herança.
"""
from __future__ import annotations

from typing import Protocol

from conectividade.lote.dominio.resultado_consulta import ResultadoConsultaLote


class RepositorioIneps(Protocol):
    """Fonte da lista de códigos INEP a processar."""

    def carregar(self) -> list[str]:
        """Retorna os códigos INEP a processar, na ordem em que devem ser consultados."""
        ...


class RepositorioResultadosLote(Protocol):
    """Armazenamento incremental dos resultados do lote (com suporte a retomada)."""

    def carregar_processados(self) -> set[str]:
        """Retorna os INEPs que já têm um resultado salvo de uma execução anterior."""
        ...

    def salvar(self, resultado: ResultadoConsultaLote) -> None:
        """Persiste um resultado imediatamente (chamado após cada consulta)."""
        ...


class ConsultorEscolaPortal(Protocol):
    """Executa uma única consulta de INEP contra o portal, já aberto em uma página."""

    def consultar(
        self,
        inep: str,
        assinatura_anterior: tuple[object, ...] | None,
    ) -> ResultadoConsultaLote:
        """
        Consulta um INEP.

        `assinatura_anterior` é a assinatura dos dados da consulta bem
        sucedida anterior no mesmo lote (ou `None` na primeira consulta) —
        necessária para o portal detectar que os dados antigos já foram
        substituídos pelos novos antes de considerá-los estáveis.
        """
        ...


class NotificadorProgressoLote(Protocol):
    """Reporta o andamento do processamento em lote (ex.: console, log estruturado)."""

    def consulta_concluida(
        self,
        *,
        indice: int,
        total: int,
        resultado: ResultadoConsultaLote,
    ) -> None:
        """Chamado após cada consulta (sucesso ou falha) ser processada e salva."""
        ...
