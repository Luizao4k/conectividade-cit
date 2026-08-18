"""
Portas (interfaces) que o caso de uso de processamento em lote depende.

São `Protocol`s: qualquer classe com os métodos certos serve como
implementação, sem herança.
"""
from __future__ import annotations

from typing import Protocol

from conectividade.dominio.resultado_consulta import ResultadoConsultaLote


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
        útil para uma implementação que reaproveita a mesma sessão do
        Shiny entre consultas, e por isso precisa distinguir dados
        antigos ainda na tela de uma resposta nova (ver
        `docs/LOTE_OPERACIONAL.md`). A implementação padrão
        (`ConsultorEscolaPortalPolling`) recarrega a página a cada
        consulta e ignora este parâmetro — nunca existe "dado antigo"
        para uma sessão que acabou de começar —, mas o parâmetro segue
        parte da porta para não travar outras estratégias que voltem a
        reaproveitar a sessão entre consultas.
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
