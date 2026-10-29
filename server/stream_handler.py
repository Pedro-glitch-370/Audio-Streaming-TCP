"""
Funções de leitura/envio de áudio do lado do servidor.

Contrato com o cliente (definido em client/socket_client.py):
  - `obter_info_streaming` retorna o JSON que o cliente espera receber
    ANTES do WAV/MP3. Campos obrigatórios:
        nome_arquivo, tamanho, taxa_bytes, tamanho_chunk
  - `enviar_arquivo_streaming` envia o WAV/MP3 INTEIRO (cabeçalho + dados).
    O cliente faz o parsing do cabeçalho sozinho.

Garantia importante: o total de bytes enviados é exatamente `tamanho`
(ou seja, `path.stat().st_size`). O cliente compara o recebido com
`tamanho_dados` do cabeçalho WAV e reclama se faltar.
"""
import socket
import threading
import time
import wave
from pathlib import Path

import miniaudio

from config import (
    DIRETORIO_AUDIO,
    EXTENSOES_SUPORTADAS,
    FALLBACK_BITRATE_KBPS,
    SEGUNDOS_PRE_BUFFER,
    TAMANHO_BUFFER,
)


def listar_arquivos_audio():
    """Retorna nomes dos arquivos de áudio disponíveis (ordem alfabética)."""
    if not DIRETORIO_AUDIO.is_dir():
        return []
    return sorted(
        p.name
        for p in DIRETORIO_AUDIO.iterdir()
        if p.is_file() and p.suffix.lower() in EXTENSOES_SUPORTADAS
    )


def obter_caminho_arquivo(name: str) -> Path | None:
    """
    Resolve nome → caminho absoluto dentro de DIRETORIO_AUDIO.

    Rejeita: nomes vazios, extensões não suportadas, path traversal
    (ex.: "../../etc/passwd") e arquivos inexistentes.
    """
    if not name:
        return None
    path = (DIRETORIO_AUDIO / name).resolve()

    # Confina o arquivo dentro de DIRETORIO_AUDIO (proteção contra traversal).
    try:
        path.relative_to(DIRETORIO_AUDIO.resolve())
    except ValueError:
        return None

    if path.suffix.lower() in EXTENSOES_SUPORTADAS and path.is_file():
        return path
    return None


def obter_taxa_transmissao(path: Path) -> int:
    """
    Bytes por segundo que o áudio consome.

    Para .wav: lê do cabeçalho (preciso).
    Para .mp3: tamanho do arquivo / duração.
    Falha: usa FALLBACK_BITRATE_KBPS.
    """
    if path.suffix.lower() == ".wav":
        try:
            with wave.open(str(path), "rb") as w:
                rate = w.getframerate() * w.getnchannels() * w.getsampwidth()
                if rate > 0:
                    return rate
        except (wave.Error, EOFError):
            pass
    elif path.suffix.lower() == ".mp3":
        try:
            duracao = miniaudio.mp3_get_file_info(str(path)).duration
            if duracao > 0:
                return int(path.stat().st_size / duracao)
        except miniaudio.MiniaudioError:
            pass
    return FALLBACK_BITRATE_KBPS * 1000 // 8


def obter_info_streaming(path: Path) -> dict:
    """
    JSON de metadados que o cliente recebe antes do WAV.

    O cliente usa:
      - `taxa_bytes`  → dimensionar o Buffer (taxa_bytes * SEGUNDOS_PRE_BUFFER)
      - `tamanho`     → detectar fim de transferência truncada
      - `tamanho_chunk` → só informativo
    """
    return {
        "nome_arquivo": path.name,
        "tamanho": path.stat().st_size,
        "taxa_bytes": obter_taxa_transmissao(path),
        "tamanho_chunk": TAMANHO_BUFFER,
    }


def enviar_arquivo_streaming(
    conn: socket.socket,
    path: Path,
    taxa_bytes: int,
    stop_event: threading.Event,
) -> int:
    """
    Envia o arquivo em chunks de TAMANHO_BUFFER, em ritmo contínuo.

    Estratégia:
      - primeiros `bytes_prebuffer` bytes → enviados o mais rápido possível
        (preenche o buffer do cliente sem atrasar o início)
      - a partir daí → pacing: cada chunk é liberado no instante em que
        o cliente teria terminado de tocar o anterior. Isso mantém o
        buffer do cliente estável (sem encher nem esvaziar) e o envio
        é contínuo do ponto de vista do cliente.

    O relógio de referência é atualizado a cada chunk (não é fixo em
    `start`), então atrasos pontuais de rede não se acumulam.
    """
    bytes_prebuffer = int(taxa_bytes * SEGUNDOS_PRE_BUFFER)
    bytes_enviados = 0
    start = time.monotonic()

    with open(path, "rb") as f:
        while not stop_event.is_set():
            chunk = f.read(TAMANHO_BUFFER)
            if not chunk:
                break

            # Momento em que este chunk começa a ser enviado.
            inicio_chunk = time.monotonic()
            conn.sendall(chunk)
            bytes_enviados += len(chunk)

            if bytes_enviados > bytes_prebuffer:
                # Quanto tempo o cliente leva pra tocar este chunk.
                duracao_chunk = len(chunk) / taxa_bytes
                # Deadline relativo ao INÍCIO do envio deste chunk —
                # evita acúmulo de atraso entre iterações.
                deadline = inicio_chunk + duracao_chunk
                delay = deadline - time.monotonic()
                if delay > 0:
                    stop_event.wait(delay)

    return bytes_enviados
