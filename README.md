# Audio Streaming TCP

Streaming de áudio WAV via sockets TCP.
O servidor divide o arquivo em blocos e envia em ritmo de reprodução (tempo real) para cada cliente.
O cliente guarda os blocos num buffer, espera um pré-buffer encher e, depois, toca na placa de som.

## Estrutura

```
audio-streaming-tcp/
├── config.py
├── requirements.txt
├── audio_files/
│   ├── Natal.wav
│   ├── Celular.wav
│   └── Sample.wav
├── server/
│   ├── main.py
│   ├── socket_server.py
│   └── stream_handler.py
└── client/
    ├── main.py
    ├── socket_client.py
    ├── playback_buffer.py
    └── playlist.py
```

> Os nomes dos arquivos em `audio_files/` precisam bater **exatamente** (maiúsculas
> e minúsculas) com os de `client/playlist.py`. Só são aceitos WAV (PCM) no cliente.

## 1. Instalação

Requisito: Python 3.10 ou superior.

### Sobre o PortAudio

O `sounddevice` precisa da biblioteca PortAudio:

- **Windows e macOS:** vem embutida no `pip install sounddevice`.
- **Linux:** instale antes :
  - Debian/Ubuntu: `sudo apt install libportaudio2`
  - Fedora: `sudo dnf install portaudio`
  - Arch: `sudo pacman -S portaudio`

## 2. Instalação

```
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 3. Rodando

Abra **dois terminais na raiz do projeto** (com o ambiente ativado no do cliente).

**Terminal 1 - Servidor:**
```
python server/main.py
```
Deve aparecer: `Server escutando em 127.0.0.1:8080.`

**Terminal 2 - Cliente:**
```
python client/main.py
```
Escolha uma música (1, 2 ou 3). Depois de uma mensagem "Carregando buffer..." a música
começa. Aperte **ENTER** para parar e voltar ao menu. Apertar `0` sai.
