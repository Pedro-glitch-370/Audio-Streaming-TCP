'''
Usar aqui programação concorrente (como asyncio ou threading)
pra aceitar vários clientes simultaneamente de forma isolada
'''

import os
import socket
import sys
import time

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)

from config import HOST, PORT, BUFFER_SIZE, AUDIO_PATH

def run_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #cria uma interface socket por IPv4
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) #permite um socket se associar a uma porta em uso por outro socket
    server_socket.bind((HOST, PORT)) #o bind amarra o IP e a porta (definidos no config.py) ao server
    server_socket.listen(1) #o listen coloca o servidor em modo de espera, pronto para aceitar conexões
    #aqui, o server só aceita 1 cliente por vez, mas no futuro vamo ter que ampliar
    
    print(f"Servidor escutando em {HOST}:{PORT}.")
    #o código vai travar nessa linha de baixo até que um cliente se conecte
    conn, addr = server_socket.accept() #um cliente se conecta e o código retorna um canal exclusivo (conn) e o IP do client (addr)
    print(f"Conexão estabelecida com {addr}")
    
    try:
        with open(AUDIO_PATH, "rb") as f: #rb abre o arquivo de áudio em modo de leitura binária
            while True: #aqui o arquivo é lido pedaço por pedaço
                chunk = f.read(BUFFER_SIZE) #tamanho de cada pedaço
                if not chunk:
                    break
                conn.sendall(chunk) #garante que o bloco todo seja enviado de forma confiável pela rede TCP
                time.sleep(0.01) #esse atraso aqui é opcional, só pra simular a taxa de fluxo
        print("Transmissão do arquivo concluída com sucesso.")
    except Exception as e:
        print(f"Erro na transmissão: {e}")
    finally: #garante que a conexão com o cliente e o socket principal sejam fechados corretamente
        conn.close()
        server_socket.close()
        print("Conexão encerrada.")

if __name__ == "__main__":
    run_server()