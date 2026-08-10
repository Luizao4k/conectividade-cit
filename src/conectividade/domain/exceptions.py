class ConsultaEscolaError(Exception):
    """Erro base para qualquer falha ao consultar dados de uma escola."""


class EscolaNaoEncontradaError(ConsultaEscolaError):
    """Levantada quando nenhuma escola é encontrada para o INEP informado."""


class RespostaIncompletaError(ConsultaEscolaError):
    """Levantada quando o portal não envia os frames esperados dentro do timeout."""


class AplicacaoShinyEncerradaError(ConsultaEscolaError):
    """Levantada quando o servidor encerra a aplicação Shiny no meio da consulta
    (ex.: crash da aplicação, código de fechamento diferente de 1000)."""
