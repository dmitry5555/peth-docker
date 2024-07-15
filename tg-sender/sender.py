# рассылает обновления по всем чатам(пользователям)

import logging
from logging.handlers import RotatingFileHandler
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.error import TelegramError
from datetime import datetime
from db import db, Token, initialize_db, msgs_to_sent, mark_as_sent
# from dotenv import load_dotenv
import os
import asyncio

# logging.getLogger("requests").setLevel(logging.WARNING)
# logging.getLogger("aiohttp").setLevel(logging.WARNING)

# Настройка логирования
logger = logging.getLogger(__name__)
handler = RotatingFileHandler(filename='/var/logs/sender.log', maxBytes=1048576, backupCount=10)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

async def send_message():
	bot = Application.builder().token(token).build().bot # до 30 сообщений в секунду но это не точно
	while True:
		# sent_ids = []
		for message in msgs_to_sent():
			text = message.text
			chat_id = message.chat_id
			# user_id = message.user_id
			# обновляем базу и шлем сообщения (100-1000 разом все должно быть ок)
			if text:
				try:
					await bot.send_message(chat_id=chat_id, text=text, parse_mode='Markdown')
					mark_as_sent(message.id)
					# sent_ids.append(message.id)
				except TelegramError as e:
					logger.error(f"Failed to send message to chat {chat_id}. Error: {e}")
			else:
				logger.error(f"Message with id {message.id} has no text")
		# if sent_ids:
		# 	mark_as_sent(sent_ids)
		await asyncio.sleep(5) # Задержка в 2 секунды после выполнения цикла

if __name__ == '__main__':
	# load_dotenv()
	initialize_db()
	token = os.getenv("TG_API_TOKEN")
	asyncio.run(send_message())