from pathlib import Path

DIRETORIO_BASE = Path(__file__).resolve().parent  #caminho absoluto da pasta raiz do projeto

#constantes da rede
HOST = "127.0.0.1" #IP onde o servidor vai rodar
PORT = 8080 #porta padrão onde o server escuta as conexões TCP que chegam
TAMANHO_BUFFER = 8192 #limite de 8KB por bloco
MAX_CLIENTS = 50 #permite 50 conexões ao mesmo tempo
HANDSHAKE_TIMEOUT = 10 #permite 10 segundos pro cliente enviar sua requisição, depois derruba
SEND_TIMEOUT = 30 #permite 30 segundos sem conseguir enviar, depois derruba

#constantes do áudio
DIRETORIO_AUDIO = DIRETORIO_BASE / "audio_files" #define o caminho pra pasta audio_files
DEFAULT_AUDIO = "sample.wav" #nome do arquivo de áudio padrão que será carregado
EXTENSOES_SUPORTADAS = (".wav", ".mp3") #extensões de áudio permitidas pelo sistema

#constantes do streaming
SEGUNDOS_PRE_BUFFER = 2.0 #permite 2 segundos de áudio pro servidor enviar sem atraso e já na conexão, pra encher o buffer do cliente antes de reproduzir
FALLBACK_BITRATE_KBPS = 128 #taxa de de 128 kbps pra fallback de arquivos onde não é fácil calcular a taxa de transmissão