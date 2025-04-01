import telebot
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import re
import os
import time
from flask import Flask, request
from threading import Thread
import uuid

# Configurações do Flask
app = Flask(__name__)
bot = telebot.TeleBot(os.getenv("TELEGRAM_TOKEN"))

# Dicionário para armazenar tokens (usar um banco de dados real em produção)
auth_flows = {}
user_tokens = {}

# Configuração OAuth do Spotify
SPOTIFY_OAUTH = SpotifyOAuth(
    client_id=os.getenv("SPOTIFY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
    redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI"),
    scope="playlist-modify-public"
)

# Rota de callback para autenticação
@app.route('/callback')
def spotify_callback():
    code = request.args.get('code')
    state = request.args.get('state')

    if state not in auth_flows:
        return "Sessão expirada! Tente novamente no Telegram."

    try:
        token_info = SPOTIFY_OAUTH.get_access_token(code, as_dict=True)
        user_tokens[auth_flows[state]] = token_info

        bot.send_message(auth_flows[state], "✅ Autenticação concluída! Agora você pode criar playlists.\n✏️ Escreva o que deseja na sua playlist.")
        return "Autenticação bem-sucedida! Volte ao Telegram."
    except Exception as e:
        return f"Erro na autenticação: {e}"

# Comando para iniciar autenticação
@bot.message_handler(commands=['login'])
def start_auth(message):
    state = str(uuid.uuid4())
    auth_url = SPOTIFY_OAUTH.get_authorize_url(state=state)
    auth_flows[state] = message.chat.id

    bot.send_message(
        message.chat.id,
        f"🔑 [Clique aqui para autenticar no Spotify]({auth_url})",
        parse_mode="Markdown"
    )

# Handler para criar playlists
@bot.message_handler(func=lambda m: True)
def handle_message(message):
    try:
        if message.chat.id not in user_tokens:
            return bot.reply_to(message, "⚠️ Faça /login primeiro!")

        # Aguarda 2 minutos antes de processar a solicitação
        bot.reply_to(message, "⏳ Processando sua solicitação... Aguarde um momento.")
        time.sleep(120)

        # Obtém o token atualizado
        token_info = user_tokens[message.chat.id]
        if SPOTIFY_OAUTH.is_token_expired(token_info):
            token_info = SPOTIFY_OAUTH.refresh_access_token(token_info['refresh_token'])
            user_tokens[message.chat.id] = token_info

        sp = spotipy.Spotify(auth=token_info['access_token'])

        # Processa o comando do usuário
        command = message.text.lower()
        numbers = [int(n) for n in re.findall(r'\d+', command)]
        limit = numbers[0] if numbers else 20  # Define 20 como padrão se não houver número
        query = re.sub(r'\d+', '', command).strip()

        if not query:
            return bot.reply_to(message, "🎯 Exemplo: '15 músicas de rock anos 80'")

        # Busca músicas
        results = sp.search(q=query, type='track', limit=limit)
        tracks = [item['uri'] for item in results['tracks']['items']]

        if not tracks:
            return bot.reply_to(message, "😵 Nenhum resultado encontrado!")

        # Cria playlist
        playlist = sp.user_playlist_create(
            user=sp.me()['id'],
            name="Playlist by GeniefyBot",
            public=True
        )
        sp.playlist_add_items(playlist['id'], tracks)

        bot.reply_to(message, f"🎉 Playlist criada!\n{playlist['external_urls']['spotify']}")

    except Exception as e:
        bot.reply_to(message, f"💥 Erro: {str(e)}")
        print(f"Erro no chat {message.chat.id}: {e}")

# Comando start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_msg = (
        "🎵 *Bem-vindo ao Spotify Playlist Bot!*\n\n"
        "1. Faça /login para vincular sua conta Spotify\n"
        "2. Digite o estilo musical desejado\n"
        "Exemplo: _'25 músicas de sertanejo universitário'_"
    )
    bot.send_message(message.chat.id, welcome_msg, parse_mode="Markdown")

# Inicialização
def run_bot():
    bot.polling(none_stop=True)

if __name__ == "__main__":
    Thread(target=run_bot).start()
    app.run(host='0.0.0.0', port=8080)
