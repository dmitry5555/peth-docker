# Парсинг от новых к старым ( чтобы не парсил все позиции) + ограничение на количество парсинга (поставил 5 последних позиций)
import sys

from web3 import Web3
from decimal import Decimal, getcontext
import logging
import time
from datetime import datetime

# from dotenv import load_dotenv
from db import db, initialize_db, add_message, get_tokens, upd_is_in_range, upd_liquidity, get_user_tokens
# import os

# Установка точности для десятичных вычислений
getcontext().prec = 50

# Настройка логирования
# logging.basicConfig(level=logging.INFO)
logging.basicConfig(filename='/var/logs/check.log', format='%(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def get_price_from_tick(tick: int, token0_decimals: int, token1_decimals: int) -> Decimal:
	"""
	Функция для перевода тика в стоимость USDC за 1 ETH с учетом количества десятичных знаков токенов.
	"""
	price_ratio = Decimal('1.0001') ** Decimal(-tick)
	price_in_usdc = price_ratio * Decimal(10 ** (token0_decimals - token1_decimals))
	return price_in_usdc

def get_pool_liquidity_by_nft_id(token, token_users) -> None:
	nft_id = token.token_id
	ankr_token = os.getenv('ANKR_TOKEN')
	ankr_url = 'https://rpc.ankr.com/optimism/' + ankr_token
	# ankr_url = 'https://rpc.ankr.com/optimism/fd27c3ac3eb21dd5f197d92e85c54e899776d7ff5e5c902e71bbafe9e2a180a9'
	web3 = Web3(Web3.HTTPProvider(ankr_url))

	nft_position_manager_address = '0xC36442b4a4522E871399CD717aBDD847Ab11FE88'
	nft_position_manager_abi = [
		{
			"inputs": [{"internalType": "uint256", "name": "tokenId", "type": "uint256"}],
			"name": "positions",
			"outputs": [
				{"internalType": "uint96", "name": "nonce", "type": "uint96"},
				{"internalType": "address", "name": "operator", "type": "address"},
				{"internalType": "address", "name": "token0", "type": "address"},
				{"internalType": "address", "name": "token1", "type": "address"},
				{"internalType": "uint24", "name": "fee", "type": "uint24"},
				{"internalType": "int24", "name": "tickLower", "type": "int24"},
				{"internalType": "int24", "name": "tickUpper", "type": "int24"},
				{"internalType": "uint128", "name": "liquidity", "type": "uint128"},
				{"internalType": "uint256", "name": "feeGrowthInside0LastX128", "type": "uint256"},
				{"internalType": "uint256", "name": "feeGrowthInside1LastX128", "type": "uint256"},
				{"internalType": "uint128", "name": "tokensOwed0", "type": "uint128"},
				{"internalType": "uint128", "name": "tokensOwed1", "type": "uint128"}
			],
			"stateMutability": "view",
			"type": "function"
		}
	]
	pool_address = '0x1fb3cf6e48F1E7B10213E7b6d87D4c073C7Fdb7b'
	pool_abi = [
		{
			"inputs": [],
			"name": "slot0",
			"outputs": [
				{"internalType": "uint160", "name": "sqrtPriceX96", "type": "uint160"},
				{"internalType": "int24", "name": "tick", "type": "int24"},
				{"internalType": "uint16", "name": "observationIndex", "type": "uint16"},
				{"internalType": "uint16", "name": "observationCardinality", "type": "uint16"},
				{"internalType": "uint16", "name": "observationCardinalityNext", "type": "uint16"},
				{"internalType": "uint8", "name": "feeProtocol", "type": "uint8"},
				{"internalType": "bool", "name": "unlocked", "type": "bool"}
			],
			"stateMutability": "view",
			"type": "function"
		},
		{
			"inputs": [
				{"internalType": "uint32[]", "name": "secondsAgos", "type": "uint32[]"}
			],
			"name": "observe",
			"outputs": [
				{"internalType": "int56[]", "name": "tickCumulatives", "type": "int56[]"},
				{"internalType": "uint160[]", "name": "secondsPerLiquidityCumulativeX128s", "type": "uint160[]"}
			],
			"stateMutability": "view",
			"type": "function"
		}
	]

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
	logger.info(f"{datetime.now()}: ⚠️ PriceUppeer: {price_upper}")
	logger.info(f"{datetime.now()}: ⚠️ CurrPrice: {current_price}")

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

	print(f"NFT ID: {nft_id}")
	print(f"Liquidity: {liquidity}")
	print(f"Token 0: {token0}")
	print(f"Token 1: {token1}")
	print(f"Tick Lower: {tick_lower}")
	print(f"Tick Upper: {tick_upper}")
	print(f"Price Lower: {price_lower}")
	print(f"Price Upper: {price_upper}")
	print(f"Current Tick: {current_tick}")
	print(f"Current Price: {current_price}")

# Основной цикл
if __name__ == "__main__":
	# nft_id = 644982
	# nft_id = 663944
	initialize_db()
	while True:
		for token in get_tokens():
			if int(token.liquidity) > 0:
				logger.info(f"{datetime.now()}: ✅ Checking pool liquidity for NFT ID: {token.token_id}")
				token_users = get_user_tokens(token.token_id)
				get_pool_liquidity_by_nft_id(token, token_users)
		logger.info(f"{datetime.now()}: ✨ Sleeping for 10 seconds...")
		time.sleep(10)