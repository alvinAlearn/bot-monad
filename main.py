import yaml
import time
import logging
from web3 import Web3

# Load config
with open('config.yaml') as f:
    config = yaml.safe_load(f)

RPC_URL = config['rpc_url']
PRIVATE_KEY = config['private_key']
ROUTER_ADDRESS = Web3.to_checksum_address(config['router_address'])
TOKEN_CONTRACTS = config['token_contracts']

w3 = Web3(Web3.HTTPProvider(RPC_URL))
account = w3.eth.account.from_key(PRIVATE_KEY)
address = account.address

# Router ABI Minimal
ROUTER_ABI = config['router_abi']

router = w3.eth.contract(address=ROUTER_ADDRESS, abi=ROUTER_ABI)

# ERC20 ABI Minimal
ERC20_ABI = [
    {"constant":True,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"},
    {"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"},
    {"constant":False,"inputs":[{"name":"_spender","type":"address"},{"name":"_value","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"type":"function"},
]

# Setup logging
logging.basicConfig(filename='logs/swap_log.txt', level=logging.INFO, format='%(asctime)s %(message)s')

def swap_mon_to_token(token_address, amount_in_wei):
    try:
        tx = router.functions.swapExactETHForTokens(
            0,  # amountOutMin
            [Web3.to_checksum_address("0x0000000000000000000000000000000000000000"), Web3.to_checksum_address(token_address)],
            address,
            int(time.time()) + 600
        ).build_transaction({
            'from': address,
            'value': amount_in_wei,
            'nonce': w3.eth.get_transaction_count(address),
            'gas': 300000,
            'gasPrice': w3.eth.gas_price,
        })

        signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        logging.info(f"Swap MON -> {token_address} | TX Hash: {tx_hash.hex()}")
        print(f"Swap MON -> {token_address} | TX: {tx_hash.hex()}")
    except Exception as e:
        logging.error(f"Error swap to {token_address}: {e}")
        print(f"Error swap to {token_address}: {e}")

def swap_token_to_mon(token_address, amount_token):
    try:
        token = w3.eth.contract(address=Web3.to_checksum_address(token_address), abi=ERC20_ABI)
        decimals = token.functions.decimals().call()
        amount_in = int(amount_token * (10 ** decimals))

        approve_tx = token.functions.approve(
            ROUTER_ADDRESS,
            amount_in
        ).build_transaction({
            'from': address,
            'nonce': w3.eth.get_transaction_count(address),
            'gas': 100000,
            'gasPrice': w3.eth.gas_price,
        })

        signed_approve = w3.eth.account.sign_transaction(approve_tx, PRIVATE_KEY)
        approve_tx_hash = w3.eth.send_raw_transaction(signed_approve.rawTransaction)
        w3.eth.wait_for_transaction_receipt(approve_tx_hash)
        print(f"Approve {token_address} | TX: {approve_tx_hash.hex()}")

        tx = router.functions.swapExactTokensForETH(
            amount_in,
            0,
            [Web3.to_checksum_address(token_address), Web3.to_checksum_address("0x0000000000000000000000000000000000000000")],
            address,
            int(time.time()) + 600
        ).build_transaction({
            'from': address,
            'nonce': w3.eth.get_transaction_count(address),
            'gas': 300000,
            'gasPrice': w3.eth.gas_price,
        })

        signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        logging.info(f"Swap {token_address} -> MON | TX Hash: {tx_hash.hex()}")
        print(f"Swap {token_address} -> MON | TX: {tx_hash.hex()}")
    except Exception as e:
        logging.error(f"Error swap from {token_address}: {e}")
        print(f"Error swap from {token_address}: {e}")

if __name__ == "__main__":
    amount_mon = w3.to_wei(config['amount_mon_to_swap'], 'ether')
    amount_token = config['amount_token_to_swap']

    print(f"Starting swap for {len(TOKEN_CONTRACTS)} tokens...")

    for token in TOKEN_CONTRACTS:
        swap_mon_to_token(token, amount_mon)
        time.sleep(config['delay_between_swaps'])

    print("Swap completed.")
