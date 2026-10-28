import os
import time

from client import playlist, socket_client

# Texto do menu em constante — evita prints espalhados e facilita mudar depois.
MENU = """ =========== SPOTCIN ===========
 [1] Natal
 [2] Hit de carnaval 2027 (bem provavel)
 [3] Zelda
 [0] Sair
"""


def limpar_terminal():
    """Limpa a tela em Windows (cls) e Unix (clear)."""
    os.system("cls" if os.name == "nt" else "clear")


def tocar_musica(caminho: str):
    """
    Faz o ciclo completo de uma música: conecta, espera pré-buffer,
    toca até ENTER, e garante o cleanup no finally.

    Isolar isso em uma função deixa o loop do menu curto e legível,
    e o finally cuida de parar/reprodução mesmo se algo der errado no meio.
    """
    sessao = socket_client.iniciar_streaming(caminho)
    reproducao = None  # ainda não criada — usada no finally

    try:
        print(" Carregando buffer...")
        sessao.buffer.aguardar_prebuffer()

        # Se a rede falhou antes do pré-buffer encher, aborta aqui.
        if sessao.get_erro():
            raise RuntimeError(sessao.get_erro())

        # Começa a tocar. A partir daqui a reprodução roda em thread própria
        # do sounddevice; este código só aguarda o ENTER.
        reproducao = playlist.iniciar_reproducao(sessao.buffer, sessao.formato)

        print(" Pressione ENTER a qualquer momento para parar a música.")
        input()  # bloqueia até o usuário apertar ENTER

        # Pode ter havido erro de rede durante a reprodução (não fatal).
        if sessao.get_erro():
            print(f" --- Transmissão interrompida: {sessao.get_erro()} --- \n")
        print(" --- Áudio encerrado! --- \n")

    finally:
        # Cleanup garantido: encerra o stream de áudio e avisa o servidor.
        if reproducao:
            reproducao.stop()
            reproducao.close()
        sessao.parar()


def main():
    """Loop principal do menu."""
    while True:
        limpar_terminal()
        print(MENU)
        escolha = input(" Escolha uma opção: ")

        if escolha == "0":
            limpar_terminal()
            print("Até logo!!\n")
            time.sleep(2)
            limpar_terminal()
            return  # sai de main (equivalente ao exit, mas testável)

        titulo, caminho = playlist.escolher_musica(escolha)
        if not caminho:
            print("\n --- Opção inválida! Tente novamente --- \n")
            time.sleep(2)
            continue  # volta pro topo do loop

        limpar_terminal()
        print(f" --- Tocando agora: {titulo} --- \n")

        # try/except aqui: qualquer falha de rede/áudio vira mensagem amigável
        # sem derrubar o menu.
        try:
            tocar_musica(caminho)
        except (OSError, RuntimeError, ValueError) as e:
            print(f"\n --- Erro: {e} --- \n")

        time.sleep(1)


# Só roda se o arquivo for executado diretamente — permite importar main
# em testes sem disparar o menu.
if __name__ == "__main__":
    main()