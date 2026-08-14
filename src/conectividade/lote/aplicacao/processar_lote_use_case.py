"""
Caso de uso principal do processamento em lote.

Não conhece Playwright, Shiny ou CSV — só as portas injetadas no
construtor (`RepositorioIneps`, `RepositorioResultadosLote`) e, por
consulta, um `ConsultorEscolaPortal` (que representa a sessão de
navegador já aberta e pronta para consultar).
"""
from __future__ import annotations

import logging

from conectividade.lote.aplicacao.portas import (
    ConsultorEscolaPortal,
    NotificadorProgressoLote,
    RepositorioIneps,
    RepositorioResultadosLote,
)
from conectividade.lote.dominio.plano_execucao import PlanoExecucaoLote
from conectividade.lote.dominio.resultado_consulta import ResultadoConsultaLote, StatusConsultaLote
from conectividade.lote.dominio.resumo_lote import ResumoLote

logger = logging.getLogger(__name__)


class ProcessarLoteUseCase:
    """Orquestra a consulta de um lote de INEPs, com checkpoint e salvamento incremental."""

    def __init__(
        self,
        *,
        repositorio_ineps: RepositorioIneps,
        repositorio_resultados: RepositorioResultadosLote,
    ) -> None:
        self._repositorio_ineps = repositorio_ineps
        self._repositorio_resultados = repositorio_resultados

    def planejar(self) -> PlanoExecucaoLote:
        """
        Calcula quais INEPs ainda precisam ser consultados, sem abrir
        nenhuma sessão de navegador.

        Chamar isto antes de `executar()` permite ao composition root (ex.:
        `infraestrutura/cli.py`) decidir se vale a pena sequer abrir o
        navegador, quando não sobrar nenhum INEP pendente.
        """
        ineps = self._repositorio_ineps.carregar()
        ja_processados = self._repositorio_resultados.carregar_processados()
        pendentes = tuple(inep for inep in ineps if inep not in ja_processados)

        return PlanoExecucaoLote(
            total_ineps=len(ineps),
            ja_processados=len(ja_processados),
            pendentes=pendentes,
        )

    def executar(
        self,
        plano: PlanoExecucaoLote,
        *,
        consultor: ConsultorEscolaPortal,
        notificador: NotificadorProgressoLote | None = None,
    ) -> ResumoLote:
        """
        Consulta, em sequência, todos os INEPs pendentes do plano.

        Cada resultado é salvo imediatamente após a consulta (via
        `RepositorioResultadosLote.salvar`), então uma interrupção no meio
        do lote não perde o progresso já feito.
        """
        resultados: list[ResultadoConsultaLote] = []
        assinatura_anterior: tuple[object, ...] | None = None
        total = len(plano.pendentes)

        for indice, inep in enumerate(plano.pendentes, start=1):
            resultado = self._consultar_com_seguranca(consultor, inep, assinatura_anterior)

            self._repositorio_resultados.salvar(resultado)

            if notificador is not None:
                notificador.consulta_concluida(indice=indice, total=total, resultado=resultado)

            if resultado.sucesso:
                assinatura_anterior = resultado.assinatura

            resultados.append(resultado)

        return ResumoLote.a_partir_de(resultados)

    @staticmethod
    def _consultar_com_seguranca(
        consultor: ConsultorEscolaPortal,
        inep: str,
        assinatura_anterior: tuple[object, ...] | None,
    ) -> ResultadoConsultaLote:
        """
        Executa uma consulta isolando falhas inesperadas: qualquer exceção
        não tratada pelo `ConsultorEscolaPortal` vira um resultado de
        status `erro` para este INEP, sem interromper o restante do lote.
        """
        try:
            return consultor.consultar(inep, assinatura_anterior)
        except Exception:
            logger.exception("Falha inesperada ao consultar o INEP %r.", inep)
            return ResultadoConsultaLote(inep=inep, status=StatusConsultaLote.ERRO)
