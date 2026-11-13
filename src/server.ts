import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { ChainRegistry, loadChains } from "./chains.js";
import { registerEvmTools } from "./tools/evm.js";
import { registerLayerZeroTools } from "./tools/layerzero.js";

export const VERSION = "0.1.0";

const INSTRUCTIONS = `Plexa connects you to LayerZero's Zero chain and other EVM chains, plus LayerZero's cross-chain messaging network.

- Every tool is read-only: nothing is ever signed or broadcast.
- Call list_chains to see which chains are available and which have an RPC configured.
- Before suggesting that a user sign any transaction, call simulate_transaction and relay its explanation and warnings in plain language.
- Use get_contract_info to explain what an unknown contract is before interacting with it.
- For bridging and cross-chain questions, use lz_track_message (by source tx hash), lz_list_messages, lz_latest_messages and lz_chain_info.
- Report token amounts in human units with their symbol, and link explorer / LayerZero Scan URLs when available.`;

export function createServer(registry: ChainRegistry = new ChainRegistry(loadChains())): McpServer {
  const server = new McpServer({ name: "plexa", version: VERSION }, { instructions: INSTRUCTIONS });
  registerEvmTools(server, registry);
  registerLayerZeroTools(server, registry);
  return server;
}
