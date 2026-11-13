import { esc } from "../mcp";

interface Input { name: string; type: string; required?: boolean; desc: string }
interface ToolDoc { name: string; group: string; desc: string; inputs: Input[]; ask: string; example: Record<string, unknown> }

const CHAIN: Input = { name: "chain", type: "string", required: true, desc: "Chain key (base, ethereum, arbitrum, hyperevm, zero-atlas…) or numeric chain ID" };
const NETWORK: Input = { name: "network", type: '"mainnet" | "testnet"', desc: 'LayerZero network, default "mainnet"' };

const TOOLS: ToolDoc[] = [
  { name: "list_chains", group: "Read", desc: "Every chain Plexa can reach, with chain IDs, LayerZero endpoint IDs and whether an RPC is configured.", inputs: [], ask: "Which chains can you read?", example: {} },
  { name: "get_balance", group: "Read", desc: "Native balance of an address and, optionally, its ERC-20 balances.", inputs: [CHAIN, { name: "address", type: "address", required: true, desc: "Wallet or contract address" }, { name: "tokens", type: "address[]", desc: "Up to 25 ERC-20 token addresses" }], ask: "What's in 0xd8dA…6045 on Base?", example: { chain: "base", address: "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045", tokens: ["0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"] } },
  { name: "get_token_info", group: "Read", desc: "Name, symbol, decimals and total supply of an ERC-20 token.", inputs: [CHAIN, { name: "token", type: "address", required: true, desc: "Token contract address" }], ask: "How many USDC exist on Arbitrum?", example: { chain: "arbitrum", token: "0xaf88d065e77c8cC2239327C5EDb3A432268e5831" } },
  { name: "get_block", group: "Read", desc: "A block's number, hash, timestamp, transaction count and gas usage.", inputs: [CHAIN, { name: "block", type: 'number | "latest"', desc: "Defaults to the latest block" }], ask: "What's the latest block on HyperEVM?", example: { chain: "hyperevm" } },
  { name: "get_transaction", group: "Read", desc: "Status, fee, decoded call (verified or ERC-20) and the token transfers a transaction caused.", inputs: [CHAIN, { name: "hash", type: "tx hash", required: true, desc: "0x-prefixed transaction hash" }], ask: "What did this transaction do?", example: { chain: "base", hash: "0x…" } },
  { name: "read_contract", group: "Inspect", desc: "Calls any read-only function from a Solidity signature. Large integers go in as strings.", inputs: [CHAIN, { name: "address", type: "address", required: true, desc: "Contract address" }, { name: "function", type: "string", required: true, desc: 'Signature, e.g. "balanceOf(address) view returns (uint256)"' }, { name: "args", type: "array", desc: "Arguments in order" }, { name: "blockNumber", type: "number", desc: "Read historical state" }], ask: "Read totalSupply() on this contract.", example: { chain: "base", address: "0x8335…2913", function: "totalSupply() view returns (uint256)" } },
  { name: "get_contract_info", group: "Inspect", desc: "Contract or wallet (incl. EIP-7702 smart wallets), proxy and implementation, verified name, compiler, functions and events via Sourcify.", inputs: [CHAIN, { name: "address", type: "address", required: true, desc: "Address to inspect" }, { name: "includeSource", type: "boolean", desc: "Include verified source (truncated)" }], ask: "What is this contract, and is it verified?", example: { chain: "arbitrum", address: "0x1a44076050125825900e736c501f859c50fe728c" } },
  { name: "simulate_transaction", group: "Protect", desc: "Dry-runs a transaction on live state: succeed or revert (with reason), fee, plain-language explanation and drainer warnings. Never broadcasts.", inputs: [CHAIN, { name: "to", type: "address", required: true, desc: "Recipient or contract" }, { name: "from", type: "address", desc: "Sender; many calls revert without it" }, { name: "data", type: "hex", desc: "Calldata; omit for a plain transfer" }, { name: "value", type: "string", desc: 'Native amount in whole units, e.g. "0.05"' }], ask: "Is this approval safe to sign?", example: { chain: "base", to: "0x8335…2913", from: "0xd8dA…6045", data: "0x095ea7b3…" } },
  { name: "lz_track_message", group: "LayerZero", desc: "Tracks the message(s) a source transaction created: status in plain words, each DVN by name, delivery time and Scan link.", inputs: [{ name: "txHash", type: "tx hash", required: true, desc: "Source-chain transaction hash" }, NETWORK], ask: "Where is my bridge transfer?", example: { txHash: "0x…" } },
  { name: "lz_latest_messages", group: "LayerZero", desc: "The most recent messages across the whole LayerZero network.", inputs: [{ name: "limit", type: "1–50", desc: "Default 10" }, NETWORK], ask: "What's happening on LayerZero right now?", example: { limit: 10 } },
  { name: "lz_list_messages", group: "LayerZero", desc: "Recent messages sent by a wallet, or handled by an OApp when oappEid is given.", inputs: [{ name: "address", type: "address", required: true, desc: "Wallet or OApp address" }, { name: "oappEid", type: "number", desc: "Treat address as an OApp on this EID" }, { name: "limit", type: "1–50", desc: "Default 10" }, NETWORK], ask: "Show my last five bridge transfers.", example: { address: "0x…", limit: 5 } },
  { name: "lz_chain_info", group: "LayerZero", desc: "LayerZero's official registry: EID, EndpointV2, message libraries, executor and active DVNs for a chain.", inputs: [{ name: "query", type: "string", required: true, desc: 'Chain key, chain ID, EID or name fragment, e.g. "zero"' }], ask: "Which DVNs run on Base?", example: { query: "base" } },
];

export function initDocs() {
  const ref = document.getElementById("tool-ref");
  if (ref) {
    ref.innerHTML = TOOLS.map(
      (t) => `<article class="tool-doc" id="tool-${t.name}">
        <header><code class="tool-doc-n">${t.name}</code><span class="pill">${esc(t.group)}</span></header>
        <p>${esc(t.desc)}</p>
        ${t.inputs.length ? `<div class="table-wrap"><table class="table params"><thead><tr><th>Input</th><th>Type</th><th>Description</th></tr></thead><tbody>${t.inputs.map((i) => `<tr><td><code>${i.name}</code>${i.required ? ' <span class="req">required</span>' : ""}</td><td>${esc(i.type)}</td><td>${esc(i.desc)}</td></tr>`).join("")}</tbody></table></div>` : `<p class="muted">No inputs.</p>`}
        <p class="ask">Ask: <i>"${esc(t.ask)}"</i></p>
        <pre class="code"><code>${esc(JSON.stringify({ name: t.name, arguments: t.example }, null, 2))}</code></pre>
      </article>`,
    ).join("");
  }

  // "On this page" and scroll-spy
  const sections = [...document.querySelectorAll<HTMLElement>("#doc > section")];
  const toc = document.getElementById("toc")!;
  const crumb = document.getElementById("crumb")!;
  toc.innerHTML = sections.map((s) => `<a href="#${s.id}">${esc(s.querySelector("h1, h2")?.textContent ?? s.id)}</a>`).join("");
  const sideLinks = [...document.querySelectorAll<HTMLAnchorElement>(".docs-side a, #toc a")];
  const setActive = (id: string) => {
    for (const a of sideLinks) a.classList.toggle("on", a.getAttribute("href") === `#${id}`);
    const s = document.getElementById(id);
    crumb.textContent = s?.querySelector("h1, h2")?.textContent ?? "";
  };
  const io = new IntersectionObserver(
    (entries) => {
      const visible = entries.filter((e) => e.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0];
      if (visible) setActive(visible.target.id);
    },
    { rootMargin: "-20% 0px -70% 0px" },
  );
  sections.forEach((s) => io.observe(s));
  setActive(location.hash.slice(1) || "overview");
}
