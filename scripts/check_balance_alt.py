"""Check ETH balance on Arbitrum Sepolia via multiple fallback RPCs."""
import json
import urllib.request

WALLET = "0x6164641bE1E09C67C9335BB38448A139e93B8722"
RPCS = [
    "https://arbitrum-sepolia.blockpi.network/v1/rpc/public",
    "https://arbitrum-sepolia.public.blastapi.io",
    "https://sepolia-rollup.arbitrum.io/rpc",
]

payload = json.dumps({
    "jsonrpc": "2.0",
    "method": "eth_getBalance",
    "params": [WALLET, "latest"],
    "id": 1
}).encode()

for rpc in RPCS:
    try:
        req = urllib.request.Request(
            rpc, data=payload,
            headers={"Content-Type": "application/json",
                     "User-Agent": "ArbiSense/0.1"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
        balance_wei = int(result["result"], 16)
        balance_eth = balance_wei / 1e18
        print(f"RPC: {rpc}")
        print(f"Wallet:  {WALLET}")
        print(f"Balance: {balance_eth:.6f} ETH")
        if balance_eth < 0.001:
            print("NOTICE: Need testnet ETH from faucet")
        else:
            print("OK: Sufficient for deployment")
        break
    except Exception as exc:
        print(f"Failed {rpc}: {exc}")
