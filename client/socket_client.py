import json
import os
import socket
import struct
import sys
import threading

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)

from config import HOST, PORT, TAMANHO_BUFFER, SEGUNDOS_PRE_BUFFER
from playback_buffer import criar_buffer, adicionar_chunk, finalizar_buffer

#dtypes do sounddevice de acordo com o número de bytes por amostra
_DTYPES_PCM = {1: "uint8", 2: "int16", 3: "int24", 4: "int32"}

#o servidor manda o arquivo .wav inteiro, então os primeiros bytes são o cabeçalho WAV (e não áudio);
#aqui a gente lê esse cabeçalho pra descobrir canais, taxa de amostragem e formato das amostras;
#e deixa o stream posicionado exatamente no começo do áudio de verdade
def _ler_cabecalho_wav(stream):
    riff = stream.read(12) #lê os 12 primeiros bytes
    if len(riff) < 12 or riff[:4] != b"RIFF" or riff[8:12] != b"WAVE":
        raise ValueError("O server enviou um arquivo que não é WAV")

    formato = None
    while True:
        cab = stream.read(8) #percorre os blocos do .wav de 8 em 8 bytes
        if len(cab) < 8:
            raise ValueError("WAV inválido: bloco 'data' não encontrado")
        id_bloco, tamanho = struct.unpack("<4sI", cab)

        #bloco do formato, que define o tipo correto do dado que o player vai usar
        if id_bloco == b"fmt ":
            fmt = stream.read(tamanho + tamanho % 2)
            tag, canais, taxa, _, _, bits = struct.unpack("<HHIIHH", fmt[:16])
            if tag == 0xFFFE and tamanho >= 26:
                tag = struct.unpack("<H", fmt[24:26])[0]
            if tag == 1 and bits // 8 in _DTYPES_PCM:
                dtype = _DTYPES_PCM[bits // 8]
            elif tag == 3 and bits == 32:
                dtype = "float32"
            else:
                raise ValueError(f"Formato WAV não suportado (tag={tag}, {bits} bits)")
            formato = {"canais": canais, "taxa_amostragem": taxa, "bytes_amostra": bits // 8, "dtype": dtype}

        #bloco data, que confirma que o bloco de formato veio antes e pega o tamanho real dos dados de áudio
        elif id_bloco == b"data":
            if formato is None:
                raise ValueError("WAV inválido: bloco 'data' veio antes do 'fmt '")
            formato["tamanho_dados"] = tamanho
            return formato

        else: #blocos que não interessam são pulados
            stream.read(tamanho + tamanho % 2)

#função pra se conectar ao servr, validar o comando play e começar a receber o áudio no plano de fundo;
#é chamada quando o usuário escolhe uma música
def iniciar_streaming(nome_arquivo: str):
    sock = socket.create_connection((HOST, PORT), timeout=30) #cria uma conexão TCP com o server
    try:
        sock.sendall(f"PLAY {nome_arquivo}\n".encode("utf-8")) #envia o comando de reprodução formatado
        stream = sock.makefile("rb")

        linha = stream.readline() #lê a primeira linha de resposta do server, que é um JSON com o status da requisição e metadados gerais
        if not linha:
            raise ConnectionError("O servidor fechou a conexão sem responder")
        info = json.loads(linha)
        if info.get("status") != "ok":
            raise RuntimeError(info.get("message", "Erro desconhecido do servidor"))

        formato = _ler_cabecalho_wav(stream) #posiciona o ponteiro do stream no começo dos dados de áudio bruto
    except Exception:
        sock.close()
        raise
    
    buffer = criar_buffer(int(info["taxa_bytes"] * SEGUNDOS_PRE_BUFFER)) #cria o buffer, calculando o espaço necessário com a taxa de bytes e o tempo de pré-buffer
    
    estado = {"erro": None, "parado": False} #dict pra controlar a execução da thread
    tamanho_dados = formato["tamanho_dados"]
    restante = tamanho_dados if 0 < tamanho_dados <= info["tamanho"] else None

    def _fechar():
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        stream.close()
        sock.close()

    #função interna pra iniciar a thread com um loop baixando os pedaços do arquivo de áudio
    def _receber():
        nonlocal restante #pra garantir que tá mexendo no 'restante' externo certo
        try:
            while not estado["parado"] and restante != 0:
                n = TAMANHO_BUFFER if restante is None else min(TAMANHO_BUFFER, restante)
                chunk = stream.read(n)
                if not chunk:
                    if restante is not None and not estado["parado"]:
                        estado["erro"] = f"Conexão encerrada com {restante} bytes faltando"
                    break
                adicionar_chunk(buffer, chunk) #os pedaços do arquivo são adicionados no buffer do cliente
                if restante is not None:
                    restante -= len(chunk)
        except OSError as e:
            if not estado["parado"]:
                estado["erro"] = f"Erro ao receber dados: {e}"
        finally:
            finalizar_buffer(buffer)
            _fechar()

    def parar():
        estado["parado"] = True
        _fechar()

    #começa a thread de rede em segundo plano
    threading.Thread(target=_receber, daemon=True).start()

    #dict com os controles e dados da sessão
    return {
        "buffer": buffer,
        "formato": formato,
        "get_erro": lambda: estado["erro"],
        "parar": parar,
    }