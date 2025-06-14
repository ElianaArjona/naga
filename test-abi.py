from web3 import Web3
from dotenv import load_dotenv
import os

# Load API key from .env
load_dotenv()
API_KEY = os.getenv("ALCHEMY_API_KEY")
RPC_URL = f"https://eth-mainnet.g.alchemy.com/v2/{API_KEY}"
web3 = Web3(Web3.HTTPProvider(RPC_URL))

if not web3.is_connected():
    raise Exception("❌ Could not connect to Ethereum mainnet")

# Transaction hash to inspect (you can change this)
tx_hash = "0x0410bf886236e8c9f457fd052ae7fbdb20a6e78e43a1c3b7506a8fb1c3dda75e"
receipt = web3.eth.get_transaction_receipt(tx_hash)

# ERC-20 Transfer event signature
TRANSFER_SIG = web3.keccak(text="Transfer(address,address,uint256)").hex()

# ERC-20 interface fragment for symbol & decimals
erc20_abi = [
    {
        "constant": True,
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function",
    },
]

print(f"\n🔍 Analyzing transaction: {tx_hash}")
print(f"🧾 Logs found: {len(receipt.logs)}")

for i, log in enumerate(receipt.logs):
    if not log.topics:
        continue

    topic0 = log.topics[0].hex()

    if topic0 == TRANSFER_SIG:
        try:
            token_contract = web3.eth.contract(address=log.address, abi=erc20_abi)
            symbol = token_contract.functions.symbol().call()
            decimals = token_contract.functions.decimals().call()
        except Exception:
            symbol = "UNKNOWN"
            decimals = 18

        from_addr = "0x" + log.topics[1].hex()[-40:]
        to_addr = "0x" + log.topics[2].hex()[-40:]
        amount = int.from_bytes(log.data, byteorder='big') / (10 ** decimals)

        print(f"\n🔁 Transfer #{i+1}")
        print(f"→ Token: {symbol} ({log.address})")
        print(f"→ From : {from_addr}")
        print(f"→ To   : {to_addr}")
        print(f"→ Amount: {amount:,.6f} {symbol}")

    else:
        continue
