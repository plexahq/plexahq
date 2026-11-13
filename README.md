# Plexa

An MCP gateway that connects AI assistants (Claude, ChatGPT, Cursor, VS Code…) to **LayerZero's Zero chain**, other EVM chains and LayerZero's cross-chain messaging network.

Ask your assistant things like *"what's in this wallet?"*, *"what does this contract do?"*, *"is this approval safe to sign?"* or *"where is my bridge transfer?"* and it answers from live chain data.

> Status: v0.1, read-only. Nothing is ever signed or broadcast. Zero mainnet support switches on with one environment variable once LayerZero publishes its RPC (launch: 2026-11-30).

## Tools

| Tool | What it does |
|---|---|
| `list_chains` | Chains Plexa can reach, their chain IDs, LayerZero EIDs and whether an RPC is configured |
| `get_balance` | Native balance plus any ERC-20 balances |
| `get_token_info` | Name, symbol, decimals, total supply |
| `get_block` | Latest or a specific block |
| `get_transaction` | Status, fee, decoded call and token transfers of a transaction |
| `read_contract` | Calls any view function from a Solidity signature |
| `get_contract_info` | Contract vs wallet (incl. EIP-7702 delegated wallets), proxy detection, verified name, functions and source via Sourcify |
| `simulate_transaction` | Dry-runs a transaction: succeed/revert, fee, plain-language explanation and risk warnings (unlimited approvals, approvals to plain wallets, tokens sent to the token contract…) |
| `lz_chain_info` | LayerZero deployment registry lookup: EID, EndpointV2, libraries, executor, active DVNs |
| `lz_track_message` | Tracks a cross-chain message by source tx hash, names the DVNs and explains stuck states |
| `lz_list_messages` | Recent LayerZero messages for a wallet or an OApp |

Built-in chains: Zero (ATLAS and Interop zones, placeholders until launch), Ethereum, Arbitrum, Base, HyperEVM, and the Sepolia testnets of Ethereum, Arbitrum and Base.

## Quick start

Requires Node.js 22.12+.

```bash
npm install
npm run build
```

### Local (stdio): Claude Code

```bash
claude mcp add plexa -- node /absolute/path/to/plexahq/dist/stdio.js
```

### Local (stdio): Claude Desktop, Cursor, VS Code

```json
{
  "mcpServers": {
    "plexa": {
      "command": "node",
      "args": ["/absolute/path/to/plexahq/dist/stdio.js"]
    }
  }
}
```

### Remote on Vercel

The repo deploys to Vercel as-is: `vercel.json` builds `dist/`, serves the landing page from `public/` and runs `api/mcp.js` and `api/health.js` as functions.

1. In Vercel, **Add New → Project** and import `plexahq/plexahq`. Leave the framework preset as **Other**; the settings come from `vercel.json`.
2. Optionally add environment variables (see [Configuration](#configuration)).
3. Deploy. The MCP URL is `https://<project>.vercel.app/mcp`.

Every push to the production branch redeploys automatically.

### Remote on any Node host (Docker, Railway, Fly.io, a VPS)

```bash
HOST=0.0.0.0 PORT=3000 npm start
```

The MCP endpoint is `POST /mcp`, the health check is `GET /health`. The server is stateless, so it scales horizontally. Clients that support remote MCP servers connect with the URL alone, e.g.:

```bash
claude mcp add --transport http plexa https://your-host.example/mcp
```

## Configuration

All configuration is through environment variables (see `.env.example`).

| Variable | Purpose |
|---|---|
| `PLEXA_RPC_<CHAIN>` | RPC URL for a chain, e.g. `PLEXA_RPC_ZERO_ATLAS`, `PLEXA_RPC_BASE` |
| `PLEXA_CHAIN_ID_<CHAIN>` | Chain ID (otherwise read from the RPC) |
| `PLEXA_EXPLORER_<CHAIN>` | Block explorer base URL |
| `PLEXA_EXTRA_CHAINS` | JSON array of extra chains: `[{"key":"mychain","name":"My Chain","rpcUrl":"https://…"}]` |
| `PORT`, `HOST` | HTTP server bind address (default `127.0.0.1:3000`) |

`<CHAIN>` is the chain key upper-cased with dashes turned into underscores (`zero-atlas` → `ZERO_ATLAS`).

### Enabling Zero on launch day

```bash
PLEXA_RPC_ZERO_ATLAS=https://<zero-atlas-rpc> \
PLEXA_RPC_ZERO_INTEROP=https://<zero-interop-rpc> \
npm start
```

LayerZero's metadata API already lists the zones as `zeroatlas` and `zerointerop` (EVM, gas token ZRO). The testnet entries there use chain ID 1337 and contract addresses that match local Hardhat/Anvil defaults, so they look like internal devnets rather than public testnets; Plexa does not hard-code them.

## Development

```bash
npm run typecheck
npm test              # unit tests
npm run test:live     # calls real chains and LayerZero APIs
npm run dev:http      # HTTP server with tsx
```

Behind an HTTP proxy, run Node with `NODE_USE_ENV_PROXY=1` so `fetch` uses `HTTPS_PROXY`.

## Roadmap

- [x] Read, inspect and simulate on EVM chains
- [x] LayerZero chain registry, message tracking
- [ ] Zero mainnet RPC (on launch, 2026-11-30)
- [ ] Unsigned transaction builder + signing page (user signs in their own wallet)
- [ ] OFT bridging: quote and build cross-chain sends
- [ ] OApp security review: DVN / executor configuration per pathway
- [ ] lzATLAS market data once its API is public
- [ ] Agent wallets with spend limits, allow-lists and expiry
