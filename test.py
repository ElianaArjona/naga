from web3 import Web3
import os
from dotenv import load_dotenv

# Load .env variables
load_dotenv()
API_KEY = os.getenv("ALCHEMY_API_KEY")
if not API_KEY:
    raise ValueError("Missing ALCHEMY_API_KEY")

RPC_URL = f"https://eth-sepolia.g.alchemy.com/v2/{API_KEY}"
web3 = Web3(Web3.HTTPProvider(RPC_URL))

if not web3.is_connected():
    raise ConnectionError("❌ No connection to Sepolia RPC")
print("✅ Connected to Sepolia")

# Event signature hashes
TRANSFER_SIG = web3.keccak(text="Transfer(address,address,uint256)").hex()
UNIV2_SWAP_SIG = web3.keccak(text="Swap(address,uint256,uint256,uint256,uint256,address)").hex()
UNIV3_SWAP_SIG = web3.keccak(text="Swap(address,address,int256,int256,uint160,uint128,int24)").hex()

BLOCK_LOOKBACK = 5
current_block = web3.eth.block_number
found = False

for block_num in range(current_block, current_block - BLOCK_LOOKBACK, -1):
    block = web3.eth.get_block(block_num, full_transactions=True)
    print(f"\n🔍 Scanning block {block.number} ({len(block.transactions)} txs)")

    for tx in block.transactions:
        try:
            receipt = web3.eth.get_transaction_receipt(tx.hash)
            if not receipt.logs:
                continue

            for log in receipt.logs:
                topic0 = log.topics[0].hex()

                # ✅ ERC-20 Transfer
                if topic0 == TRANSFER_SIG and len(log.topics) >= 3:
                    from_addr = "0x" + log.topics[1].hex()[-40:]
                    to_addr = "0x" + log.topics[2].hex()[-40:]
                    amount = int(log.data.hex(), 16)

                    print("\n✅ ERC-20 Transfer:")
                    print(f"→ Token Contract : {log.address}")
                    print(f"→ From           : {from_addr}")
                    print(f"→ To             : {to_addr}")
                    print(f"→ Amount         : {amount} tokens")
                    found = True

                # 🟣 Uniswap V2 Swap
                elif topic0 == UNIV2_SWAP_SIG:
                    print("\n🟣 Uniswap V2 Swap:")
                    print(f"→ Pool Contract  : {log.address}")
                    print(f"→ Topics         : {[t.hex() for t in log.topics]}")
                    print(f"→ Data           : {log.data.hex()}")
                    found = True

                # 🔵 Uniswap V3 Swap
                elif topic0 == UNIV3_SWAP_SIG:
                    print("\n🔵 Uniswap V3 Swap:")
                    print(f"→ Pool Contract  : {log.address}")
                    print(f"→ Topics         : {[t.hex() for t in log.topics]}")
                    print(f"→ Data           : {log.data.hex()}")
                    found = True

                # ❓ Unknown log
                else:
                    print("\n📦 Unknown Log:")
                    print(f"→ Contract       : {log.address}")
                    print(f"→ Topics         : {[t.hex() for t in log.topics]}")
                    print(f"→ Data (raw)     : {log.data}")
        except Exception as e:
            print(f"⚠️ Error in tx {tx.hash.hex()}: {e}")

if not found:
    print("⚠️ No logs of interest found in last blocks.")
