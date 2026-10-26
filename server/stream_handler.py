import socket
import threading
import time
import wave
from pathlib import Path

from config import (
    DIRETORIO_AUDIO, TAMANHO_BUFFER, FALLBACK_BITRATE_KBPS,
    SEGUNDOS_PRE_BUFFER, EXTENSOES_SUPORTADAS,
)

#função pra listar os arquivos de áudio que tem no server
def listar_arquivos_audio():
    if not DIRETORIO_AUDIO.is_dir(): #essa pasta DIRETORIO_AUDIO vai ser percorrida
        return []
    return sorted(
        p.name for p in DIRETORIO_AUDIO.iterdir() #o que é retornado é uma lista ordenada com os nomes dos arquivos válidos
        if p.is_file()
        and p.suffix.lower() in EXTENSOES_SUPORTADAS #só arquivos .wav e .mp3 são listados
        and not p.name.startswith("received_") #não lista arquivos salvos sem querer pelo cliente, pode ser tirado futuramente qndo acertar os dois lados
    )

#função pra pegar o nome e o caminho do arquivo solicitado pelo cliente
def obter_caminho_arquivo(name: str):
    if not name:
        return None
    path = DIRETORIO_AUDIO / name #cria o caminho até o arquivo
    if path.suffix.lower() in EXTENSOES_SUPORTADAS and path.is_file():
        return path
    return None

#função pra calcular a taxa de transmissão de um arquivo (ou seja, quantos bytes por segundo o áudio consome);
#em arquivos .wav, essa taxa é dada pelo cabeçalho, mas em .mp3 não;
#por isso, tem que estimar a taxa nos casos de .mp3 
def obter_taxa_transmissao(path: Path):
    if path.suffix.lower() == ".wav": #caso de arquivo .wav
        try:
            with wave.open(str(path), "rb") as w: #lê o cabeçalho do arquivo usando a biblioteca wave
                rate = w.getframerate() * w.getnchannels() * w.getsampwidth() #frequência × canais × bytes por amostra
                if rate > 0:
                    return rate
        except (wave.Error, EOFError):
            pass
    return FALLBACK_BITRATE_KBPS * 1000 // 8 #caso de arquivo .mp3, usando um valor de segurança definido no config

#função que retorna as informações do arquivo em um dict;
#esse pacote é enviado via JSON pro cliente antes da música começar;
#assim ele sabe o que vai receber
def obter_info_streaming(path: Path):
    return {
        "nome_arquivo": path.name, #nome do arquivo
        "tamanho": path.stat().st_size, #tamanho total do arquivo
        "taxa_bytes": obter_taxa_transmissao(path), #taxa de bytes por segundo
        "tamanho_chunk": TAMANHO_BUFFER, #tamanho de cada bloco enviado
    }

#função pra enviar o arquivo em blocos
def enviar_arquivo_streaming(conn: socket.socket, path: Path, taxa_bytes: int, stop_event: threading.Event):

    bytes_prebuffer = int(taxa_bytes * SEGUNDOS_PRE_BUFFER) #os primeiros segundos são enviados na mesma hora e sem atraso
                                                           #isso preenche o buffer do client pra evitar engasgo no início
    bytes_enviados = 0
    start = time.monotonic() #usando um relógio pra prevenir atrasos nos envios

    with open(path, "rb") as f:
        while not stop_event.is_set():
            chunk = f.read(TAMANHO_BUFFER)
            if not chunk:
                break
            conn.sendall(chunk)
            bytes_enviados += len(chunk)

            if bytes_enviados > bytes_prebuffer: #controla o ritmo do envio dps de preencher o buffer inicial
                deadline = start + (bytes_enviados - bytes_prebuffer) / taxa_bytes #deadline pra enviar o próximo bloco, calculado pela taxa de bytes por segundo
                delay = deadline - time.monotonic() 
                if delay > 0:
                    stop_event.wait(delay) #se o envio tiver adiantado, espera um pouquinho
    return bytes_enviados
