import os
import time
import playlist
import socket_client
from playback_buffer import aguardar_prebuffer
escolha = ""

#função que usa comandos do sistema operacional pra limpar a tela
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

    if escolha == "0": #botão de exit
        limpar_terminal()
        print("Até logo!!\n")
        time.sleep(2)
        limpar_terminal()
        exit()

    #seleção da música;
    #o usuario escolhe sua opção e o código envia ela pra playlist;
    #o que é retornado é o título da música e o caminho do arquivo
    titulo, caminho = playlist.escolher_musica(escolha)

    if caminho: #opção escolhida é válida
        limpar_terminal()
        print(f" --- Tocando agora: {titulo} --- \n")

        sessao = None
        reproducao = None
        
        try:
            # pede a música ao servidor e começa a baixar os blocos em uma thread separada
            sessao = socket_client.iniciar_streaming(caminho) #se conecta ao server via socket
            print(" Carregando buffer...")
            aguardar_prebuffer(sessao["buffer"]) # só começa a tocar depois de acumular o pré-buffer
            if sessao["get_erro"]():
                raise RuntimeError(sessao["get_erro"]())

            #o player de áudio começa a tocar os dados recebidos diretamente do buffer
            reproducao = playlist.iniciar_reproducao(sessao["buffer"], sessao["formato"])
            print("Pressione ENTER a qualquer momento para parar a música.")
            input() #esse input trava o loop principal e deixa a música tocando até o enter ser pressionado

            if sessao["get_erro"]:
                print(f" --- Transmissão interrompida: {sessao["get_erro"]} --- \n")
            print(" --- Áudio encerrado! --- \n")

        except (OSError, RuntimeError, ValueError) as e:
            print(f"\n --- Erro: {e} --- \n")

        finally: 
            if reproducao:
                reproducao.stop() #fecha os recursos de áudio
                reproducao.close() #fecha a sessão de rede
            if sessao:
                sessao["parar"]() # avisa o servidor que o cliente saiu
        time.sleep(1)

    else: #opção escolhida é inválida
        print("\n --- Opção inválida! Tente novamente --- \n")
        time.sleep(2)

