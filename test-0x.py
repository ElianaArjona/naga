from web3 import Web3
import os
from dotenv import load_dotenv

# Load API key from .env
load_dotenv()
API_KEY = os.getenv("ALCHEMY_API_KEY")
RPC_URL = f"https://eth-mainnet.g.alchemy.com/v2/{API_KEY}"
web3 = Web3(Web3.HTTPProvider(RPC_URL))

if not web3.is_connected():
    raise Exception("❌ Could not connect to Ethereum mainnet")

# Transaction hash provided
tx_hash = "0x25477219465fb7cbb7591c435315f9732f86ba1ba171bda1acef40441042c503"

# Event signatures (0x protocol)
BRIDGE_FILL_SIG = web3.keccak(text="BridgeFill(address,address,address,address,address,uint256,uint256,uint256)").hex()
FILL_SIG = web3.keccak(text="Fill(address,address,address,address,address,uint256,uint256,uint256,uint256,bytes32)").hex()

receipt = web3.eth.get_transaction_receipt(tx_hash)

bridge_routes = []
fill_routes = []

print(f"🔎 Checking logs for tx: {tx_hash}")
print(f"Block: {receipt.blockNumber} | Logs found: {len(receipt.logs)}")

for i, log in enumerate(receipt.logs):
    print(f"\n--- Log #{i+1} ---")
    print(f"Contract: {log.address}")

    if not log.topics:
        print("⚠️ No topics — skipping this log (likely internal transfer or unknown event).")
        continue

    sig = log.topics[0].hex()

    if sig == BRIDGE_FILL_SIG:
        print("🔁 BridgeFill detected (0x routed to an external DEX)")
        bridge_routes.append(log.address)

    elif sig == FILL_SIG:
        print("📄 Fill detected (0x filled via RFQ / Limit Order)")
        fill_routes.append(log.address)

    else:
        print("📎 Other event — not a 0x BridgeFill or Fill")


# Final result
if len(bridge_routes) + len(fill_routes) > 1:
    print("\n✅ This was a multi-route swap!")
else:
    print("\n🔂 This was a single-route or single-AMM swap.")

if bridge_routes:
    print(f"\n🌉 BridgeFill contracts used:\n- " + "\n- ".join(set(bridge_routes)))

if fill_routes:
    print(f"\n🧾 Fill contracts used:\n- " + "\n- ".join(set(fill_routes)))
