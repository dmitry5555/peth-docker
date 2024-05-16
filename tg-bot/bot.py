# приветствует и добавляет чат(user.tg_chat_id) в базу данных для дальнейшей рассылки обновлений 

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, filters, MessageHandler
from datetime import datetime
from db import db, Token, User, UserToken, initialize_db, msgs_to_sent, add_user, add_token, connect_user_token
# from dotenv import load_dotenv
import os
import asyncio
import re
import logging

# logging.getLogger("requests").setLevel(logging.WARNING)
# logging.getLogger("aiohttp").setLevel(logging.WARNING)

logging.basicConfig(filename='/var/logs/bot.log', format='%(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	try:
		inp_text = update.message.text
		resp_text = f'❌ Wrong address/token: {inp_text}'
		if inp_text == '/start':
			resp_text = '👋 Welcome! Please send your wallet address or NFT ID to monitor.'
		if inp_text.startswith('0x'):
			resp_text = add_user(update.effective_chat.id, inp_text)
		if re.match(r'^\d{6}$', inp_text):
			resp_text = add_token(int(inp_text), True, 0, False)
			connect_user_token(update.effective_chat.id, int(inp_text))
		if resp_text:
			await update.message.reply_text(resp_text)
	except Exception as e:
			logger.error(f"⚠️ tg_bot.py error at handle_text: {e}")
			print(f"⚠️ tg_bot.py error at handle_text: {e}")


if __name__ == '__main__':
	# load_dotenv()
	initialize_db()
	application = Application.builder().token(os.getenv("TG_API_TOKEN")).build()
	application.add_handler(MessageHandler(filters.TEXT, handle_text))
	application.run_polling()