"""
Aggregate Root: representa o resultado completo de uma consulta por INEP.

`ConsultaEscola` é o único ponto de entrada para os dados de uma escola —
o restante da aplicação nunca deveria trabalhar com `Escola`,
`Conectividade` ou `Provedores` soltos, e sim sempre através deste
agregado, montado pelo `AgregadorDeConsulta` (infraestrutura) a partir
dos frames recebidos.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from conectividade.domain.conectividade import Conectividade
from conectividade.domain.erro_consulta import ErroConsulta
from conectividade.domain.escola import Escola
from conectividade.domain.provedores import Provedores


@dataclass(frozen=True, slots=True)
class ConsultaEscola:
    """Resultado completo de uma consulta ao portal para um código INEP."""

    inep: str
    escola: Escola
    conectividade: Conectividade | None = None
    provedores: Provedores | None = None
    erros: tuple[ErroConsulta, ...] = field(default_factory=tuple)

    @property
    def possui_medidor_ativo(self) -> bool:
        """True se a escola tem conectividade reportada e o medidor está ativo."""
        return self.conectividade is not None and self.conectividade.medidor_ativo
