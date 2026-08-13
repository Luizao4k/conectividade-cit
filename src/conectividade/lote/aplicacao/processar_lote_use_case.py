"""
Caso de uso principal do processamento em lote.

Não conhece Playwright, Shiny ou CSV — só as portas injetadas no
construtor (`RepositorioIneps`, `RepositorioResultadosLote`) e, por
consulta, um `ConsultorEscolaPortal` (que representa a sessão de
navegador já aberta e pronta para consultar).
"""
from __future__ import annotations

import logging
from dataclasses import replace

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

_CAMPOS_PROVEDOR_SUJEITOS_A_DESCARTE: tuple[str, ...] = ("provedor_do_estabelecimento",)
"""
Só o provedor específico da escola entra no descarte de repetição —
`provedoresSIMET_regiao` fica de fora porque é um dado por região, e
duas escolas vizinhas no mesmo lote legitimamente têm a mesma lista de
provedores da região; descartá-lo também apagaria dado real com
frequência. Ver `docs/LOTE_OPERACIONAL.md`.
"""


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
            # `assinatura_anterior` é o "cru" da consulta bem-sucedida
            # anterior (nunca com provedores descartados — ver mais
            # abaixo) porque é isto que o `ConsultorEscolaPortal` usa
            # para saber se os dados na tela já são os do INEP atual.
            resultado_bruto = self._consultar_com_seguranca(consultor, inep, assinatura_anterior)

            resultado_para_registrar = self._sem_provedores_repetidos(resultado_bruto, assinatura_anterior)

            self._repositorio_resultados.salvar(resultado_para_registrar)

            if notificador is not None:
                notificador.consulta_concluida(indice=indice, total=total, resultado=resultado_para_registrar)

            if resultado_bruto.sucesso:
                assinatura_anterior = resultado_bruto.assinatura

            resultados.append(resultado_para_registrar)

        return ResumoLote.a_partir_de(resultados)

    @staticmethod
    def _sem_provedores_repetidos(
        resultado: ResultadoConsultaLote,
        assinatura_anterior: tuple[object, ...] | None,
    ) -> ResultadoConsultaLote:
        """
        Aplica `DadosEscolaLote.descartando_provedores_nao_atualizados` ao
        resultado que será salvo/exibido — sem alterar o `resultado`
        original usado para encadear a assinatura da próxima consulta.

        Isto é proposital: se descartássemos o provedor diretamente no
        objeto que também alimenta `assinatura_anterior`, a consulta
        seguinte compararia os dados "crus" ainda na tela (com o
        provedor real, não descartado) contra uma assinatura "limpa"
        (com `None` no lugar do provedor) — os dois nunca bateriam por
        causa só do provedor, e o detector de estabilização passaria a
        interpretar dados antigos como se fossem uma resposta nova.

        Restrito a `_CAMPOS_PROVEDOR_SUJEITOS_A_DESCARTE` (só o provedor
        da escola) — `provedoresSIMET_regiao` nunca é descartado por
        este mecanismo, para não apagar dado real de escolas vizinhas na
        mesma região.
        """
        if not resultado.sucesso:
            return resultado

        dados_limpos = resultado.dados.descartando_provedores_nao_atualizados(
            assinatura_anterior,
            campos=_CAMPOS_PROVEDOR_SUJEITOS_A_DESCARTE,
        )

        if dados_limpos is resultado.dados:
            return resultado

        return replace(resultado, dados=dados_limpos)

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
