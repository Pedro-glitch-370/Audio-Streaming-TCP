import os
import time

from client import playlist, socket_client

# Texto do menu em constante — evita prints espalhados e facilita mudar depois.
def montar_menu(arquivos):
    """Monta o texto do menu a partir da lista de arquivos do servidor."""
    linhas = [" =========== SPOTCIN ==========="]
    for i, nome in enumerate(arquivos, start=1):
        linhas.append(f" [{i}] {nome}")
    linhas.append(" [0] Sair ")
    return "\n".join(linhas)


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
    # Descobre uma vez o que o servidor oferece (poderia ser a cada iteração)
    try:
        arquivos = socket_client.listar_arquivos()
    except (OSError, RuntimeError, ConnectionError) as e:
        print(f"\n --- Não foi possível conectar ao servidor: {e} --- \n")
        return

    if not arquivos:
        print("\n --- Servidor não tem nenhum áudio disponível --- \n")
        return

    menu = montar_menu(arquivos)

    while True:
        limpar_terminal()
        print(menu)
        escolha = input(" Escolha uma opção: ")

        if escolha == "0":
            limpar_terminal()
            print("Até logo!!\n")
            time.sleep(2)
            limpar_terminal()
            return

        # Valida: precisa ser número entre 1 e len(arquivos)
        try:
            idx = int(escolha)
        except ValueError:
            idx = -1

        if not (1 <= idx <= len(arquivos)):
            print("\n --- Opção inválida! Tente novamente --- \n")
            time.sleep(2)
            continue

        titulo = arquivos[idx - 1]        # nome do arquivo = "título" exibido
        caminho = arquivos[idx - 1]       # o que vai pro servidor no PLAY

        limpar_terminal()
        print(f" --- Tocando agora: {titulo} --- \n")

        try:
            tocar_musica(caminho)
        except KeyboardInterrupt:
            print("\n --- Interrompido pelo usuário --- \n")
        except (OSError, RuntimeError, ValueError) as e:
            print(f"\n --- Erro: {e} --- \n")

        time.sleep(1)


# Só roda se o arquivo for executado diretamente — permite importar main
# em testes sem disparar o menu.
if __name__ == "__main__":
    main()