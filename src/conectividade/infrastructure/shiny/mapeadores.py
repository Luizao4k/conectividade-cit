"""
Camada anticorrupção: converte os DTOs brutos do Shiny (strings com
prefixos e números em formato brasileiro) nos tipos de domínio, já
limpos e tipados (int, float, tuple[str, ...]).

Esta é a única parte do sistema que precisa conhecer as excentricidades
de texto do portal (ex.: "Gestão: Municipal", "39,9" para 39.9). Se o
portal mudar a redação desses textos, só este arquivo muda — `Escola`,
`Conectividade` e `Provedores` continuam exatamente iguais.
"""
from __future__ import annotations

import re

from conectividade.domain.conectividade import Conectividade
from conectividade.domain.provedores import Provedores
from conectividade.domain.escola import Escola
from conectividade.infrastructure.shiny.dtos import (
    ConectividadeFrameDTO,
    EscolaFrameDTO,
    ProvedoresFrameDTO,
)
from conectividade.infrastructure.shiny.exceptions import FrameInvalidoError

_PADRAO_MUNICIPIO_UF = re.compile(r"Município:\s*(?P<municipio>.+?)\s*-\s*(?P<uf>.+)$")
_PADRAO_ESTUDANTES = re.compile(
    r"Número de estudantes:\s*(?P<quantidade>\d+)\s*\(Censo\s*(?P<ano_censo>\d+)\)"
)
_PADRAO_VELOCIDADE_ADEQUADA = re.compile(
    r"Velocidade adequada:\s*(?P<valor>[\d.,]+)\s*Mbit/s", re.IGNORECASE
)
_PREFIXO_DEPENDENCIA = re.compile(r"^Gestão:\s*")


def mapear_escola(dto: EscolaFrameDTO) -> Escola:
    """Converte o DTO do frame principal em uma entidade `Escola`."""
    municipio, uf = _extrair_municipio_uf(dto.uf_escola)
    quantidade_estudantes, ano_censo = _extrair_estudantes(dto.estudantes_escola)

    return Escola(
        nome=dto.nome_escola,
        municipio=municipio,
        uf=uf,
        dependencia_administrativa=_PREFIXO_DEPENDENCIA.sub("", dto.dependencia_escola).strip(),
        quantidade_estudantes=quantidade_estudantes,
        ano_censo=ano_censo,
        quantidade_medicoes=_inteiro(dto.medicoes_escola),
        percentual_95_download=_numero_pt_br(dto.max_95_down),
        velocidade_adequada_mbps=_extrair_velocidade_adequada(dto.vel_adequada),
    )


def mapear_conectividade(dto: ConectividadeFrameDTO) -> Conectividade:
    """Converte o DTO do frame de qualidade de conexão em `Conectividade`."""
    return Conectividade(
        quantidade_medicoes=_inteiro(dto.nro_medicoes),
        perda_pacote_percentual=_numero_pt_br(dto.perda_pacote),
        jitter_ms=_numero_pt_br(dto.jitter),
        latencia_ms=_numero_pt_br(dto.latencia),
        velocidade_upload_mbps=_numero_pt_br(dto.vel_upload),
        velocidade_download_mbps=_numero_pt_br(dto.vel_download),
        plano_estimado_mbps=_numero_pt_br(dto.plano_estimado),
        medidor_ativo="ativo" in dto.status_medidor.lower(),
    )


def mapear_provedores(dto: ProvedoresFrameDTO) -> Provedores:
    """Converte o DTO do frame de provedores em `Provedores`."""
    return Provedores(
        provedores_regiao=_extrair_lista(dto.provedores_regiao),
        provedor_estabelecimento=_extrair_lista(dto.provedor_estabelecimento),
    )


def _numero_pt_br(texto: str) -> float:
    """Converte um número no formato brasileiro ("39,9") para float (39.9)."""
    try:
        return float(texto.replace(".", "").replace(",", "."))
    except ValueError as erro:
        raise FrameInvalidoError(f"Número em formato inesperado: {texto!r}") from erro


def _inteiro(texto: str) -> int:
    try:
        return int(texto)
    except ValueError as erro:
        raise FrameInvalidoError(f"Inteiro em formato inesperado: {texto!r}") from erro


def _extrair_municipio_uf(texto: str) -> tuple[str, str]:
    encontrado = _PADRAO_MUNICIPIO_UF.search(texto)
    if not encontrado:
        raise FrameInvalidoError(f"Formato de município/UF inesperado: {texto!r}")
    return encontrado.group("municipio"), encontrado.group("uf")


def _extrair_estudantes(texto: str) -> tuple[int, int]:
    encontrado = _PADRAO_ESTUDANTES.search(texto)
    if not encontrado:
        raise FrameInvalidoError(f"Formato de número de estudantes inesperado: {texto!r}")
    return int(encontrado.group("quantidade")), int(encontrado.group("ano_censo"))


def _extrair_velocidade_adequada(texto: str) -> float:
    encontrado = _PADRAO_VELOCIDADE_ADEQUADA.search(texto)
    if not encontrado:
        raise FrameInvalidoError(f"Formato de velocidade adequada inesperado: {texto!r}")
    return _numero_pt_br(encontrado.group("valor"))


def _extrair_lista(texto: str) -> tuple[str, ...]:
    return tuple(nome.strip() for nome in texto.split(",") if nome.strip())
