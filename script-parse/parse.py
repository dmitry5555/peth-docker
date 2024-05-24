# gcheck wallet for nfts

from web3 import Web3
import logging
from logging.handlers import RotatingFileHandler
import time

# from dotenv import load_dotenv
from db import db, initialize_db, add_token, get_users, add_message, connect_user_token
import os

# Настройка логирования
logger = logging.getLogger(__name__)
handler = RotatingFileHandler(filename='/var/logs/parse.log', maxBytes=1048576, backupCount=10)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

user = os.getenv('POSTGRES_USER')
ankr_token = os.getenv('ANKR_TOKEN')
ankr_url = 'https://rpc.ankr.com/optimism/' + ankr_token

web3 = Web3(Web3.HTTPProvider(ankr_url))

nft_manager_address = '0xC36442b4a4522E871399CD717aBDD847Ab11FE88'
nft_manager_abi = [
	{
		"inputs": [
			{
				"internalType": "address",
				"name": "owner",
				"type": "address"
			}
		],
		"name": "balanceOf",
		"outputs": [
			{
				"internalType": "uint256",
				"name": "",
				"type": "uint256"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "address",
				"name": "owner",
				"type": "address"
			},
			{
				"internalType": "uint256",
				"name": "index",
				"type": "uint256"
			}
		],
		"name": "tokenOfOwnerByIndex",
		"outputs": [
			{
				"internalType": "uint256",
				"name": "",
				"type": "uint256"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "uint256",
				"name": "tokenId",
				"type": "uint256"
			}
		],
		"name": "positions",
		"outputs": [
			{
				"internalType": "uint96",
				"name": "nonce",
				"type": "uint96"
			},
			{
				"internalType": "address",
				"name": "operator",
				"type": "address"
			},
			{
				"internalType": "address",
				"name": "token0",
				"type": "address"
			},
			{
				"internalType": "address",
				"name": "token1",
				"type": "address"
			},
			{
				"internalType": "uint24",
				"name": "fee",
				"type": "uint24"
			},
			{
				"internalType": "int24",
				"name": "tickLower",
				"type": "int24"
			},
			{
				"internalType": "int24",
				"name": "tickUpper",
				"type": "int24"
			},
			{
				"internalType": "uint128",
				"name": "liquidity",
				"type": "uint128"
			},
			{
				"internalType": "uint256",
				"name": "feeGrowthInside0LastX128",
				"type": "uint256"
			},
			{
				"internalType": "uint256",
				"name": "feeGrowthInside1LastX128",
				"type": "uint256"
			},
			{
				"internalType": "uint128",
				"name": "tokensOwed0",
				"type": "uint128"
			},
			{
				"internalType": "uint128",
				"name": "tokensOwed1",
				"type": "uint128"
			}
		],
		"stateMutability": "view",
		"type": "function"
	}
]

if __name__ == "__main__":
	initialize_db()
	while True:
		for user in get_users():
			if user.wallet:
				try:
					# wallet = '0x3e4C0f29D9978458821025ec56e30086A5A70B01'
					wallet = Web3.to_checksum_address(user.wallet)
					nft_manager_contract = web3.eth.contract(address=nft_manager_address, abi=nft_manager_abi)
					logger.info(f"Checking NFT balance for wallet: {wallet}")
					# add_message(user.chat_id, f'⚙️ Checking NFT balance for wallet: {wallet}')
					balance = nft_manager_contract.functions.balanceOf(wallet).call()
					logger.info(f"NFT balance: {balance}")

					if balance > 0:
						logger.info("✅ Retrieving active positions...")
						# add_message('⚙️ Retrieving active positions...')
						positions_to_parse = min(balance, 5)  # Ограничение на количество позиций
						for i in range(balance - 1, balance - positions_to_parse - 1, -1): # Парсинг от новых позиций к старым
							token_id = nft_manager_contract.functions.tokenOfOwnerByIndex(wallet, i).call()
							if isinstance(token_id, int) and token_id >= 0:
								position = nft_manager_contract.functions.positions(token_id).call()
								logger.info(f"Checking position for Token ID: {token_id}")
								liquidity = position[7]
								if liquidity > 0:
									if add_token(int(token_id), False, liquidity, True):
										add_message(user.chat_id, f'✅ New position added: ' + str(token_id))
										connect_user_token(user.chat_id, int(token_id))
							else:
								logger.error(f"Invalid Token ID: {token_id}")
								# user, created = User.get_or_create(chat_id=update.effective_chat.id)
								# UserToken.create(user.chat_id, int(token_id))

								
								# token_id, is_manual, liquidity, is_in_range
								# просто добавляем в базу данных - ликв не важна
								# if res:
								# 	add_message(user.chat_id, res)
							#     token0 = position[2]
							#     token1 = position[3]
							#     fee = position[4]
							#     tick_lower = position[5]
							#     tick_upper = position[6]
							#     tokens_owed_0 = position[10]
							#     tokens_owed_1 = position[11]
							#     logger.info(f"Active position found for Token ID: {token_id}")
							#     logger.info(f"  Token 0: {token0}")
							#     logger.info(f"  Token 1: {token1}")
							#     logger.info(f"  Fee tier: {fee/10000}%")
							#     logger.info(f"  Tick range: [{tick_lower}, {tick_upper}]")
							#     logger.info(f"  Liquidity: {liquidity}")
							#     logger.info(f"  Tokens owed: {tokens_owed_0} {token0}, {tokens_owed_1} {token1}")
							# else:
							#     logger.info(f"No active liquidity for Token ID: {token_id}")
					else:
						logger.info("No positions found for this wallet")
				except Exception as e:
					logger.error(f"An error occurred: {e}")

		logger.info("✨ Sleeping for 10 seconds...")
		time.sleep(10)