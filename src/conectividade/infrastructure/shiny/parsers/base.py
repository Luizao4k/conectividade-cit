"""
Interface comum a todos os parsers especializados.

Um `ParserDeFrame` sabe responder duas perguntas: "esse conjunto de
chaves é comigo?" (`reconhece`) e, se for, "converta para o DTO
correspondente" (`parse`). O `RoteadorDeFrames` não conhece nenhum
parser específico — só itera essa interface. Isso é o que permite
adicionar um novo tipo de frame (ex.: um dia o portal passar a enviar
histórico de medições) criando só uma classe nova, sem tocar no roteador.
"""
from __future__ import annotations

from typing import Protocol, TypeVar

T_co = TypeVar("T_co", covariant=True)


class ParserDeFrame(Protocol[T_co]):
    def reconhece(self, valores: dict[str, object]) -> bool:
        """Retorna True se este parser sabe processar este conjunto de chaves."""
        print(valores.keys())
        return True
        ...

    def parse(self, valores: dict[str, object]) -> T_co:
        """Converte os valores brutos no DTO correspondente.

        Só deve ser chamado quando `reconhece(valores)` for True.
        """
        ...
