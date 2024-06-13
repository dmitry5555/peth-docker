# from dotenv import load_dotenv
from peewee import Model, PostgresqlDatabase, IntegerField, CharField, BooleanField
import os

# load_dotenv()

user = os.getenv('POSTGRES_USER')
password = os.getenv('POSTGRES_PASSWORD')
db_name = os.getenv('POSTGRES_DB')
host = "postgres"
port = 5432

# Определяем базу данных SQLite
# db = SqliteDatabase('db.db')

db = PostgresqlDatabase(
    db_name,
    user=user,
    password=password,
    host=host,
    port=port
)

class BaseModel(Model):
    class Meta:
        database = db
		
class User(BaseModel):
	chat_id = IntegerField()
	wallet = CharField(null=True)

	class Meta:
		database = db 

class Token(BaseModel):
	token_id = IntegerField()
	is_manual = BooleanField(default=False)
	liquidity = CharField()
	is_in_range = BooleanField(default=False)
	network = CharField()

	class Meta:
		database = db

class UserToken(BaseModel):
    chat_id = IntegerField()
    token_id = IntegerField()

    class Meta:
        database = db 

class Message(BaseModel):
	chat_id = IntegerField()
	text = CharField()
	is_sent = BooleanField(default=False)

	class Meta:
		database = db

def initialize_db():
	with db:
		db.create_tables([User], safe=True)
		db.create_tables([Token], safe=True)
		db.create_tables([Message], safe=True)
		db.create_tables([UserToken], safe=True)


def add_user(chat_id, wallet):
	with db:
		text = 'Error adding new wallet/user'
		user, created = User.get_or_create(chat_id=chat_id, defaults={'wallet': wallet})
		if created:
			text = f'⚙️ New wallet created. Retrieving active positions: {wallet} ...'
		if not created: # Если запись уже существует
			if user.wallet == wallet:
				text = f'⚙️ Wallet already exists: {wallet} ...'
			else:
				user.wallet = wallet
				user.save()
				text = f'⚙️ Your wallet updated. Retrieving active positions: {wallet} ...'
		return text

def get_users():
	with db:
		users = []
		for user in User.select():
			users.append(user)
		return users

# кейсы   1 - новая позииция  2 - ликвидность изменилась после 0  3 - ликвидность также выше нуля (ничего не делать)

def add_token(token_id, is_manual, liquidity, is_in_range, network):
	with db:
		token, created = Token.get_or_create(token_id=token_id, network=network, defaults={'is_manual': is_manual, 'liquidity': liquidity, 'is_in_range': is_in_range})
		if created:
			return True

def connect_user_token(chat_id, token_id):
	with db:
		token, created = UserToken.get_or_create(chat_id=chat_id, token_id=token_id)
		# if created:
		# return true

def get_users_with_token(token_id):
	with db:
		users_with_token = []
		for user_with_token in UserToken.select().where(UserToken.token_id == token_id):
			users_with_token.append(user_with_token)
		return users_with_token

def upd_liquidity(token_id, liquidity):
	with db:
		query = Token.update(liquidity=str(liquidity)).where(Token.token_id == token_id)
		query.execute()
		# token = Token.get(token_id=token_id)
		# token.save()

def upd_is_in_range(token_id, is_in_range):
	with db:
		query = Token.update(is_in_range=is_in_range).where(Token.token_id == token_id)
		query.execute()
		# token = Token.get(token_id=token_id)
		# token.save()

# def is__token(token_id):
# 	db.connect()
# 	token = Token.get(token_id=token_id)
# 	token.is_active = False
# 	token.save()
# 	db.close()

def add_message(chat_id, text):
	with db:
		Message.create(chat_id=chat_id, text=text, is_sent=False)
	# return message.id

def get_tokens():
	with db:
		tokens = []
		for token in Token.select():
			tokens.append(token)
		return tokens

def get_msgs():
	with db:
		msgs = []
		for msg in Message.select():
			msgs.append(msg)
		return msgs

def msgs_to_sent():
	with db:
		messages = []
		for message in Message.select().where(Message.is_sent == False):
			messages.append(message)
		return messages

# def mark_as_sent(sent_ids):
# 	with db:
# 		for sent_id in sent_ids:
# 			query = Message.update(is_sent=True).where(Message.id == sent_id)
# 			query.execute()

def mark_as_sent(sent_id):
	with db:
		query = Message.update(is_sent=True).where(Message.id == sent_id)
		query.execute()
			
# def print_tokens():
# 	db.connect()
# 	for token in Token.select():
# 		print(f'{token.token_id}, {token.liquidity}')
# 	db.close()