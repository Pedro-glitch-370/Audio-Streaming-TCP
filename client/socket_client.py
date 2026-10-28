import json
import socket
import threading
import wave
from dataclasses import dataclass

from config import HOST, PORT, TAMANHO_BUFFER, SEGUNDOS_PRE_BUFFER
from client.playback_buffer import Buffer

# Mapeia bytes por amostra → dtype do sounddevice.
# Só cobre PCM inteiro; WAV float32 exige parser manual (wave da stdlib não lê).
_DTYPES_PCM = {1: "uint8", 2: "int16", 3: "int24", 4: "int32"}


def _ler_cabecalho_wav(fp):
    """
    Lê o cabeçalho do WAV e deixa `fp` posicionado no primeiro byte de áudio.

    Usar o módulo `wave` da stdlib substitui ~40 linhas de parsing manual
    com `struct`. Ele já sabe pular blocos auxiliares (LIST, fact, etc.) e
    respeitar o padding de tamanho ímpar.
    """
    wav = wave.open(fp, "rb")

    if wav.getcomptype() != "NONE":
        raise ValueError(f"WAV comprimido não suportado: {wav.getcomptype()}")

    canais = wav.getnchannels()
    taxa = wav.getframerate()
    bytes_amostra = wav.getsampwidth()

    if bytes_amostra not in _DTYPES_PCM:
        raise ValueError(f"WAV com {bytes_amostra * 8} bits não suportado")

    return {
        "canais": canais,
        "taxa_amostragem": taxa,
        "bytes_amostra": bytes_amostra,
        "dtype": _DTYPES_PCM[bytes_amostra],
        "tamanho_dados": wav.getnframes() * canais * bytes_amostra,
    }

@dataclass
class Sessao:
    """
    Agrupa tudo que a main precisa para tocar e parar uma música:
      - o Buffer (consumido pelo player)
      - os metadados de formato
      - o socket (para fechar quando a main pedir)
      - o estado interno da thread de rede (parado / erro)
    """

    buffer: Buffer
    formato: dict
    sock: socket.socket
    _parado: bool = False   # flag lida pela thread de rede a cada iteração
    _erro: str | None = None

    def get_erro(self):
        """Retorna mensagem de erro (ou None). A main checa isso após o streaming."""
        return self._erro

    def parar(self):
        """Chamado pela main no finally — encerra a thread de rede e o socket."""
        self._parado = True
        try:
            # shutdown força o read() em andamento a retornar imediatamente.
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass  # socket já fechado — ignora
        self.sock.close()


def iniciar_streaming(nome_arquivo: str) -> Sessao:
    """
    Conecta ao servidor, envia PLAY, lê cabeçalho e dispara a thread
    que baixa o áudio em segundo plano. Retorna assim que a thread começa.
    """
    sock = socket.create_connection((HOST, PORT), timeout=30)

    try:
        # Comando do protocolo: "PLAY <nome_arquivo>\n"
        sock.sendall(f"PLAY {nome_arquivo}\n".encode())
        fp = sock.makefile("rb")

        # 1ª linha da resposta: JSON com status e metadados (taxa_bytes, tamanho).
        linha = fp.readline()
        if not linha:
            raise ConnectionError("Servidor fechou conexão sem responder")

        info = json.loads(linha)
        if info.get("status") != "ok":
            raise RuntimeError(info.get("message", "Erro desconhecido do servidor"))

        # Depois do JSON vem o WAV cru — pulamos o cabeçalho dele.
        formato = _ler_cabecalho_wav(fp)

    except Exception:
        # Qualquer falha aqui significa que não vamos mais usar o socket.
        sock.close()
        raise

    # Quantos bytes queremos acumular antes de liberar a reprodução.
    buffer = Buffer(int(info["taxa_bytes"] * SEGUNDOS_PRE_BUFFER))
    sessao = Sessao(buffer=buffer, formato=formato, sock=sock)

    # Quantos bytes ainda faltam receber. Se o servidor informou um tamanho
    # de dados válido e menor que o total anunciado, usamos ele para saber
    # exatamente quando parar (evita ler lixo ou ficar esperando EOF).
    restante = formato["tamanho_dados"] or None
    if restante is None or restante > info["tamanho"]:
        restante = None  # não confiável — lê até a conexão fechar

    def receber():
        """Thread de rede: baixa blocos e joga no buffer até acabar ou parar."""
        nonlocal restante  # modificamos o valor de fora do escopo

        try:
            while not sessao._parado and restante != 0:
                # Nunca pedir mais do que resta, se sabemos o total.
                n = TAMANHO_BUFFER if restante is None else min(TAMANHO_BUFFER, restante)
                chunk = fp.read(n)

                if not chunk:
                    # EOF inesperado: conexão fechou antes do previsto.
                    if restante and not sessao._parado:
                        sessao._erro = f"Conexão encerrada com {restante} bytes faltando"
                    break

                buffer.adicionar_chunk(chunk)
                if restante is not None:
                    restante -= len(chunk)

        except OSError as e:
            # Erro de rede (reset, timeout, etc.). Só registra se não fomos nós
            # que pedimos para parar (nesse caso, o erro é esperado).
            if not sessao._parado:
                sessao._erro = f"Erro ao receber dados: {e}"

        finally:
            # Em qualquer caso (sucesso, erro, parada), avisa o buffer que acabou
            # e libera os recursos. Sem isso o player pode travar esperando dados.
            buffer.finalizar()
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            fp.close()
            sock.close()

    threading.Thread(target=receber, daemon=True).start()
    return sessao

def listar_arquivos() -> list[str]:
    """
    Pergunta ao servidor quais arquivos ele tem disponíveis (comando LIST).

    Retorna a lista de nomes, ou [] se o servidor responder erro.
    """
    sock = socket.create_connection((HOST, PORT), timeout=10)
    try:
        sock.sendall(b"LIST\n")
        linha = sock.makefile("rb").readline()
        if not linha:
            raise ConnectionError("Servidor fechou conexão sem responder")
        info = json.loads(linha)
        if info.get("status") != "ok":
            raise RuntimeError(info.get("message", "Erro desconhecido do servidor"))
        return info["files"]
    finally:
        sock.close()