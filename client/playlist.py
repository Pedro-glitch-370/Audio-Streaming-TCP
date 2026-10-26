'''
Consumir os dados do playback_buffer e
enviar eles pra placa de som usando a biblioteca de áudio escolhida
'''

# Simulação de servidor
biblioteca_musicas = {
    "1": {
        "titulo": "Natal",
        "caminho_arquivo": "./audio_files/Natal.wav"
    },
    "2": {
        "titulo": "Hit de carnaval 2027 (bem provavel)",
        "caminho_arquivo": "./audio_files/Celular.wav"
    },
    "3": {
        "titulo": "Zelda",
        "caminho_arquivo": "./audio_files/Sample.wav"
    }
}

def escolher_musica(user_escolha):
    titulo = ""
    caminho = ""

    #verifica se na biblioteca_musicas há a musica que o usuario quer e guarda na variavel que é 
    #exportada para a main para a reproducao
    if user_escolha in biblioteca_musicas:
        titulo = biblioteca_musicas[user_escolha]["titulo"]
        caminho = biblioteca_musicas[user_escolha]["caminho_arquivo"] 

        return titulo, caminho
        
    # Retorna None caso o usuário escolha uma opção inválida
    return None, None