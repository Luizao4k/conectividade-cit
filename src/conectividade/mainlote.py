"""
Teste de consulta em lote utilizando Shiny.$values.

Objetivo:
    Validar consultas sequenciais de INEPs sem reutilizar os dados
    da consulta anterior.

Este arquivo é um teste de integração/debug.
"""

from __future__ import annotations

import time
from typing import Any

from conectividade.infrastructure.browser.browser import Browser


# ============================================================
# CONFIGURAÇÃO
# ============================================================

INEPS = [
    "15588831",
    "15588610",
    "15588599",
    "15588378",
    "15587916",
    "15587894",
    "15587886",
    "15587878",
    "15587711",
    "15587282"
]

URL_PORTAL = (
    "https://conectividadenaeducacao.nic.br/#sua-escola"
)

TIMEOUT_SHINY = 90.0

# Tempo máximo aguardando a resposta de uma escola.
TIMEOUT_RESPOSTA = 60.0

# Intervalo entre as verificações.
INTERVALO = 0.5

# Tempo que os dados precisam permanecer iguais
# antes de serem considerados estabilizados.
TEMPO_ESTABILIZACAO = 5.0


# ============================================================
# CAMPOS
# ============================================================

CAMPOS_ESPERADOS = (
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


# ============================================================
# NORMALIZAÇÃO
# ============================================================

def normalizar_valor(valor: Any) -> Any:
    """
    Extrai o conteúdo HTML dos valores reativos do Shiny.
    """

    if isinstance(valor, dict):

        if "html" in valor:
            return valor["html"]

        return valor

    return valor


# ============================================================
# LEITURA DO SHINY
# ============================================================

def ler_values(page) -> dict[str, Any]:
    """
    Lê Shiny.shinyapp.$values.

    Durante uma reação do Shiny o contexto JavaScript pode
    ser destruído temporariamente. Nesse caso retorna {}.
    """

    try:

        valores = page.evaluate(
            """
            () => {
                return window.Shiny
                    ?.shinyapp
                    ?.$values ?? {};
            }
            """
        )

    except Exception as exc:

        if "Execution context was destroyed" in str(exc):
            return {}

        raise

    if not isinstance(valores, dict):
        return {}

    return valores


def ler_input_inep(page) -> str:
    """
    Retorna o INEP atualmente registrado pelo Shiny.
    """

    try:

        valor = page.evaluate(
            """
            () => {
                return window.Shiny
                    ?.shinyapp
                    ?.$inputValues
                    ?.inep_plano ?? "";
            }
            """
        )

    except Exception as exc:

        if "Execution context was destroyed" in str(exc):
            return ""

        raise

    return str(valor)


def ler_input_shiny(page) -> str:
    """
    Alias explícito para leitura do INEP no runtime Shiny.
    """

    return ler_input_inep(page)


# ============================================================
# CONEXÃO SHINY
# ============================================================

def shiny_conectado(page) -> bool:
    """
    Verifica se o WebSocket do Shiny está conectado.
    """

    try:

        estado = page.evaluate(
            """
            () => ({
                shiny: !!window.Shiny,

                app: !!window.Shiny?.shinyapp,

                socket:
                    window.Shiny
                        ?.shinyapp
                        ?.$socket
                        ?.readyState ?? null
            })
            """
        )

    except Exception as exc:

        if "Execution context was destroyed" in str(exc):
            return False

        raise

    return bool(
        estado["shiny"]
        and estado["app"]
        and estado["socket"] == 1
    )


def aguardar_shiny(page) -> None:
    """
    Aguarda o estabelecimento da conexão do Shiny.
    """

    print("\nAguardando conexão do Shiny...")

    inicio = time.monotonic()

    while time.monotonic() - inicio < TIMEOUT_SHINY:

        if shiny_conectado(page):

            print("[OK] Shiny conectado.")

            return

        page.wait_for_timeout(
            int(INTERVALO * 1000)
        )

    raise TimeoutError(
        f"Shiny não conectou em "
        f"{TIMEOUT_SHINY:.0f} segundos."
    )


# ============================================================
# ENVIO DO INEP
# ============================================================

def enviar_inep(page, inep: str) -> None:
    """
    Envia o INEP para o input do Shiny e confirma
    que o runtime recebeu o valor.
    """

    print(f"\nEnviando INEP: {inep}")

    campo = page.locator("#inep_plano")

    campo.wait_for(
        state="visible",
        timeout=10_000,
    )

    campo.fill(inep)

    page.evaluate(
        """
        (inep) => {

            Shiny.setInputValue(
                "inep_plano",
                inep,
                {
                    priority: "event"
                }
            );
        }
        """,
        inep,
    )

    inicio = time.monotonic()

    while time.monotonic() - inicio < 10:

        try:

            dom = campo.input_value()

            shiny = ler_input_shiny(page)

            socket = page.evaluate(
                """
                () => window.Shiny
                    ?.shinyapp
                    ?.$socket
                    ?.readyState ?? null
                """
            )

        except Exception as exc:

            if "Execution context was destroyed" in str(exc):

                page.wait_for_timeout(200)

                continue

            raise

        if dom == inep and shiny == inep:

            print(
                "[INPUT]",
                {
                    "dom": dom,
                    "shiny": shiny,
                    "socket": socket,
                },
            )

            return

        page.wait_for_timeout(200)

    raise TimeoutError(
        f"Shiny não confirmou o INEP {inep}."
    )


# ============================================================
# ASSINATURA DOS DADOS
# ============================================================

def obter_assinatura_escola(
    valores: dict[str, Any],
) -> tuple[Any, ...]:
    """
    Cria uma assinatura somente com os dados relevantes
    da escola.

    A assinatura é utilizada para descobrir se os dados
    retornados pelo portal realmente mudaram.
    """

    return tuple(
        normalizar_valor(
            valores.get(campo)
        )
        for campo in (
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
    )


# ============================================================
# DADOS VÁLIDOS
# ============================================================

def dados_validos(
    valores: dict[str, Any],
) -> bool:
    """
    Verifica se já existe um nome de escola válido.
    """

    nome = normalizar_valor(
        valores.get("nome_escola")
    )

    if not isinstance(nome, str):
        return False

    return bool(nome.strip())


# ============================================================
# INEP NÃO ENCONTRADO
# ============================================================

def inep_nao_encontrado(page) -> bool:
    """
    Detecta a mensagem apresentada pelo portal quando
    o INEP não é reconhecido.
    """

    try:

        texto = page.locator(
            "body"
        ).inner_text(
            timeout=1000
        )

    except Exception as exc:

        if "Execution context was destroyed" in str(exc):
            return False

        return False

    return (
        "O INEP digitado não foi reconhecido"
        in texto
    )


# ============================================================
# AGUARDAR RESPOSTA
# ============================================================

def aguardar_resposta(
    page,
    inep: str,
    assinatura_anterior: tuple[Any, ...] | None,
) -> tuple[str, dict[str, Any]]:
    """
    Aguarda a resposta do portal para o INEP.

    Estratégia:

    1. Confirma que o novo INEP foi enviado.
    2. Aguarda o portal começar a processar.
    3. Verifica se o INEP não existe.
    4. Aguarda os dados anteriores desaparecerem
       ou serem substituídos.
    5. Detecta uma nova assinatura.
    6. Aguarda os dados permanecerem estáveis por
       TEMPO_ESTABILIZACAO segundos.
    7. Retorna somente os dados estabilizados.
    """

    print(
        "\nAguardando resposta do portal..."
    )

    inicio = time.monotonic()

    nova_assinatura: tuple[Any, ...] | None = None

    valores_finais: dict[str, Any] | None = None

    inicio_estabilidade: float | None = None

    mostrou_processamento = False

    mostrou_limpeza = False

    mostrou_novos_dados = False

    while (
        time.monotonic() - inicio
        < TIMEOUT_RESPOSTA
    ):

        # ====================================================
        # 1. Verifica INEP inexistente
        # ====================================================

        if inep_nao_encontrado(page):

            print(
                "[OK] Portal informou que o INEP "
                "não foi encontrado."
            )

            return "nao_encontrado", {}

        # ====================================================
        # 2. Confirma INEP atual no Shiny
        # ====================================================

        input_atual = ler_input_shiny(page)

        if input_atual != inep:

            page.wait_for_timeout(
                int(INTERVALO * 1000)
            )

            continue

        # ====================================================
        # 3. Mensagem de processamento
        # ====================================================

        if not mostrou_processamento:

            print(
                "[AGUARDANDO] "
                "Portal processando o novo INEP..."
            )

            mostrou_processamento = True

        # ====================================================
        # 4. Lê os valores atuais
        # ====================================================

        valores = ler_values(page)

        if not valores:

            page.wait_for_timeout(
                int(INTERVALO * 1000)
            )

            continue

        assinatura_atual = (
            obter_assinatura_escola(
                valores
            )
        )

        # ====================================================
        # 5. Ainda não existem dados de escola
        # ====================================================

        if not dados_validos(valores):

            if not mostrou_limpeza:

                print(
                    "[AGUARDANDO] "
                    "Dados anteriores foram limpos."
                )

                mostrou_limpeza = True

            page.wait_for_timeout(
                int(INTERVALO * 1000)
            )

            continue

        # ====================================================
        # 6. PRIMEIRA CONSULTA
        # ====================================================

        if assinatura_anterior is None:

            if not mostrou_novos_dados:

                print(
                    "[AGUARDANDO] "
                    "Primeiros dados recebidos..."
                )

                mostrou_novos_dados = True

            if (
                nova_assinatura is None
                or assinatura_atual != nova_assinatura
            ):

                nova_assinatura = (
                    assinatura_atual
                )

                valores_finais = valores

                inicio_estabilidade = (
                    time.monotonic()
                )

                print(
                    "[AGUARDANDO] "
                    "Dados ainda estão sendo carregados..."
                )

            else:

                assert inicio_estabilidade is not None

                tempo_estavel = (
                    time.monotonic()
                    - inicio_estabilidade
                )

                if (
                    tempo_estavel
                    >= TEMPO_ESTABILIZACAO
                ):

                    print(
                        "[OK] "
                        "Dados da escola carregados "
                        "e estabilizados em "
                        "Shiny.$values."
                    )

                    assert valores_finais is not None

                    return (
                        "sucesso",
                        valores_finais,
                    )

            page.wait_for_timeout(
                int(INTERVALO * 1000)
            )

            continue

        # ====================================================
        # 7. CONSULTAS SEGUINTES
        # ====================================================

        # Enquanto os dados forem exatamente iguais aos
        # da consulta anterior, ainda não temos uma nova
        # resposta.

        if (
            assinatura_atual
            == assinatura_anterior
        ):

            if not mostrou_limpeza:

                print(
                    "[AGUARDANDO] "
                    "Dados anteriores ainda presentes."
                )

                mostrou_limpeza = True

            page.wait_for_timeout(
                int(INTERVALO * 1000)
            )

            continue

        # ====================================================
        # 8. NOVOS DADOS DETECTADOS
        # ====================================================

        if (
            nova_assinatura is None
            or assinatura_atual != nova_assinatura
        ):

            nova_assinatura = (
                assinatura_atual
            )

            valores_finais = valores

            inicio_estabilidade = (
                time.monotonic()
            )

            if not mostrou_novos_dados:

                print(
                    "[OK] Novos dados detectados."
                )

                print(
                    "[AGUARDANDO] "
                    "Carregando dados da escola..."
                )

                mostrou_novos_dados = True

            else:

                print(
                    "[AGUARDANDO] "
                    "Portal ainda atualizando os dados..."
                )

            page.wait_for_timeout(
                int(INTERVALO * 1000)
            )

            continue

        # ====================================================
        # 9. NOVOS DADOS PERMANECEM IGUAIS
        # ====================================================

        assert inicio_estabilidade is not None

        assert valores_finais is not None

        tempo_estavel = (
            time.monotonic()
            - inicio_estabilidade
        )

        if (
            tempo_estavel
            >= TEMPO_ESTABILIZACAO
        ):

            print(
                "[OK] "
                "Dados da escola carregados "
                "e estabilizados em "
                "Shiny.$values."
            )

            return (
                "sucesso",
                valores_finais,
            )

        page.wait_for_timeout(
            int(INTERVALO * 1000)
        )

    # ========================================================
    # TIMEOUT
    # ========================================================

    print(
        "[TIMEOUT] "
        "O portal não apresentou uma resposta válida "
        f"para o INEP {inep}."
    )

    return "timeout", {}


# ============================================================
# EXTRAÇÃO
# ============================================================

def extrair_dados(
    valores: dict[str, Any],
) -> dict[str, Any]:
    """
    Extrai os campos relevantes da escola.
    """

    return {
        campo: normalizar_valor(
            valores.get(campo)
        )
        for campo in CAMPOS_ESPERADOS
    }


# ============================================================
# SAÍDA
# ============================================================

def imprimir_resultado(
    inep: str,
    status: str,
    dados: dict[str, Any],
    tempo: float,
) -> None:
    """
    Exibe o resultado de uma consulta.
    """

    print(
        "\n" + "=" * 80
    )

    print(
        f"INEP: {inep}"
    )

    print(
        f"Status: {status}"
    )

    if status == "sucesso":

        print(
            f"Escola: "
            f"{dados.get('nome_escola')}"
        )

        print(
            f"Local: "
            f"{dados.get('uf_escola')}"
        )

        print(
            f"Gestão: "
            f"{dados.get('dependencia_escola')}"
        )

        print(
            f"Velocidade adequada: "
            f"{dados.get('vel_adequada')}"
        )

        print(
            f"Status medidor: "
            f"{dados.get('status_medidor')}"
        )

        print(
            f"Download: "
            f"{dados.get('vel_download')}"
        )

        print(
            f"Upload: "
            f"{dados.get('vel_upload')}"
        )

        print(
            f"Latência: "
            f"{dados.get('latencia')}"
        )

        print(
            f"Jitter: "
            f"{dados.get('jitter')}"
        )

        print(
            f"Perda de pacotes: "
            f"{dados.get('perda_pacote')}"
        )

        print(
            f"Medições: "
            f"{dados.get('nro_medicoes')}"
        )

    print(
        f"Tempo: {tempo:.2f}s"
    )

    print(
        "=" * 80
    )


# ============================================================
# CONSULTA INDIVIDUAL
# ============================================================

def consultar(
    page,
    inep: str,
    assinatura_anterior: tuple[Any, ...] | None,
) -> tuple[
    str,
    dict[str, Any],
    float,
]:
    """
    Executa uma consulta individual.
    """

    inicio = time.monotonic()

    enviar_inep(
        page,
        inep,
    )

    status, valores = aguardar_resposta(
        page,
        inep,
        assinatura_anterior,
    )

    tempo = (
        time.monotonic()
        - inicio
    )

    dados = extrair_dados(
        valores
    )

    return (
        status,
        dados,
        tempo,
    )


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    """
    Executa o teste de consulta em lote.
    """

    print(
        "=== TESTE DE CONSULTA EM LOTE ==="
    )

    print(
        f"Quantidade de INEPs: {len(INEPS)}"
    )

    resultados = []

    assinatura_anterior = None

    with Browser(
        url_portal=URL_PORTAL,
        headless=False,
    ) as browser:

        print("\nChrome aberto.")

        print(
            "Configure o proxy manualmente "
            "(caso necessário)."
        )

        input(
            "Pressione ENTER após configurar "
            "o proxy/carregar a página..."
        )

        page = browser.page

        print(
            "\nURL atual:",
            page.url,
        )

        # ====================================================
        # ABRIR PORTAL
        # ====================================================

        if (
            "conectividadenaeducacao.nic.br"
            not in page.url
        ):

            print(
                "\nAbrindo portal..."
            )

            page.goto(
                URL_PORTAL,
                wait_until="domcontentloaded",
                timeout=120_000,
            )

        # ====================================================
        # AGUARDAR SHINY
        # ====================================================

        aguardar_shiny(page)

        # ====================================================
        # LOTE
        # ====================================================

        for indice, inep in enumerate(
            INEPS,
            start=1,
        ):

            print("\n")

            print(
                "#" * 80
            )

            print(
                f"CONSULTA "
                f"{indice}/{len(INEPS)}"
            )

            print(
                f"INEP: {inep}"
            )

            print(
                "#" * 80
            )

            status, dados, tempo = consultar(
                page,
                inep,
                assinatura_anterior,
            )

            imprimir_resultado(
                inep,
                status,
                dados,
                tempo,
            )

            # =================================================
            # ATUALIZA ASSINATURA
            # =================================================

            if status == "sucesso":

                assinatura_anterior = (
                    obter_assinatura_escola(
                        dados
                    )
                )

            resultados.append(
                {
                    "inep": inep,
                    "status": status,
                    "tempo": tempo,
                }
            )

        # ====================================================
        # RESUMO
        # ====================================================

        total = len(
            resultados
        )

        sucessos = sum(
            resultado["status"]
            == "sucesso"
            for resultado in resultados
        )

        nao_encontrados = sum(
            resultado["status"]
            == "nao_encontrado"
            for resultado in resultados
        )

        timeouts = sum(
            resultado["status"]
            == "timeout"
            for resultado in resultados
        )

        print("\n")

        print(
            "=" * 80
        )

        print(
            "RESUMO DO LOTE"
        )

        print(
            "=" * 80
        )

        print(
            f"Total:           {total}"
        )

        print(
            f"Sucesso:         {sucessos}"
        )

        print(
            f"Não encontrado:  {nao_encontrados}"
        )

        print(
            f"Timeout:         {timeouts}"
        )

        print(
            "=" * 80
        )

        print(
            "\nRESULTADOS:"
        )

        for resultado in resultados:

            print(
                f"  {resultado['inep']} "
                f"-> {resultado['status']}"
            )

        input(
            "\nPressione ENTER para fechar "
            "o navegador..."
        )


if __name__ == "__main__":
    main()
