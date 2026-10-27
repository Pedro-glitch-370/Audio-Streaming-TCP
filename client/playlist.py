from pathlib import Path
from playback_buffer import ler_buffer, buffer_terminou
import sounddevice as sd

#dict com as músicas do menu;
#o "caminho_arquivo" é o nome do arquivo na pasta audio_files do server
biblioteca_musicas = {
    "1": {
        "titulo": "Natal",
        "caminho_arquivo": "./audio_files/Natal.wav"
    },
    "2": {
        "titulo": "Hit de carnaval 2027 (bem provavel)",
        "caminho_arquivo": "./audio_files/Celular.wav"
    },
    "3": {
        "titulo": "Zelda",
        "caminho_arquivo": "./audio_files/Sample.wav"
    }
}

def escolher_musica(user_escolha):
    titulo = ""
    caminho_completo = ""

    #verifica se na biblioteca_musicas há a musica que o usuario quer e guarda na variavel que é 
    #exportada para a main para a reproducao
    if user_escolha in biblioteca_musicas:
        titulo = biblioteca_musicas[user_escolha]["titulo"]
        caminho_completo = biblioteca_musicas[user_escolha]["caminho_arquivo"]
        caminho = Path(caminho_completo).name 
        return titulo, caminho
        
    # Retorna None caso o usuário escolha uma opção inválida
    return None, None

#toca o que for chegando no playback_buffer;
#devolve o stream pra main poder parar quando quiser
def iniciar_reproducao(buffer, formato):
    bytes_por_frame = formato["canais"] * formato["bytes_amostra"]
    silencio = b"\x80" if formato["bytes_amostra"] == 1 else b"\x00" #WAV de 8 bits usa 128 como silêncio

    #a placa de som chama essa função sozinha, de tempo em tempo, pedindo mais áudio
    def callback(outdata, frames, time_info, status):
        n = frames * bytes_por_frame
        dados = ler_buffer(buffer, n)
        if len(dados) < n:
            dados += silencio * (n - len(dados)) #faltou dado (rede lenta ou fim da música), completa com silêncio
            if buffer_terminou(buffer):
                outdata[:] = dados
                raise sd.CallbackStop #acabou a música, toca o último bloco e para
        outdata[:] = dados

    stream = sd.RawOutputStream(
        samplerate=formato["taxa_amostragem"],
        channels=formato["canais"],
        dtype=formato["dtype"],
        callback=callback,
    )
    stream.start()
    return stream
