# gcheck wallet for nfts

from web3 import Web3
import logging
from logging.handlers import RotatingFileHandler
import time
import json

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
ethereum_url = 'https://rpc.ankr.com/eth/' + ankr_token
optim_url = 'https://rpc.ankr.com/optimism/' + ankr_token
arbit_url = 'https://rpc.ankr.com/arbitrum/' + ankr_token
base_url = 'https://rpc.ankr.com/base/' + ankr_token

ethereum_nft_position_manager_address = Web3.to_checksum_address('0xc36442b4a4522e871399cd717abdd847ab11fe88')
optim_nft_position_manager_address = Web3.to_checksum_address('0xc36442b4a4522e871399cd717abdd847ab11fe88')
arbit_nft_position_manager_address = Web3.to_checksum_address('0xc36442b4a4522e871399cd717abdd847ab11fe88')
base_nft_position_manager_address = Web3.to_checksum_address('0x03a520b32c04bf3beef7beb72e919cf822ed34f1')
eth_factory_address = Web3.to_checksum_address('0x1F98431c8aD98523631AE4a59f267346ea31F984')
base_factory_address = Web3.to_checksum_address('0x33128a8fC17869897dcE68Ed026d694621f6FDfD')

networks = ['optimism', 'arbitrum', 'ethereum', 'base']

with open('./optim_nft_position_manager_abi.json', 'r') as w:
	optim_nft_position_manager_abi = json.load(w)
with open('./arbit_nft_position_manager_abi.json', 'r') as w:
	arbit_nft_position_manager_abi = json.load(w)
with open('./base_nft_position_manager_abi.json', 'r') as w:
	base_nft_position_manager_abi = json.load(w)
with open('./eth_factory.json', 'r') as file:
	eth_factory_abi = json.load(file)
with open('./base_factory.json', 'r') as file:
	base_factory_abi = json.load(file)

if __name__ == "__main__":
	initialize_db()
	while True:
		for user in get_users():
			if user.wallet:
				for network in networks:
					wallet = Web3.to_checksum_address(user.wallet)
					if (network == 'optimism'):
						rpc_url = optim_url
						nft_position_manager_address = optim_nft_position_manager_address
						nft_position_manager_abi = optim_nft_position_manager_abi
						factory_address = eth_factory_address
						factory_address_abi = eth_factory_abi
						# pool_abi = optim_pool_abi
						# pool_address = optim_pool_address
					elif (network == 'arbitrum'):
						rpc_url = arbit_url
						nft_position_manager_address = arbit_nft_position_manager_address
						nft_position_manager_abi = arbit_nft_position_manager_abi
						factory_address = eth_factory_address
						factory_address_abi = eth_factory_abi
						# pool_abi = arbit_pool_abi
						# pool_address = arbit_pool_address
					elif (network == 'ethereum'):
						rpc_url = ethereum_url
						nft_position_manager_address = optim_nft_position_manager_address
						nft_position_manager_abi = optim_nft_position_manager_abi
						factory_address = eth_factory_address
						factory_address_abi = eth_factory_abi
						# pool_abi = arbit_pool_abi
						# pool_address = arbit_pool_address
					elif (network == 'base'):
						rpc_url = base_url
						nft_position_manager_address = base_nft_position_manager_address
						nft_position_manager_abi = base_nft_position_manager_abi
						factory_address = base_factory_address
						factory_address_abi = base_factory_abi
						# pool_abi = base_pool_abi
						# pool_address = base_pool_address
					try:
						web3 = Web3(Web3.HTTPProvider(rpc_url))
						factory_contract = web3.eth.contract(address=factory_address, abi=factory_address_abi)
						# wallet = '0x3e4C0f29D9978458821025ec56e30086A5A70B01'
						nft_manager_contract = web3.eth.contract(address=nft_position_manager_address, abi=nft_position_manager_abi)
						logger.info(f"Checking NFT balance for wallet: {wallet} @ {network}...")
						# add_message(user.chat_id, f'⚙️ Checking NFT balance for wallet: {wallet}')
						balance = nft_manager_contract.functions.balanceOf(wallet).call()
						logger.info(f"NFT balance: {balance}")

						if balance > 0:
							logger.info("⏱️ Retrieving active positions ...")
							# add_message('⚙️ Retrieving active positions...')
							positions_to_parse = min(balance, 5)  # Ограничение на количество позиций
							for i in range(balance - 1, balance - positions_to_parse - 1, -1): # Парсинг от новых позиций к старым
								token_id = nft_manager_contract.functions.tokenOfOwnerByIndex(wallet, i).call()
								if isinstance(token_id, int) and token_id >= 0:
									position = nft_manager_contract.functions.positions(token_id).call()
									logger.info(f"Checking position for Token ID: {token_id}")
									token_a = position[2]
									token_b = position[3]
									fee = position[4]
									liquidity = position[7]
									pair_pool = factory_contract.functions.getPool(token_a, token_b, fee).call()
									if liquidity > 0:
										if add_token(int(token_id), False, liquidity, True, network, pair_pool):
											network_log = network
											if network == 'ethereum':
												network_log = 'mainnet'
											add_message(user.chat_id, f'✅ New position added @ {network}: [{token_id}](https://app.uniswap.org/pool/{token_id}?chain={network_log}).')
											connect_user_token(user.chat_id, int(token_id))
											
								else:
									logger.error(f"Invalid Token ID: {token_id}")
									
						else:
							logger.info("No positions found for this wallet")
					except Exception as e:
						logger.error(f"An error occurred: {e}")

		logger.info("✨ Sleeping for 10 seconds...")
		time.sleep(10)