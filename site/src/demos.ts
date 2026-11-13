import { ago, callTool, esc, mcpUrl, short } from "./mcp";
import { appName, chainName, ZERO_AT_DEFAULT } from "./live";

const VITALIK = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045";
const USDC: Record<string, string> = {
  base: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
  ethereum: "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
  arbitrum: "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
};
const MAX = "f".repeat(64);
const pad = (hex: string) => hex.replace(/^0x/, "").toLowerCase().padStart(64, "0");
const $ = <T extends HTMLElement = HTMLElement>(s: string, root: ParentNode = document) => root.querySelector<T>(s)!;
const $$ = <T extends HTMLElement = HTMLElement>(s: string, root: ParentNode = document) => [...root.querySelectorAll<T>(s)];
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
const shortAddrs = (t: string) => t.replace(/0x[0-9a-fA-F]{40}/g, (m) => short(m));

/* ---------------------------------------------------------------- copy + connect */

async function copyText(btn: HTMLElement, text: string) {
  try {
    await navigator.clipboard.writeText(text);
    btn.textContent = "Copied";
    btn.classList.add("done");
  } catch {
    btn.textContent = "Press ⌘C";
  }
  setTimeout(() => {
    btn.textContent = "Copy";
    btn.classList.remove("done");
  }, 1600);
}

export function initConnect() {
  const url = mcpUrl();
  $$(".js-mcp-url").forEach((el) => (el.textContent = url));
  $$("[data-template]").forEach((el) => (el.textContent = el.dataset.template!.replace("{url}", url)));
  $$("[data-copy-mcp]").forEach((b) => b.addEventListener("click", () => copyText(b, url)));
  $$("[data-copy-code]").forEach((b) => b.addEventListener("click", () => copyText(b, b.parentElement!.querySelector("code")!.textContent ?? "")));
  const tabs = $$("[data-tab]");
  tabs.forEach((t) =>
    t.addEventListener("click", () => {
      tabs.forEach((x) => x.setAttribute("aria-selected", String(x === t)));
      $$("[data-panel]").forEach((p) => (p.hidden = p.dataset.panel !== t.dataset.tab));
    }),
  );
}

/* ---------------------------------------------------------------- read demo */

interface Balance { native: { symbol: string; formatted: string }; tokens: { symbol?: string; formatted?: string; error?: string }[]; explorer?: string; address: string; chain: string }
interface ContractInfo {
  isContract: boolean; name?: string; verified?: boolean; compiler?: string; summary?: string; warning?: string;
  proxy?: { implementation: string; implementationName?: string; type?: string };
  eip7702Delegation?: { delegate: string; delegateName?: string; delegateVerified: boolean };
  readFunctions?: string[]; writeFunctions?: string[]; explorer?: string; bytecodeBytes?: number;
}

const fmt = (v: string, max = 6) => {
  const [i, d = ""] = v.split(".");
  return `${Number(i).toLocaleString("en-US")}${d ? "." + d.slice(0, max) : ""}`;
};
const fnName = (sig: string) => sig.replace(/^function\s+/, "").split("(")[0];

export function initRead(onRun?: () => void) {
  const form = $<HTMLFormElement>("#read-form");
  const chain = $<HTMLSelectElement>("#read-chain");
  const addr = $<HTMLInputElement>("#read-address");
  const call = $("#read-call");
  const out = $("#read-result");
  const presetsEl = $("#read-presets");
  let mode: "wallet" | "contract" = "wallet";
  let ctrl: AbortController | null = null;

  const presets: Record<string, { label: string; chain: string; address: string }[]> = {
    wallet: [
      { label: "vitalik.eth · Base", chain: "base", address: VITALIK },
      { label: "vitalik.eth · Ethereum", chain: "ethereum", address: VITALIK },
      { label: "LayerZero Endpoint · Arbitrum", chain: "arbitrum", address: "0x1a44076050125825900e736c501f859c50fe728c" },
    ],
    contract: [
      { label: "USDC · Base (proxy)", chain: "base", address: USDC.base! },
      { label: "LayerZero EndpointV2 · Arbitrum", chain: "arbitrum", address: "0x1a44076050125825900e736c501f859c50fe728c" },
      { label: "EIP-7702 wallet · Base", chain: "base", address: VITALIK },
    ],
  };
  const renderPresets = () => {
    presetsEl.innerHTML = presets[mode]!.map((p, i) => `<button type="button" data-i="${i}">${esc(p.label)}</button>`).join("");
  };
  presetsEl.addEventListener("click", (e) => {
    const b = (e.target as HTMLElement).closest<HTMLElement>("[data-i]");
    if (!b) return;
    const p = presets[mode]![Number(b.dataset.i)]!;
    chain.value = p.chain;
    addr.value = p.address;
    void run();
  });
  $$("[data-read-mode]").forEach((b) =>
    b.addEventListener("click", () => {
      mode = b.dataset.readMode as typeof mode;
      $$("[data-read-mode]").forEach((x) => x.classList.toggle("on", x === b));
      renderPresets();
      const p = presets[mode]![0]!;
      chain.value = p.chain;
      addr.value = p.address;
      void run();
    }),
  );

  async function run() {
    onRun?.();
    ctrl?.abort();
    ctrl = new AbortController();
    const c = chain.value;
    const a = addr.value.trim();
    if (!/^0x[0-9a-fA-F]{40}$/.test(a)) {
      out.innerHTML = `<p class="err">That doesn't look like an address (0x + 40 hex characters).</p>`;
      return;
    }
    const tool = mode === "wallet" ? "get_balance" : "get_contract_info";
    const args: Record<string, unknown> = { chain: c, address: a };
    if (mode === "wallet" && USDC[c]) args.tokens = [USDC[c]];
    call.innerHTML = `→ tools/call <b>${tool}</b> ${esc(JSON.stringify(args).replace(a, short(a)))}`;
    out.innerHTML = `<div class="result-empty">Reading ${esc(chainName(c))}…</div>`;
    try {
      const { data, ms } = await callTool<Balance & ContractInfo>(tool, args, ctrl.signal);
      call.innerHTML += ` <span class="ms">· ${ms} ms</span>`;
      out.innerHTML = mode === "wallet" ? renderBalance(data) : renderContract(data);
    } catch (e) {
      if ((e as Error).name === "AbortError") return;
      out.innerHTML = `<p class="err">${esc((e as Error).message)}</p>`;
    }
  }

  function renderBalance(d: Balance) {
    const tokens = d.tokens
      .map((t) => (t.error ? `<span class="chip bad">${esc(t.error)}</span>` : `<span class="chip ok">${esc(fmt(t.formatted ?? "0", 2))} ${esc(t.symbol ?? "")}</span>`))
      .join("");
    return `<p class="tool-k">Native balance</p>
      <div class="big-num">${esc(fmt(d.native.formatted, 4))}<small>${esc(d.native.symbol)}</small></div>
      <dl class="kv"><dt>Address</dt><dd>${esc(d.address)}</dd><dt>Network</dt><dd>${esc(chainName(d.chain))}</dd>
      <dt>Tokens</dt><dd><div class="chips">${tokens || '<span class="chip">none requested</span>'}</div></dd>
      <dt>Explorer</dt><dd>${d.explorer ? `<a class="link" href="${esc(d.explorer)}" target="_blank" rel="noopener">open ↗</a>` : "—"}</dd></dl>`;
  }

  function renderContract(d: ContractInfo) {
    if (!d.isContract) {
      const del = d.eip7702Delegation;
      return `<p class="tool-k">Account type</p><div class="big-num">${del ? "Smart wallet" : "Wallet"}<small>${del ? "EIP-7702" : "EOA"}</small></div>
        <p class="tool-d">${esc(d.summary)}</p>${del ? `<dl class="kv"><dt>Delegate</dt><dd>${esc(del.delegateName ?? short(del.delegate))} ${del.delegateVerified ? '<span class="chip ok">verified</span>' : '<span class="chip bad">unverified</span>'}</dd></dl>` : ""}`;
    }
    const fns = [...(d.writeFunctions ?? []).slice(0, 4), ...(d.readFunctions ?? []).slice(0, 4)].map((f) => `<span class="chip">${esc(fnName(f))}()</span>`).join("");
    return `<p class="tool-k">${d.verified ? "Verified contract" : "Unverified contract"}</p>
      <div class="big-num">${esc(d.proxy?.implementationName ?? d.name ?? "Unknown")}<small>${d.proxy ? "via proxy" : ""}</small></div>
      <dl class="kv"><dt>Source</dt><dd>${d.verified ? `<span class="chip ok">Sourcify · ${esc(d.compiler ?? "")}</span>` : `<span class="chip bad">${esc(d.warning ?? "not verified")}</span>`}</dd>
      ${d.proxy ? `<dt>Proxy</dt><dd>${esc(d.name ?? "")} → ${esc(d.proxy.implementationName ?? short(d.proxy.implementation))} <span class="chip sig">${esc(d.proxy.type ?? "proxy")}</span></dd>` : ""}
      <dt>Functions</dt><dd>${(d.writeFunctions ?? []).length} write · ${(d.readFunctions ?? []).length} read</dd>
      <dt>Sample</dt><dd><div class="chips">${fns}</div></dd></dl>`;
  }

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    void run();
  });
  renderPresets();
  return { run };
}

/* ---------------------------------------------------------------- simulate console */

interface Sim { wouldSucceed: boolean; revertReason?: string; explanation: string; feeEstimate?: string; warnings: string[]; decodedCall?: { functionName: string } }

const SCENARIOS: Record<string, { prompt: string; label: string; args: Record<string, unknown> }> = {
  approve: {
    prompt: "A site wants me to approve this. Is it safe to sign?",
    label: "base · USDC.approve(0x…dEaD, max)",
    args: { chain: "base", to: USDC.base, from: VITALIK, data: `0x095ea7b3${pad("0xdead")}${MAX}` },
  },
  send: {
    prompt: "Send 0.01 ETH to 0x…bEEF on Base. What will it cost?",
    label: "base · transfer 0.01 ETH → 0x…bEEF",
    args: { chain: "base", to: "0x000000000000000000000000000000000000bEEF", from: VITALIK, value: "0.01" },
  },
  overdraw: {
    prompt: "Move all of it to this address, more than I hold if needed.",
    label: "base · USDC.transfer(0x…dEaD, 2²⁵⁶−1)",
    args: { chain: "base", to: USDC.base, from: VITALIK, data: `0xa9059cbb${pad("0xdead")}${MAX}` },
  },
};

export function initSimulate() {
  const body = $("#console-body");
  const buttons = $$("[data-scenario]");
  let token = 0;

  const line = (cls: string, html = "") => {
    const el = document.createElement("div");
    el.className = cls;
    el.innerHTML = html;
    body.appendChild(el);
    return el;
  };
  const type = async (el: HTMLElement, text: string, t: number, speed = 16) => {
    const caret = '<span class="caret"></span>';
    for (let i = 1; i <= text.length; i++) {
      if (t !== token) return;
      el.innerHTML = esc(text.slice(0, i)) + caret;
      await sleep(speed);
    }
    el.innerHTML = esc(text);
  };

  async function run(key: string) {
    const s = SCENARIOS[key]!;
    const t = ++token;
    buttons.forEach((b) => b.classList.toggle("on", b.dataset.scenario === key));
    body.innerHTML = "";
    await type(line("c-u"), s.prompt, t);
    if (t !== token) return;
    const c = line("c-call", `→ <b>simulate_transaction</b> ${esc(s.label)}`);
    const res = line("c-res", "running against live state…");
    try {
      const { data, ms } = await callTool<Sim>("simulate_transaction", s.args);
      if (t !== token) return;
      c.innerHTML += ` <span style="color:var(--ok)">· ${ms} ms</span>`;
      const rows: string[] = [];
      rows.push(data.wouldSucceed ? `<span class="k">would succeed</span>${data.feeEstimate ? ` · fee ${esc(data.feeEstimate)}` : ""}` : `<span class="w">would revert</span> · ${esc(data.revertReason ?? "")}`);
      if (data.decodedCall) rows.push(`decoded · ${esc(data.decodedCall.functionName)}()`);
      for (const w of data.warnings) rows.push(`<span class="w">⚠ ${esc(shortAddrs(w))}</span>`);
      res.innerHTML = rows.join("<br>");
      const verdict = shortAddrs(
        !data.wouldSucceed
          ? `Don't send it. It would fail (${data.revertReason ?? "reverted"}), so nothing was signed and no gas was spent.`
          : data.warnings.length
            ? `Don't sign this. ${data.explanation} ${data.warnings[0]}`
            : `Looks fine. ${data.explanation} Estimated fee: ${data.feeEstimate ?? "n/a"}.`,
      );
      await sleep(250);
      await type(line("c-a"), verdict, t, 11);
    } catch (e) {
      res.innerHTML = `<span class="w">${esc((e as Error).message)}</span>`;
    }
  }
  buttons.forEach((b) => b.addEventListener("click", () => void run(b.dataset.scenario!)));
  return { run: () => run("approve") };
}

/* ---------------------------------------------------------------- track */

interface Tracked {
  found: boolean; message?: string;
  messages?: {
    status: string; statusDetail?: string; meaning?: string; deliverySeconds?: number;
    from: { chain?: string; app?: string; txHash?: string; sentAt?: string };
    to: { chain?: string; txHash?: string; deliveredAt?: string };
    verification: { dvns: { name: string; status?: string; optional: boolean }[]; requiredConfirmations?: number };
    scanUrl?: string;
  }[];
}

export function initTrack() {
  const form = $<HTMLFormElement>("#track-form");
  const input = $<HTMLInputElement>("#track-input");
  const tl = $("#timeline");

  async function track(hash: string) {
    input.value = hash;
    if (!/^0x[0-9a-fA-F]{64}$/.test(hash)) {
      tl.innerHTML = `<p class="err">Paste a 0x-prefixed transaction hash (64 hex characters).</p>`;
      return;
    }
    tl.innerHTML = `<p class="note">→ lz_track_message ${esc(short(hash, 10, 6))}…</p>`;
    try {
      const { data, ms } = await callTool<Tracked>("lz_track_message", { txHash: hash });
      const m = data.messages?.[0];
      if (!data.found || !m) {
        tl.innerHTML = `<p class="err">${esc(data.message ?? "Not found.")}</p>`;
        return;
      }
      const delivered = m.status === "DELIVERED";
      const dvns = m.verification.dvns
        .map((d) => `<span class="chip ${d.status === "SUCCEEDED" ? "ok" : "sig"}">${esc(d.name)} ${d.status === "SUCCEEDED" ? "✓" : "…"}</span>`)
        .join("");
      tl.innerHTML = `<div class="tl">
        <span class="tl-dot ok"></span><div class="tl-body"><b>Sent on ${esc(chainName(m.from.chain ?? "?"))} · ${esc(appName(m.from.app))}</b>${esc(short(m.from.txHash, 10, 6))} · ${esc(ago(m.from.sentAt))}</div>
        <span class="tl-dot ${m.verification.dvns.every((d) => d.status === "SUCCEEDED" || d.optional) ? "ok" : "wait"}"></span><div class="tl-body"><b>Verified by ${m.verification.dvns.length} DVNs</b><div class="chips" style="margin-top:6px">${dvns}</div></div>
        <span class="tl-dot ${delivered ? "ok" : "wait"}"></span><div class="tl-body"><b>${delivered ? "Delivered" : "Waiting"} on ${esc(chainName(m.to.chain ?? "?"))}${m.deliverySeconds ? ` · ${m.deliverySeconds}s end to end` : ""}</b>${m.to.txHash ? esc(short(m.to.txHash, 10, 6)) : esc(m.statusDetail ?? "")}</div>
      </div>
      <div class="tl-meaning">${esc(m.meaning ?? m.statusDetail ?? m.status)} ${m.scanUrl ? `<a class="link" href="${esc(m.scanUrl)}" target="_blank" rel="noopener">LayerZero Scan ↗</a>` : ""} <span style="color:var(--ink3);font-family:var(--mono);font-size:11px">· ${ms} ms</span></div>`;
    } catch (e) {
      tl.innerHTML = `<p class="err">${esc((e as Error).message)}</p>`;
    }
  }
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    void track(input.value.trim());
  });
  return { track };
}

/* ---------------------------------------------------------------- countdown */

export function initCountdown(getTarget: () => string = () => ZERO_AT_DEFAULT) {
  const d = $("#cd-d"), h = $("#cd-h"), m = $("#cd-m"), s = $("#cd-s");
  const tick = () => {
    const diff = Math.max(0, new Date(getTarget()).getTime() - Date.now());
    const two = (n: number) => String(n).padStart(2, "0");
    d.textContent = two(Math.floor(diff / 86400000));
    h.textContent = two(Math.floor(diff / 3600000) % 24);
    m.textContent = two(Math.floor(diff / 60000) % 60);
    s.textContent = two(Math.floor(diff / 1000) % 60);
  };
  tick();
  setInterval(tick, 1000);
}

/* ---------------------------------------------------------------- tools grid */

const TOOLS: [string, string, string, string][] = [
  ["Read", "get_balance", "Native and ERC-20 balances of any wallet.", "What's in 0xd8dA…6045 on Base?"],
  ["Read", "get_token_info", "Name, symbol, decimals and supply of a token.", "How many USDC exist on Arbitrum?"],
  ["Read", "get_block", "The latest block, or any block by number.", "What's the latest block on HyperEVM?"],
  ["Read", "get_transaction", "Status, fee, decoded call and token transfers.", "What did this transaction do?"],
  ["Inspect", "read_contract", "Call any view function from a Solidity signature.", "Read totalSupply() on this contract."],
  ["Inspect", "get_contract_info", "Verified source, proxies, functions, EIP-7702.", "What is this contract, and is it verified?"],
  ["Protect", "simulate_transaction", "Dry-run on live state with risk warnings.", "Is this approval safe to sign?"],
  ["Network", "list_chains", "Every chain Plexa reaches, with its status.", "Which chains can you read?"],
  ["LayerZero", "lz_track_message", "Follow one message across chains, DVN by DVN.", "Where is my bridge transfer?"],
  ["LayerZero", "lz_latest_messages", "What is moving across LayerZero right now.", "What's happening on LayerZero?"],
  ["LayerZero", "lz_list_messages", "Recent messages from a wallet or an app.", "Show my last five bridge transfers."],
  ["LayerZero", "lz_chain_info", "Endpoints, libraries and DVNs from the registry.", "Which DVNs run on Base?"],
];

export function initTools() {
  const grid = $("#tool-grid");
  grid.innerHTML = TOOLS.map(
    ([k, n, d, q]) => `<article class="tool" data-reveal><span class="tool-k">${esc(k)}</span><h3 class="tool-n">${esc(n)}</h3><p class="tool-d">${esc(d)}</p><p class="tool-q">"${esc(q)}"</p></article>`,
  ).join("");
  grid.addEventListener("pointermove", (e) => {
    const card = (e.target as HTMLElement).closest<HTMLElement>(".tool");
    if (!card) return;
    const r = card.getBoundingClientRect();
    card.style.setProperty("--mx", `${e.clientX - r.left}px`);
    card.style.setProperty("--my", `${e.clientY - r.top}px`);
  });
}
