'''
Manter aqui uma escuta contínua na porta TCP e
receber os blocos brutos de áudio enviados pelo server
'''

import os
import socket
import sys

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)

from config import HOST, PORT, BUFFER_SIZE

def run_client():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #cria o socket TCP do cliente
    client_socket.connect((HOST, PORT)) #se conecta ao IP e à porta onde o server tá escutando
    print(f"Conectado ao servidor em {HOST}:{PORT}")
    
    output_path = "audio_files/received_sample.wav" #tudo que chegar rede vai ser gravado em received_sample.wav
    
    try:
        with open(output_path, "wb") as f: #abre um arquivo local (received_sample.wav) em modo de escrita binária (wb)
            while True: 
                chunk = client_socket.recv(BUFFER_SIZE) #fica escutando a rede enquanto o server fica enviando os blocos
                if not chunk: #quando chunk vem vazio, o server cabou de enviar os pedaços
                    break
                f.write(chunk) #cada pedaço recebido é gravado no received_sample.wav
        print(f"Áudio recebido e salvo com sucesso em '{output_path}'.")
    except Exception as e:
        print(f"Erro ao receber dados: {e}")
    finally:
        client_socket.close() #fecha o socket do client

if __name__ == "__main__":
    run_client()