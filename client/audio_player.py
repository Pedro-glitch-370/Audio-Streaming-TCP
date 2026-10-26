'''
Consumir os dados do playback_buffer e
enviar eles pra placa de som usando a biblioteca de áudio escolhida
'''

import sounddevice as sd
import soundfile as sf

biblioteca_musicas = {
    "track_01": {
        "titulo": "Natal",
        "caminho_arquivo": "client/spotcin/Natal.wav"
    },
    "track_02": {
        "titulo": "Celular",
        "caminho_arquivo": "client/spotcin/Celular.wav"
    }
}

musica_selecionada = biblioteca_musicas["track_02"]

if musica_selecionada["titulo"] == "Natal":

    print("Você está ouvindo: All i want for christmas is you (mc poze)")
    caminho = musica_selecionada["caminho_arquivo"]
    dados, samplerate = sf.read('client/spotcin/Natal.wav')

elif musica_selecionada["titulo"] == "Celular":

    print("Você está ouvindo: Animadinhos: Celular")
    caminho = musica_selecionada["caminho_arquivo"]
    dados, samplerate = sf.read('client/spotcin/Celular.wav')


sd.play(dados, samplerate)
sd.wait()
exit()