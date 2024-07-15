# Парсинг от новых к старым ( чтобы не парсил все позиции) + ограничение на количество парсинга (поставил 5 последних позиций)
import sys
import json

from web3 import Web3
from decimal import Decimal, getcontext
import logging
from logging.handlers import RotatingFileHandler
import time
from datetime import datetime

# from dotenv import load_dotenv
from db import db, initialize_db, add_message, get_tokens, upd_is_in_range, upd_liquidity, get_users_with_token
import os

# Wallet
optim_nft_position_manager_address = Web3.to_checksum_address('0xc36442b4a4522e871399cd717abdd847ab11fe88')
arbit_nft_position_manager_address = Web3.to_checksum_address('0xc36442b4a4522e871399cd717abdd847ab11fe88')
base_nft_position_manager_address = Web3.to_checksum_address('0x03a520b32c04bf3beef7beb72e919cf822ed34f1')

# Optimism - Uniswap V3 (Optimism) - USD Coin Price (USDC)
ethereum_pool_address = Web3.to_checksum_address('0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640')
optim_pool_address = Web3.to_checksum_address('0x1fb3cf6e48F1E7B10213E7b6d87D4c073C7Fdb7b')
# base usdc/weth
base_pool_address = Web3.to_checksum_address('0xd0b53d9277642d899df5c87a3966a349a798f224')
# arbitrum usdc/weth
arbit_pool_address = Web3.to_checksum_address('0xc6962004f452be9203591991d15f6b388e09e8d0')

with open('./optim_nft_position_manager_abi.json', 'r') as w:
    nft_position_manager_abi = json.load(w)
with open('./optim_pool_abi.json', 'r') as w:
    optim_pool_abi = json.load(w)
with open('./base_pool_abi.json', 'r') as w:
	base_pool_abi = json.load(w)
with open('./arbit_pool_abi.json', 'r') as w:
	arbit_pool_abi = json.load(w)

ankr_token = os.getenv('ANKR_TOKEN')
ethereum_url = 'https://rpc.ankr.com/eth/' + ankr_token
optim_url = 'https://rpc.ankr.com/optimism/' + ankr_token
arbit_url = 'https://rpc.ankr.com/arbitrum/' + ankr_token
base_url = 'https://rpc.ankr.com/base/' + ankr_token

# Установка точности для десятичных вычислений
getcontext().prec = 50

# Настройка логирования
logger = logging.getLogger(__name__)
handler = RotatingFileHandler(filename='/var/logs/check.log', maxBytes=1048576, backupCount=10)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

def get_price_from_tick(tick: int, token0_decimals: int, token1_decimals: int) -> Decimal:
	"""
	Функция для перевода тика в стоимость USDC за 1 ETH с учетом количества десятичных знаков токенов.
	"""
	price_ratio = Decimal('1.0001') ** Decimal(-tick)
	price_in_usdc = price_ratio * Decimal(10 ** (token0_decimals - token1_decimals))
	return price_in_usdc

def get_pool_liquidity_by_nft_id(token, network, token_users) -> None:
	nft_id = token.token_id

	if (network == 'optimism'):
		rpc_url = optim_url
		nft_position_manager_address = optim_nft_position_manager_address
		pool_abi = optim_pool_abi
		pool_address = optim_pool_address
	elif (network == 'arbitrum'):
		rpc_url = arbit_url
		nft_position_manager_address = arbit_nft_position_manager_address
		pool_abi = arbit_pool_abi
		pool_address = arbit_pool_address
	elif (network == 'ethereum'):
		rpc_url = ethereum_url
		nft_position_manager_address = optim_nft_position_manager_address
		pool_abi = optim_pool_abi
		pool_address = ethereum_pool_address
	elif (network == 'base'):
		rpc_url = base_url
		pool_abi = base_pool_abi
		pool_address = base_pool_address
		nft_position_manager_address = base_nft_position_manager_address

# nft_position_manager - контракт в , который управляет позициями NFT в пуле ликвидности Uniswap V3.
# отвечает за создание, управление и закрытие позиций NFT в пуле. Он позволяет пользователям создавать уникальные токены NFT, 
# привязанные к определенному диапазону цен, и управлять их ликвидностью.
# В коде создается экземпляр контракта nft_position_manager с помощью библиотеки web3
	web3 = Web3(Web3.HTTPProvider(rpc_url))
	nft_position_manager = web3.eth.contract(address=nft_position_manager_address, abi=nft_position_manager_abi)
	pool_contract = web3.eth.contract(address=pool_address, abi=pool_abi)

	try:
		position = nft_position_manager.functions.positions(nft_id).call()
		logger.info(f"{datetime.now()}: Successfully retrieved position for NFT ID: {nft_id}")
	except Exception as e:
		logger.error(f"{datetime.now()}: Error retrieving position for NFT ID: {nft_id}")
		logger.error(f"{datetime.now()}: Error message: {str(e)}")
		return

	liquidity = position[7]
	token0 = position[2]
	token1 = position[3]
	tick_lower = position[5]
	tick_upper = position[6]

	token0_decimals = 18  # Для ETH
	token1_decimals = 6   # Для USDC

	price_lower = get_price_from_tick(tick_lower, token0_decimals, token1_decimals)
	price_upper = get_price_from_tick(tick_upper, token0_decimals, token1_decimals)

	# Поменять местами price_lower и price_upper, если price_lower > price_upper
	if price_lower > price_upper:
		price_lower, price_upper = price_upper, price_lower

	try:
		slot0 = pool_contract.functions.slot0().call()
		logger.info(f"{datetime.now()}: Successfully retrieved slot0")
	except Exception as e:
		logger.error(f"{datetime.now()}: Error retrieving slot0")
		logger.error(f"{datetime.now()}: Error message: {str(e)}")
		return

	current_tick = slot0[1]
	current_price = get_price_from_tick(current_tick, token0_decimals, token1_decimals)

	# только если есть ликвидность можно вернуть в мониторинг но при условии что цена в рамках

	logger.info(f"{datetime.now()}: ✅ Liquidity for NFT ID: {token.token_id} is {liquidity}")
	logger.info(f"{datetime.now()}: ⚠️ TokenOldLiquidity: {token.liquidity}")
	logger.info(f"{datetime.now()}: ⚠️ PriceUpper: {price_upper}")
	logger.info(f"{datetime.now()}: ⚠️ CurrPrice: {current_price}")

	logger.info(f"{datetime.now()}: ⚠️ Tick Lower: {tick_lower}")
	logger.info(f"{datetime.now()}: ⚠️ Tick Upper: {tick_upper}")
	logger.info(f"{datetime.now()}: ⚠️ Current Tick: {current_tick}")

	# liquidity changed to 0 - position is closed and there will be no liquidity in this NFTID 
	if int(liquidity) == 0:
		upd_liquidity(nft_id, 0)
		for token_user in token_users:
			logger.info(f'{datetime.now()}: 💧 No liquidity. NFT ID: {nft_id}.')
			add_message(token_user.chat_id, f'💧 No liquidity. NFT ID: {nft_id}.')
	# # liquidity added
	# if int(liquidity) > 0 and int(token.liquidity) == 0:
	# 	upd_liquidity(nft_id, int(liquidity))
	# 	for token_user in token_users:
	# 		logger.info(f'{datetime.now()}: 💧 Liquidity added. NFT ID: {nft_id}.')
	# 		add_message(token_user.chat_id, f'💧 Liquidity added. NFT ID: {nft_id}.')
	# price out of range
	if (current_price < price_lower) or (current_price > price_upper):
		if (token.is_in_range):
			upd_is_in_range(nft_id, False)
			for token_user in token_users:
				logger.info(f'{datetime.now()}: 📈 Out of range. NFT ID: {nft_id}.')
				add_message(token_user.chat_id, f'📈 Out of range. NFT ID: {nft_id}.')

	if (price_lower < current_price) and (current_price < price_upper):
		if not (token.is_in_range):
			upd_is_in_range(nft_id, True)
			for token_user in token_users:
				logger.info(f'{datetime.now()}: 📉 In range. NFT ID: {nft_id}.')
				add_message(token_user.chat_id, f'📉 In range. NFT ID: {nft_id}.')

	# print(f"NFT ID: {nft_id}")
	# print(f"Liquidity: {liquidity}")
	# print(f"Token 0: {token0}")
	# print(f"Token 1: {token1}")
	# print(f"Tick Lower: {tick_lower}")
	# print(f"Tick Upper: {tick_upper}")
	# print(f"Price Lower: {price_lower}")
	# print(f"Price Upper: {price_upper}")
	# print(f"Current Tick: {current_tick}")
	# print(f"Current Price: {current_price}")

# Основной цикл
if __name__ == "__main__":
	# nft_id = 644982
	# nft_id = 663944
	initialize_db()
	while True:
		for token in get_tokens():
			if int(token.liquidity) > 0:
				logger.info(f"{datetime.now()}: ✅ Checking pool liquidity for NFT ID: {token.token_id}")
				token_users = get_users_with_token(token.token_id)
				get_pool_liquidity_by_nft_id(token, token.network, token_users)
		logger.info(f"{datetime.now()}: ✨ Sleeping for 10 seconds...")
		time.sleep(10)