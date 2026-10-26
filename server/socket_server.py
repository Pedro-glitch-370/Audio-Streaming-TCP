import json
import socket
import threading

from config import (
    DEFAULT_AUDIO, HANDSHAKE_TIMEOUT, HOST, MAX_CLIENTS, PORT, SEND_TIMEOUT,
)
from server import stream_handler

#controle de conexões
vagas_clientes = threading.BoundedSemaphore(MAX_CLIENTS) #controla o número máximo de usuários simultâneos, talvez n precise no futuro
server_evento_stop = threading.Event() #sinaliza quando o server tem q parar de rodar, talvez n precise no futuror

#função que converte um dict de Python em uma string JSON (ou seja, deixa em bytes);
#ela faz isso com codificação UTF-8 e também adiciona uma quebra de linha no final;
#a quebra de linha é importante porque as mensagens de texto são enviadas em linhas únicas;
#aí, dessa forma, o cliente vai saber onde a mensagem JSON termina
def _enviar_linha_json(conn: socket.socket, payload: dict):
    conn.sendall(json.dumps(payload).encode("utf-8") + b"\n")

#função pra tratar o cliente aceito, chamada logo dps que se cria uma thread dedicada pro cliente
def handle_client(conn: socket.socket, addr):
    tag = f"[{addr[0]}:{addr[1]}]" #essa tag é o IP do clinete mais a porta usada por ele
    print(f"{tag} conectado")

    try:
        #seta os tempos limites pro cliente enviar seu comando e pro envio de dados pesados
        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        conn.settimeout(HANDSHAKE_TIMEOUT)

        #lê a primeira linha enviada pelo cliente (q vai ser LIST ou PLAY arquivo.wav)
        requisicao = conn.makefile("rb").readline(1024).decode("utf-8", "replace").strip()
        
        #ajusta o timeout pro envio contínuo de dados pesados
        conn.settimeout(SEND_TIMEOUT)

        comando, _, argumento = requisicao.partition(" ")
        comando = comando.upper()

        if comando == "LIST":
            #retorna a lista de arquivos disponíveis em formato JSON
            files = stream_handler.listar_arquivos_audio()
            _enviar_linha_json(conn, {"status": "ok", "files": files})

        elif comando == "PLAY":
            #processa o pedido de streaming do arquivo, preparando o cliente pra receber o áudio
            nome_arquivo = argumento.strip() or DEFAULT_AUDIO #podemos tirar o default audio dps
            path = stream_handler.obter_caminho_arquivo(nome_arquivo) #procura o arquivo na pasta de áudios

            if path is None:
                _enviar_linha_json(conn, {"status": "error", "message": f"Arquivo não encontrado: {nome_arquivo}"})
                return

            info = stream_handler.obter_info_streaming(path) #lê as informações do áudio
            _enviar_linha_json(conn, {"status": "ok", **info}) #envia via JSON pro cliente
            print(f"{tag} recebendo {path.name}")

            bytes_enviados = stream_handler.enviar_arquivo_streaming(conn, path, info["taxa_bytes"], server_evento_stop) #nicia a transmissão fatiada do arquivo
            status = "concluída" if bytes_enviados == info["tamanho"] else "interrompida"
            print(f"{tag} transmissão {status}, {bytes_enviados} bytes")

        else:
            _enviar_linha_json(conn, {"status": "error", "message": "Comando inválido. Use LIST ou PLAY <arquivo>"})

    except (BrokenPipeError, ConnectionResetError, socket.timeout):
        print(f"{tag} desconectou ou ficou inativo")
    except Exception as e:
        print(f"{tag} erro: {e!r}")
    finally:
        try:
            conn.close() #fecha a conexão do cliente
        finally:
            vagas_clientes.release() #abre a vaga no servidor de novo
        print(f"{tag} encerrado")


def rodar_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #socket principal do servidor
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) #permite um socket se associar a uma porta em uso por outro socket
    server.bind((HOST, PORT)) #o bind amarra o IP e a porta (definidos no config.py) ao server
    server.listen(socket.SOMAXCONN) #o listen coloca o servidor em modo de espera, pronto para aceitar conexões
    server.settimeout(1.0) #permite checar o encerramento de tempo em tempo

    print(f"Server escutando em {HOST}:{PORT}.")

    try: #loop infinito aguardando novos clientes
        while not server_evento_stop.is_set():
            try:
                conn, addr = server.accept() #um cliente se conecta e o código retorna um canal exclusivo (conn) e o IP do client (addr)
            except socket.timeout:
                continue
            except OSError:
                break

            if not vagas_clientes.acquire(blocking=False): #tenta arranjar uma vaga no servidor pro cliente
                try:
                    _enviar_linha_json(conn, {"status": "error", "message": "Servidor lotado"})
                except OSError:
                    pass
                conn.close() #fecha a conexão do cliente
                print(f"[{addr[0]}:{addr[1]}] recusado: servidor lotado")
                continue

            #tem vaga, aí cria uma thread dedicada pro cliente
            t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            t.start()

    except KeyboardInterrupt: #ctr c pra fechar fácil
        print("\nServidor encerrado pelo usuário")

    finally:
        server_evento_stop.set() #faz o loop principal pra parar
        server.close() #fecha o socket do servidor, mas n acho que precisa pq n é uma boa prática
        print("Servidor desligado")

if __name__ == "__main__":
    rodar_server()