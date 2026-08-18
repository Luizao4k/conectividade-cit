"""
Detecção de que a resposta do portal para um INEP está completa e
estável.

`ConsultorEscolaPortalPolling` recarrega a página antes de cada
consulta (ver `docs/LOTE_OPERACIONAL.md`), então na prática este
detector sempre roda com `assinatura_anterior=None` — o ramo "consultas
seguintes" abaixo existe para o caso (hoje não usado) de uma
implementação que reaproveite a mesma sessão do Shiny entre consultas,
onde é preciso distinguir "os dados antigos ainda estão na tela" de
"os dados novos já chegaram e pararam de mudar".

O algoritmo abaixo é uma tradução direta (mesma lógica, mesmos limiares)
do laço originalmente implementado em `main.py`, só reorganizado em uma
classe com dependências explícitas.
"""
from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

from conectividade.dominio.dados_escola import DadosEscolaLote
from conectividade.dominio.resultado_consulta import StatusConsultaLote
from conectividade.infraestrutura.shiny_polling.leitura_reativa import LeitorValoresReativos

if TYPE_CHECKING:
    from playwright.sync_api import Page

logger = logging.getLogger(__name__)

_MENSAGEM_INEP_NAO_RECONHECIDO = "O INEP digitado não foi reconhecido"


class DetectorEstabilizacao:
    """
    Aguarda o portal responder a um INEP enviado e os dados retornados
    ficarem estáveis por `tempo_estabilizacao` segundos seguidos.
    """

    def __init__(
        self,
        page: Page,
        leitor: LeitorValoresReativos,
        *,
        timeout_resposta: float,
        intervalo_polling: float,
        tempo_estabilizacao: float,
    ) -> None:
        self._page = page
        self._leitor = leitor
        self._timeout_resposta = timeout_resposta
        self._intervalo_polling = intervalo_polling
        self._tempo_estabilizacao = tempo_estabilizacao

    def aguardar(
        self,
        inep: str,
        assinatura_anterior: tuple[Any, ...] | None,
    ) -> tuple[StatusConsultaLote, dict[str, Any]]:
        """
        Aguarda a resposta do portal para `inep`.

        Estratégia:
            1. Detecta INEP inexistente.
            2. Confirma que o Shiny já registrou este INEP como input atual.
            3. Aguarda os dados anteriores serem substituídos.
            4. Detecta a nova assinatura dos dados.
            5. Aguarda estabilidade (mesma assinatura por `tempo_estabilizacao`).
            6. Retorna somente os dados estabilizados.
        """
        logger.info("Aguardando resposta do portal...")

        inicio = time.monotonic()

        nova_assinatura: tuple[Any, ...] | None = None
        valores_finais: dict[str, Any] | None = None
        inicio_estabilidade: float | None = None

        mostrou_processamento = False
        mostrou_limpeza = False
        mostrou_novos_dados = False

        while time.monotonic() - inicio < self._timeout_resposta:
            # 1. INEP não encontrado -----------------------------------
            if self._inep_nao_encontrado():
                logger.info("Portal informou que o INEP não foi encontrado.")
                return StatusConsultaLote.NAO_ENCONTRADO, {}

            # 2. Confirma INEP no Shiny ---------------------------------
            if self._leitor.ler_input_inep() != inep:
                self._aguardar_proximo_ciclo()
                continue

            if not mostrou_processamento:
                logger.info("Portal processando o novo INEP...")
                mostrou_processamento = True

            # 3. Lê os valores reativos atuais ---------------------------
            valores = self._leitor.ler()
            if not valores:
                self._aguardar_proximo_ciclo()
                continue

            dados_atuais = DadosEscolaLote.a_partir_de_valores_brutos(valores)
            assinatura_atual = dados_atuais.assinatura

            # 4. Dados ainda não válidos (sem nome de escola) ------------
            if not dados_atuais.possui_nome_valido:
                if not mostrou_limpeza:
                    logger.info("Dados anteriores foram limpos.")
                    mostrou_limpeza = True
                self._aguardar_proximo_ciclo()
                continue

            # 5a. Primeira consulta do lote --------------------------------
            if assinatura_anterior is None:
                if not mostrou_novos_dados:
                    logger.info("Primeiros dados recebidos...")
                    mostrou_novos_dados = True

                if nova_assinatura is None or assinatura_atual != nova_assinatura:
                    nova_assinatura = assinatura_atual
                    valores_finais = valores
                    inicio_estabilidade = time.monotonic()
                    logger.info("Dados ainda estão sendo carregados...")
                else:
                    assert inicio_estabilidade is not None
                    tempo_estavel = time.monotonic() - inicio_estabilidade

                    if tempo_estavel >= self._tempo_estabilizacao:
                        logger.info("Dados da escola carregados e estabilizados em Shiny.$values.")
                        assert valores_finais is not None
                        return StatusConsultaLote.SUCESSO, valores_finais

                self._aguardar_proximo_ciclo()
                continue

            # 5b. Consultas seguintes: ainda com os dados antigos ---------
            if assinatura_atual == assinatura_anterior:
                if not mostrou_limpeza:
                    logger.info("Dados anteriores ainda presentes.")
                    mostrou_limpeza = True
                self._aguardar_proximo_ciclo()
                continue

            # 5c. Consultas seguintes: dados novos ainda instáveis ---------
            if nova_assinatura is None or assinatura_atual != nova_assinatura:
                nova_assinatura = assinatura_atual
                valores_finais = valores
                inicio_estabilidade = time.monotonic()

                if not mostrou_novos_dados:
                    logger.info("Novos dados detectados. Carregando dados da escola...")
                    mostrou_novos_dados = True
                else:
                    logger.info("Portal ainda atualizando os dados...")

                self._aguardar_proximo_ciclo()
                continue

            # 5d. Consultas seguintes: dados estáveis ----------------------
            assert inicio_estabilidade is not None
            assert valores_finais is not None
            tempo_estavel = time.monotonic() - inicio_estabilidade

            if tempo_estavel >= self._tempo_estabilizacao:
                logger.info("Dados da escola carregados e estabilizados em Shiny.$values.")
                return StatusConsultaLote.SUCESSO, valores_finais

            self._aguardar_proximo_ciclo()

        logger.warning("O portal não apresentou uma resposta válida para o INEP %s.", inep)
        return StatusConsultaLote.TIMEOUT, {}

    def _aguardar_proximo_ciclo(self) -> None:
        self._page.wait_for_timeout(int(self._intervalo_polling * 1000))

    def _inep_nao_encontrado(self) -> bool:
        """Detecta a mensagem exibida pelo portal quando o INEP não é reconhecido."""
        try:
            texto = self._page.locator("body").inner_text(timeout=1000)
        except Exception:
            return False

        return _MENSAGEM_INEP_NAO_RECONHECIDO in texto
