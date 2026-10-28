import sounddevice as sd

# Catálogo de músicas: chave = opção do menu, valor = (título, arquivo).
# Usar tupla em vez de dict interno evita redundância ("titulo", "caminho_arquivo")
# e deixa o dict curto e escaneável.
biblioteca_musicas = {
    "1": ("Natal", "Natal.wav"),
    "2": ("Hit de carnaval 2027 (bem provavel)", "Celular.wav"),
    "3": ("Zelda", "Sample.wav"),
}


def escolher_musica(user_escolha):
    """
    Retorna (titulo, arquivo) ou (None, None) se a opção for inválida.
    Usa .get() para cobrir os dois casos sem if extra.
    """
    return biblioteca_musicas.get(user_escolha, (None, None))


def iniciar_reproducao(buffer, formato):
    """
    Cria e inicia um stream de áudio que consome do buffer.

    O sounddevice chama `callback` sozinho em uma thread própria,
    pedindo `frames` frames a cada vez. Nunca devemos bloquear aqui
    (por isso `buffer.ler` é non-blocking: se não tem dado, devolve menos).
    """

    # Quantos bytes formam 1 frame (1 amostra de todos os canais juntos).
    # Ex.: estéreo 16-bit → 2 canais * 2 bytes = 4 bytes por frame.
    bytes_por_frame = formato["canais"] * formato["bytes_amostra"]

    # Valor que representa silêncio no formato:
    # - uint8 é unsigned, então 0 seria o mínimo negativo; 128 é o "zero".
    # - int16/int24/int32/float32 usam 0 como centro.
    silencio = b"\x80" if formato["bytes_amostra"] == 1 else b"\x00"

    def callback(outdata, frames, _time_info, _status):
        n = frames * bytes_por_frame
        dados = buffer.ler(n)

        # Se o buffer devolveu menos que o pedido, completa com silêncio.
        # Isso acontece no começo (antes do buffer encher) e no fim (último frame).
        if len(dados) < n:
            dados += silencio * (n - len(dados))

            # Se a rede já acabou e o buffer esvaziou, para o stream.
            if buffer.terminou():
                outdata[:] = dados
                raise sd.CallbackStop  # exceção usada pelo sounddevice pra encerrar

        outdata[:] = dados

    stream = sd.RawOutputStream(
        samplerate=formato["taxa_amostragem"],
        channels=formato["canais"],
        dtype=formato["dtype"],
        callback=callback,
    )
    stream.start()
    return stream