/**
 * deploy.js — Deploy SentinelRegistry to Arbitrum Sepolia
 *
 * Usage:
 *   npx hardhat run scripts/deploy.js --network arbitrumSepolia
 *
 * The script reads WALLET_ADDRESS from ../.env as the agent address,
 * deploys SentinelRegistry, then writes the contract address to
 * ../arbisense/.env so the Python agent can pick it up.
 */
const { ethers } = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  const [deployer] = await ethers.getSigners();
  console.log("Deployer:", deployer.address);

  // The agent wallet is the same as the deployer for this demo.
  // In production you would use a separate agent wallet.
  const agentAddress = deployer.address;

  console.log("Deploying SentinelRegistry with agent:", agentAddress);

  const Registry = await ethers.getContractFactory("SentinelRegistry");
  const registry = await Registry.deploy(agentAddress);
  await registry.waitForDeployment();

  const address = await registry.getAddress();
  console.log("SentinelRegistry deployed to:", address);

  // Write address to .env file for Python agent
  const envPath = path.join(__dirname, "../arbisense/.env");
  const envLine = `SENTINEL_CONTRACT=${address}\n`;

  if (fs.existsSync(envPath)) {
    const existing = fs.readFileSync(envPath, "utf8");
    const filtered = existing
      .split("\n")
      .filter((l) => !l.startsWith("SENTINEL_CONTRACT="))
      .join("\n");
    fs.writeFileSync(envPath, filtered.trimEnd() + "\n" + envLine);
  } else {
    fs.writeFileSync(envPath, envLine);
  }

  console.log(`Contract address written to arbisense/.env`);
  console.log("Verify with:");
  console.log(
    `  npx hardhat verify --network arbitrumSepolia ${address} ${agentAddress}`
  );
}

main().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});
