from __future__ import annotations

from dataclasses import fields, replace
from typing import TypeVar

from conectividade.domain.consulta_escola import ConsultaEscola
from conectividade.domain.erro_consulta import ErroConsulta
from conectividade.domain.exceptions import EscolaNaoEncontradaError
from conectividade.infrastructure.shiny.dtos import (
    ConectividadeFrameDTO,
    EscolaFrameDTO,
    ErroFrameDTO,
    FrameProcessado,
    ProvedoresFrameDTO,
)
from conectividade.infrastructure.shiny.frame_bruto import FrameFechamento
from conectividade.infrastructure.shiny.mapeadores import (
    mapear_conectividade,
    mapear_escola,
    mapear_provedores,
)

_TDto = TypeVar("_TDto", EscolaFrameDTO, ConectividadeFrameDTO, ProvedoresFrameDTO)


def _merge_dto(existente: _TDto | None, novo: _TDto) -> _TDto:
    """Combina um DTO parcial novo com o estado acumulado, campo a campo.

    Cada frame do Shiny costuma trazer só um subconjunto dos campos de um
    domínio (ex.: um frame traz `nome_escola`/`uf_escola`, outro traz
    `medicoes_escola`/`max_95_down`). O merge preserva o que já foi visto:
    um campo só é sobrescrito quando o novo frame realmente traz um valor
    para ele; caso contrário o valor acumulado anteriormente é mantido.
    """
    if existente is None:
        return novo

    atualizacoes = {
        campo.name: getattr(novo, campo.name) or getattr(existente, campo.name)
        for campo in fields(existente)
    }
    return replace(existente, **atualizacoes)


class AgregadorDeConsulta:
    """Acumula os frames de uma consulta e monta o agregado final."""

    def __init__(self, inep: str) -> None:
        self.inep = inep

        self._escola: EscolaFrameDTO | None = None
        self._conectividade: ConectividadeFrameDTO | None = None
        self._provedores: ProvedoresFrameDTO | None = None
        self._erros: list[ErroFrameDTO] = []
        self._fechamento_anormal: FrameFechamento | None = None

    def registrar_fechamento(self, fechamento: FrameFechamento) -> None:
        """Registra um frame de fechamento do socket.

        Código 1000 é fechamento normal (a consulta seguiu seu curso e o
        socket foi encerrado depois) e é ignorado aqui. Qualquer outro
        código (ex.: 4503 "The application unexpectedly exited") indica
        que o servidor derrubou a aplicação Shiny no meio da consulta —
        guardamos isso para `_aguardar_conclusao` poder abortar na hora,
        em vez de estourar o timeout inteiro com um erro genérico.
        """
        if fechamento.code != 1000 and self._fechamento_anormal is None:
            self._fechamento_anormal = fechamento

    @property
    def fechamento_anormal(self) -> FrameFechamento | None:
        return self._fechamento_anormal

    def registrar(self, processado: FrameProcessado) -> None:
        if isinstance(processado, EscolaFrameDTO):
            self._escola = _merge_dto(self._escola, processado)
            return

        if isinstance(processado, ConectividadeFrameDTO):
            self._conectividade = _merge_dto(self._conectividade, processado)
            return

        if isinstance(processado, ProvedoresFrameDTO):
            self._provedores = _merge_dto(self._provedores, processado)
            return

        if isinstance(processado, ErroFrameDTO):
            self._erros.append(processado)

    @property
    def completo(self) -> bool:
        if self._erros:
            return True

        if self._escola is None:
            return False

        return all(
            (
                self._escola.nome_escola,
                self._escola.uf_escola,
                self._escola.dependencia_escola,
                self._escola.estudantes_escola,
                self._escola.medicoes_escola,
                self._escola.max_95_down,
                self._escola.vel_adequada,
            )
        )

    def montar(self) -> ConsultaEscola:
        if self._escola is None:
            detalhes = "; ".join(
                f"{erro.origem}: {erro.mensagem}"
                for erro in self._erros
            )

            raise EscolaNaoEncontradaError(
                f"Nenhuma escola encontrada para o INEP {self.inep!r}."
                + (f" {detalhes}" if detalhes else "")
            )

        return ConsultaEscola(
            inep=self.inep,
            escola=mapear_escola(self._escola),
            conectividade=(
                mapear_conectividade(self._conectividade)
                if self._conectividade
                else None
            ),
            provedores=(
                mapear_provedores(self._provedores)
                if self._provedores
                else None
            ),
            erros=tuple(
                ErroConsulta(
                    origem=erro.origem,
                    mensagem=erro.mensagem,
                )
                for erro in self._erros
            ),
        )
