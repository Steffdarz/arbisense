"""Check ETH balance on Arbitrum Sepolia."""
import json
import urllib.request

RPC = "https://sepolia-rollup.arbitrum.io/rpc"
WALLET = "0x6164641bE1E09C67C9335BB38448A139e93B8722"

payload = json.dumps({
    "jsonrpc": "2.0",
    "method": "eth_getBalance",
    "params": [WALLET, "latest"],
    "id": 1
}).encode()

req = urllib.request.Request(RPC, data=payload,
                              headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=10) as resp:
    result = json.loads(resp.read())

balance_wei = int(result["result"], 16)
balance_eth = balance_wei / 1e18
print(f"Wallet:  {WALLET}")
print(f"Network: Arbitrum Sepolia (chainId 421614)")
print(f"Balance: {balance_eth:.6f} ETH")
if balance_eth < 0.001:
    print("WARNING: Insufficient ETH — need testnet ETH from faucet before deploying")
else:
    print("OK: Sufficient ETH for deployment")
