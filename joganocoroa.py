import telebot
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import re
import os

# Pegando variáveis de ambiente
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")

bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Autenticação no Spotify com Refresh Token
sp_oauth = SpotifyOAuth(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET,
    redirect_uri=SPOTIFY_REDIRECT_URI,
    scope="playlist-modify-public playlist-modify-private user-library-read"
)

# Pega o token atualizado
def get_spotify_client():
    token_info = sp_oauth.get_cached_token()
    if not token_info:
        auth_url = sp_oauth.get_authorize_url()
        print(f"Autorize o bot acessando este link: {auth_url}")
        response = input("Cole aqui o URL após autenticar: ")
        token_info = sp_oauth.get_access_token(response.split("code=")[1])

    return spotipy.Spotify(auth=token_info["access_token"])

sp = get_spotify_client()  # Autentica e pega a instância do Spotify

# Função para buscar músicas no Spotify
def buscar_musicas(query, limit=20):
    results = sp.search(q=query, type="track", limit=limit)
    return [track["uri"] for track in results["tracks"]["items"]]

# Função para criar playlist
def criar_playlist(user_id, nome, musicas):
    playlist = sp.user_playlist_create(user_id, nome, public=True)
    sp.playlist_add_items(playlist["id"], musicas)
    return playlist["external_urls"]["spotify"]

# Comando do bot para receber o prompt
@bot.message_handler(commands=["start"])
def send_welcome(message):
    bot.reply_to(message, "Envie um prompt com os critérios da playlist e, opcionalmente, a quantidade de músicas (ex: '50 músicas de kpop').")

@bot.message_handler(func=lambda message: True)
def gerar_playlist(message):
    user_query = message.text.strip()

    # Encontra todos os números no prompt
    numeros = [int(num) for num in re.findall(r'\d+', user_query)]

    if numeros:
        limit = max(numeros)  # Pega o maior número encontrado
        user_query = re.sub(r'\d+', '', user_query).strip()  # Remove os números do texto
    else:
        limit = 20  # Padrão

    bot.reply_to(message, f"Buscando {limit} músicas para: '{user_query}'...")
    musicas = buscar_musicas(user_query, limit)

    if not musicas:
        bot.reply_to(message, "Não encontrei músicas com esses critérios.")
        return

    user_id = sp.current_user()["id"]
    playlist_link = criar_playlist(user_id, "Playlist Gerada", musicas)
    bot.reply_to(message, f"Aqui está sua playlist: {playlist_link}")

# Rodando o bot
bot.polling()
