import playlist

# Nossa biblioteca que esta nomeada como sd e sf
import os
import time
import sounddevice as sd
import soundfile as sf
escolha = ""

def limpar_terminal():
    os.system('cls' if os.name == 'nt' else 'clear')

while escolha != "0":
    limpar_terminal()
    # interface do cliente
    print(" =========== SPOTCIN ===========")
    print(" [1] Natal")
    print(" [2] Hit de carnaval 2027 (bem provavel)")
    print(" [3] Zelda")
    print(" [0] Sair ")
    escolha = input(" Escolha uma opção: ")

    if escolha == "0":
        limpar_terminal()
        print("até logo!!\n")
        time.sleep(2)
        limpar_terminal()
        exit()

    # retorna o nas variaveis a musica que o usuario pediu (ele vai la na funcao)
    titulo, caminho = playlist.escolher_musica(escolha)

    if caminho:
        limpar_terminal()
        print(f" --- Tocando agora: {titulo} --- \n")
        dados, samplerate = sf.read(caminho)
        sd.play(dados, samplerate)
        print("Pressione ENTER a qualquer momento para parar a música.")
        input()

        sd.stop()
        print(" --- Áudio encerrado! --- \n")
        time.sleep(1)
    else:
        print("\n --- Opção inválida! Tente novamente --- \n")
        time.sleep(2)

