import queue
import threading

#função que cria um dict com a estrutura de estado do buffer;
#ela usa uma fila segura pra multithreading
def criar_buffer(bytes_prebuffer: int):
    return {
        "fila": queue.Queue(), #a thread da rede joga os pedaços de áudio nessa fila e depois a thread de som tira
        "sobra": bytearray(), #guarda pedaços de áudio que sobraram de leituras anteriores
        "bytes_prebuffer": bytes_prebuffer,
        "recebido": 0,
        "pronto": threading.Event(), #sinal de sincronização
        "fim": threading.Event(), #sinal de sincronização
    }

#função chamada pela thread da rede a cada bloco que é baixado e recebido
def adicionar_chunk(buffer: dict, chunk: bytes):
    buffer["fila"].put(chunk) #guarda o bloco na fila
    buffer["recebido"] += len(chunk) #soma o tamanho total recebido
    if buffer["recebido"] >= buffer["bytes_prebuffer"]: #condição quando o volume atinge o limite seguro
        buffer["pronto"].set() #aciona um evento que libera o player pra tocar sem engasgo

#função chamada quando a música acaba ou quando a conexão cai
def finalizar_buffer(buffer: dict):
    buffer["fim"].set()
    buffer["pronto"].set() #pra evitar que o player n trave e espere pra sempre

#função que trava o programa principal no início do áudio até que o pré-buffer fiqu cheio
def aguardar_prebuffer(buffer: dict, timeout=None):
    return buffer["pronto"].wait(timeout) #dps disso, a reprodução começa

#função chamada pelo player de audio, que vai pegando sempre os próximos n_bytes do som
def ler_buffer(buffer: dict, n_bytes: int):
    while len(buffer["sobra"]) < n_bytes:
        try:
            buffer["sobra"] += buffer["fila"].get_nowait()
        except queue.Empty:
            break
    dados = bytes(buffer["sobra"][:n_bytes])
    del buffer["sobra"][:n_bytes]
    return dados

#função booleana pro player saber que a música acabou de tocar por completo (true)
def buffer_terminou(buffer: dict):
    #a funçaõ checa respectivamente se a rede fechou, se a fila de blocos tá vazia e se não sobrou nenhum byte no bytearray
    return buffer["fim"].is_set() and buffer["fila"].empty() and not buffer["sobra"]