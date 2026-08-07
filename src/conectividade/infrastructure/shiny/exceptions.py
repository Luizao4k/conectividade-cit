class FrameInvalidoError(Exception):
    """
    Levantada quando um frame do Shiny tem um formato inesperado dentro
    das chaves que um parser já reconheceu (ex.: um valor que deveria ser
    string veio como número, ou um texto não bate com o padrão esperado).

    É um erro de infraestrutura (formato do portal mudou ou é inesperado),
    não um erro de domínio.
    """
