from __future__ import annotations

from dataclasses import replace

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
from conectividade.infrastructure.shiny.mapeadores import (
    mapear_conectividade,
    mapear_escola,
    mapear_provedores,
)


class AgregadorDeConsulta:
    """Acumula os frames de uma consulta e monta o agregado final."""

    def __init__(self, inep: str) -> None:
        self.inep = inep

        self._escola: EscolaFrameDTO | None = None
        self._conectividade: ConectividadeFrameDTO | None = None
        self._provedores: ProvedoresFrameDTO | None = None
        self._erros: list[ErroFrameDTO] = []

    def registrar(self, processado: FrameProcessado) -> None:
        if isinstance(processado, EscolaFrameDTO):
            self._merge_escola(processado)
            return

        if isinstance(processado, ConectividadeFrameDTO):
            self._conectividade = processado
            return

        if isinstance(processado, ProvedoresFrameDTO):
            self._provedores = processado
            return

        if isinstance(processado, ErroFrameDTO):
            self._erros.append(processado)

    def _merge_escola(self, novo: EscolaFrameDTO) -> None:
        if self._escola is None:
            self._escola = novo
            return

        self._escola = replace(
            self._escola,
            nome_escola=novo.nome_escola or self._escola.nome_escola,
            uf_escola=novo.uf_escola or self._escola.uf_escola,
            dependencia_escola=(
                novo.dependencia_escola
                or self._escola.dependencia_escola
            ),
            estudantes_escola=(
                novo.estudantes_escola
                or self._escola.estudantes_escola
            ),
            medicoes_escola=(
                novo.medicoes_escola
                or self._escola.medicoes_escola
            ),
            max_95_down=(
                novo.max_95_down
                or self._escola.max_95_down
            ),
            vel_adequada=(
                novo.vel_adequada
                or self._escola.vel_adequada
            ),
        )

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
