"""
Value Object com os dados de uma escola tal como extraídos do painel
reativo do Shiny (`Shiny.shinyapp.$values`) durante o processamento em
lote.

Diferente do domínio da consulta individual (`conectividade.domain.escola`),
que interpreta e tipa os textos brutos do portal (ex.: separar
"Município: X - Y" em `municipio`/`uf`), aqui os campos são mantidos como
texto cru (já sem o wrapper HTML do Shiny) — é exatamente o que o
processamento em lote grava no CSV de saída, e mudar esse formato mudaria
o contrato do arquivo de resultados. Ver `docs/LOTE_OPERACIONAL.md`.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, Mapping


@dataclass(frozen=True, slots=True)
class DadosEscolaLote:
    """Campos de uma escola extraídos de `Shiny.shinyapp.$values`, já normalizados."""

    nome_escola: Any = None
    uf_escola: Any = None
    dependencia_escola: Any = None
    estudantes_escola: Any = None
    estudantes_escola_maior_turno: Any = None
    vel_adequada: Any = None
    status_medidor: Any = None
    vel_download: Any = None
    vel_upload: Any = None
    latencia: Any = None
    jitter: Any = None
    perda_pacote: Any = None
    nro_medicoes: Any = None
    medicoes_escola: Any = None
    max_95_down: Any = None

    CAMPOS: ClassVar[tuple[str, ...]] = (
        "nome_escola",
        "uf_escola",
        "dependencia_escola",
        "estudantes_escola",
        "estudantes_escola_maior_turno",
        "vel_adequada",
        "status_medidor",
        "vel_download",
        "vel_upload",
        "latencia",
        "jitter",
        "perda_pacote",
        "nro_medicoes",
        "medicoes_escola",
        "max_95_down",
    )
    """Ordem canônica dos campos — usada tanto na assinatura de
    estabilização quanto nas colunas do CSV de resultados. Preservar
    exatamente esta ordem e estes nomes é o que garante compatibilidade
    com o `resultado_lote.csv` já existente."""

    @staticmethod
    def normalizar_valor(valor: Any) -> Any:
        """
        Extrai o conteúdo textual de valores reativos do Shiny.

        O Shiny frequentemente envia valores como `{"html": "...", "deps": [...]}`
        em vez de texto puro — este método devolve só o texto (`valor["html"]`)
        nesses casos, e o valor original em qualquer outro caso.
        """
        if isinstance(valor, dict):
            if "html" in valor:
                return valor["html"]
            return valor
        return valor

    @classmethod
    def a_partir_de_valores_brutos(cls, valores: Mapping[str, Any]) -> "DadosEscolaLote":
        """Constrói a partir de um snapshot bruto de `Shiny.shinyapp.$values`."""
        return cls(
            **{
                campo: cls.normalizar_valor(valores.get(campo))
                for campo in cls.CAMPOS
            }
        )

    @property
    def possui_nome_valido(self) -> bool:
        """True se já existe um nome de escola não vazio (indício de que os dados chegaram)."""
        nome = self.nome_escola
        return isinstance(nome, str) and bool(nome.strip())

    @property
    def assinatura(self) -> tuple[Any, ...]:
        """
        Tupla com todos os campos, na ordem canônica — usada para detectar
        se os dados retornados pelo portal mudaram entre duas leituras
        (ver `DetectorEstabilizacao`).
        """
        return tuple(getattr(self, campo) for campo in self.CAMPOS)

    def como_dict(self) -> dict[str, Any]:
        """Representação em dicionário, na ordem canônica dos campos."""
        return {campo: getattr(self, campo) for campo in self.CAMPOS}
