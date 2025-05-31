import os
import telegram

# Enviar mensagens para o Telegram
def notificar_mensagem(texto):
    token = os.getenv("8015668113:AAHW99YDOsrecBE9Ezh7pz3TvlhTHfEMcaE")
    chat_id = os.getenv("1742433608")
    if token and chat_id:
        bot = telegram.Bot(token=token)
        bot.send_message(chat_id=chat_id, text=texto)
