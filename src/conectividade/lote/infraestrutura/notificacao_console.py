"""Reporte de progresso do lote no console (saída interativa para o operador)."""
from __future__ import annotations

from conectividade.lote.dominio.resultado_consulta import ResultadoConsultaLote, StatusConsultaLote
from conectividade.lote.dominio.resumo_lote import ResumoLote

_ROTULOS_STATUS = {
    StatusConsultaLote.SUCESSO: "sucesso",
    StatusConsultaLote.NAO_ENCONTRADO: "não encontrado",
    StatusConsultaLote.TIMEOUT: "timeout",
    StatusConsultaLote.ERRO: "erro",
}


class NotificadorConsoleLote:
    """Implementação de `NotificadorProgressoLote` que imprime no console."""

    def __init__(self, arquivo_resultados: object) -> None:
        self._arquivo_resultados = arquivo_resultados

    def consulta_concluida(
        self,
        *,
        indice: int,
        total: int,
        resultado: ResultadoConsultaLote,
    ) -> None:
        print("\n" + "=" * 80)
        print(f"CONSULTA {indice}/{total}")
        print(f"INEP: {resultado.inep}")
        print(f"Status: {_ROTULOS_STATUS[resultado.status]}")

        if resultado.sucesso:
            dados = resultado.dados
            print(f"Escola: {dados.nome_escola}")
            print(f"Local: {dados.uf_escola}")
            print(f"Gestão: {dados.dependencia_escola}")
            print(f"Velocidade adequada: {dados.vel_adequada}")
            print(f"Status medidor: {dados.status_medidor}")
            print(f"Download: {dados.vel_download}")
            print(f"Upload: {dados.vel_upload}")
            print(f"Latência: {dados.latencia}")
            print(f"Jitter: {dados.jitter}")
            print(f"Perda de pacotes: {dados.perda_pacote}")
            print(f"Medições: {dados.nro_medicoes}")

        print(f"Tempo: {resultado.tempo_segundos:.2f}s")
        print("=" * 80)
        print(f"[SALVO] Resultado gravado em: {self._arquivo_resultados}")

    def resumo_final(self, resumo: ResumoLote) -> None:
        print("\n" + "=" * 80)
        print("RESUMO DA EXECUÇÃO")
        print("=" * 80)
        print(f"Processados:      {resumo.total_processado}")
        print(f"Sucesso:          {resumo.sucessos}")
        print(f"Não encontrado:   {resumo.nao_encontrados}")
        print(f"Timeout:          {resumo.timeouts}")
        print(f"Erros:            {resumo.erros}")
        print("=" * 80)
        print("\nResultados salvos em:")
        print(self._arquivo_resultados)
