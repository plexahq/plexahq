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

/* ---------------------------------------------------------------- trust check */

interface Uln { summary: string; requiredDVNs?: string[]; optionalDVNs?: string[]; optionalThreshold?: number; blockConfirmations?: number; settings?: string }
interface Security {
  found: boolean; message?: string;
  app?: { chain: string; address: string; kind: string; name?: string; symbol?: string; explorer?: string };
  control?: { role: string; address: string; kind: string; detail: string }[];
  pathways?: { remote: string; outgoing: Uln; incoming: Uln; executor?: string; flags: string[] }[];
  summary?: { risk: "low" | "medium" | "high"; connectedChains: number; pathwaysChecked: number; typicalSetup?: string; truncated?: string; findings: string[]; notes: string[] };
}

const RISK_LABEL = { low: "Low risk", medium: "Medium risk", high: "High risk" } as const;

const dvnLine = (u: Uln) => {
  if (!u.requiredDVNs) return `<span class="muted">${esc(u.summary)}</span>`;
  const n = u.summary.match(/^(\d+)/)?.[1] ?? "?";
  const names = [...u.requiredDVNs, ...(u.optionalDVNs?.length ? [`${u.optionalThreshold} of ${u.optionalDVNs.join(" / ")}`] : [])];
  return `<b class="q q${Math.min(3, Number(n))}">${esc(n)}</b> ${esc(names.join(", "))}`;
};

export function initTrust() {
  const form = $<HTMLFormElement>("#trust-form");
  const chain = $<HTMLSelectElement>("#trust-chain");
  const addr = $<HTMLInputElement>("#trust-address");
  const call = $("#trust-call");
  const out = $("#trust-result");
  const risk = $("#trust-risk");
  const presets = [
    { label: "ZRO token · Ethereum", chain: "ethereum", address: "0x6985884C4392D348587B19cb9eAAf157F13271cd" },
    { label: "USDT0 · Ethereum", chain: "ethereum", address: "0x6C96dE32CEa08842dcc4058c14d3aaAD7Fa41dee" },
    { label: "ZRO token · Arbitrum", chain: "arbitrum", address: "0x6985884C4392D348587B19cb9eAAf157F13271cd" },
  ];
  $("#trust-presets").innerHTML = presets.map((p, i) => `<button type="button" data-i="${i}">${esc(p.label)}</button>`).join("");
  $("#trust-presets").addEventListener("click", (e) => {
    const b = (e.target as HTMLElement).closest<HTMLElement>("[data-i]");
    if (!b) return;
    const p = presets[Number(b.dataset.i)]!;
    chain.value = p.chain;
    addr.value = p.address;
    void run();
  });
  let ctrl: AbortController | null = null;

  async function run() {
    ctrl?.abort();
    ctrl = new AbortController();
    const a = addr.value.trim();
    if (!/^0x[0-9a-fA-F]{40}$/.test(a)) {
      out.innerHTML = `<p class="err">That doesn't look like an address (0x + 40 hex characters).</p>`;
      return;
    }
    const args = { chain: chain.value, address: a, maxPathways: 8 };
    call.innerHTML = `→ tools/call <b>lz_app_security</b> ${esc(JSON.stringify(args).replace(a, short(a)))}`;
    risk.className = "risk";
    risk.textContent = "";
    out.innerHTML = `<div class="result-empty">Reading ${esc(chainName(chain.value))} and LayerZero's registry…</div>`;
    try {
      const { data, ms } = await callTool<Security>("lz_app_security", args, ctrl.signal);
      call.innerHTML += ` <span class="ms">· ${ms} ms</span>`;
      out.innerHTML = render(data);
      if (data.summary) {
        risk.className = `risk ${data.summary.risk}`;
        risk.textContent = RISK_LABEL[data.summary.risk];
      }
    } catch (e) {
      if ((e as Error).name === "AbortError") return;
      out.innerHTML = `<p class="err">${esc((e as Error).message)}</p>`;
    }
  }

  function render(d: Security) {
    if (!d.found || !d.app || !d.summary) return `<p class="tool-d">${esc(d.message ?? "Not a LayerZero app.")}</p>`;
    const s = d.summary;
    const title = d.app.symbol ? `${d.app.name ?? d.app.symbol}` : d.app.kind;
    const control = (d.control ?? [])
      .map((c) => `<span class="chip ${c.kind === "single key" ? "bad" : c.kind === "multisig" ? "ok" : ""}">${esc(c.role)} · ${esc(c.kind === "multisig" ? c.detail.replace("Safe multisig, ", "multisig ") : c.kind)}</span>`)
      .join("");
    const rows = (d.pathways ?? [])
      .slice(0, 6)
      .map((p) => `<tr${p.flags.some((f) => f.startsWith("high")) ? ' class="flag"' : ""}><td>${esc(p.remote.replace(/ \(EID \d+\)$/, ""))}</td><td>${dvnLine(p.outgoing)}</td><td>${dvnLine(p.incoming)}</td></tr>`)
      .join("");
    const more = (d.pathways?.length ?? 0) > 6 || s.connectedChains > s.pathwaysChecked ? `<p class="muted small">Showing ${Math.min(6, d.pathways?.length ?? 0)} of ${s.connectedChains} connected chains.</p>` : "";
    const findings = s.findings.length
      ? `<ul class="findings">${s.findings.map((f) => `<li class="bad">${esc(f)}</li>`).join("")}</ul>`
      : `<ul class="findings"><li class="ok">No single point of failure found in the pathways checked.</li></ul>`;
    return `<p class="tool-k">${esc(d.app.kind)} · ${esc(d.app.chain)}</p>
      <div class="big-num">${esc(title)}<small>${esc(d.app.symbol ?? "")}</small></div>
      <div class="chips">${control}</div>
      <table class="paths"><thead><tr><th>Connected chain</th><th>Outgoing · DVNs</th><th>Incoming · DVNs</th></tr></thead><tbody>${rows}</tbody></table>
      ${more}${findings}`;
  }

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    void run();
  });
  return { run };
}

/* ---------------------------------------------------------------- ZRO everywhere */

interface ZroOverview {
  supply: { countedOnTheseChains: string; byChain: { chain: string; supply: string; share: string }[]; unavailable?: { chain: string }[] };
  wallet?: { address: string; totalZro: string; byChain: { chain: string; zro: string }[]; zeroReadiness: string };
}

const num = (s: string) => Number(s.replace(/,/g, ""));
const compact = (s: string) => {
  const n = num(s);
  if (n >= 1e9) return `${(n / 1e9).toFixed(2)}B`;
  if (n >= 1e6) return `${(n / 1e6).toFixed(n >= 1e8 ? 0 : 1)}M`;
  if (n >= 1e3) return `${(n / 1e3).toFixed(1)}K`;
  return n.toLocaleString("en-US", { maximumFractionDigits: 4 });
};

export function initZro() {
  const bars = $("#zro-bars");
  const total = $("#zro-total");
  const meta = $("#zro-meta");
  const form = $<HTMLFormElement>("#zro-form");
  const input = $<HTMLInputElement>("#zro-input");
  const result = $("#zro-result");

  async function load() {
    try {
      const { data, ms } = await callTool<ZroOverview>("zro_overview", {});
      const rows = data.supply.byChain;
      const max = Math.max(...rows.map((r) => num(r.supply)));
      // log scale so the smaller chains stay visible next to Ethereum
      const w = (v: number) => Math.max(0.03, Math.log10(1 + v) / Math.log10(1 + max));
      total.innerHTML = `${esc(compact(data.supply.countedOnTheseChains))}<small>ZRO counted on ${rows.length} chains</small>`;
      bars.innerHTML = rows
        .map((r) => `<div class="bar"><span class="bar-k">${esc(r.chain)}</span><span class="bar-t"><i style="transform:scaleX(${w(num(r.supply))})"></i></span><span class="bar-v">${esc(compact(r.supply))} <small>${esc(r.share)}</small></span></div>`)
        .join("");
      meta.textContent = `zro_overview · ${ms} ms`;
    } catch (e) {
      meta.textContent = "unavailable";
      bars.innerHTML = `<p class="err">${esc((e as Error).message)}</p>`;
    }
  }

  async function check(address: string) {
    if (!/^0x[0-9a-fA-F]{40}$/.test(address)) {
      result.innerHTML = `<p class="err">That doesn't look like a wallet address.</p>`;
      return;
    }
    result.innerHTML = `<p class="muted small">Reading 7 chains…</p>`;
    try {
      const { data, ms } = await callTool<ZroOverview>("zro_overview", { address });
      const w = data.wallet!;
      const ready = num(w.totalZro) > 0;
      result.innerHTML = `<div class="ready ${ready ? "ok" : "no"}"><b>${ready ? "Zero-ready" : "No ZRO yet"}</b><span>${esc(w.totalZro)} ZRO</span></div>
        <div class="chips">${w.byChain.map((c) => `<span class="chip ok">${esc(c.chain)} · ${esc(c.zro)}</span>`).join("") || '<span class="chip">none on these chains</span>'}</div>
        <p class="muted small">${esc(w.zeroReadiness)} <span class="ms">${ms} ms</span></p>`;
    } catch (e) {
      result.innerHTML = `<p class="err">${esc((e as Error).message)}</p>`;
    }
  }

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    void check(input.value.trim());
  });
  $("#zro-presets").addEventListener("click", (e) => {
    const b = (e.target as HTMLElement).closest<HTMLElement>("[data-addr]");
    if (!b) return;
    input.value = b.dataset.addr!;
    void check(input.value);
  });
  return { load };
}

/* ---------------------------------------------------------------- tokenized stocks */

interface StockLookup {
  found: number | false; message?: string;
  matches?: { symbol: string; ticker: string; name: string; totalTokens: string; chains: { chain: string; address: string; supply?: string; explorer?: string }[] }[];
}
interface StockPortfolio { address: string; positions: number; holdings: { symbol: string; name: string; chain: string; amount: string }[]; checked: string }

export function initStocks() {
  const form = $<HTMLFormElement>("#stock-form");
  const input = $<HTMLInputElement>("#stock-input");
  const call = $("#stock-call");
  const out = $("#stock-result");
  const presetsEl = $("#stock-presets");
  let mode: "lookup" | "portfolio" = "lookup";
  let ctrl: AbortController | null = null;
  const presets = {
    lookup: [
      { label: "NVIDIA", value: "NVDA" },
      { label: "Apple", value: "AAPL" },
      { label: "Tesla", value: "TSLA" },
      { label: "S&P 500 (SPY)", value: "SPY" },
      { label: "Nasdaq-100 (QQQ)", value: "QQQ" },
    ],
    portfolio: [{ label: "Uniswap v4 PoolManager · Ethereum", value: "0x000000000004444c5dc75cB358380D2e3dE08A90" }],
  };
  const renderPresets = () => {
    presetsEl.innerHTML = presets[mode].map((p, i) => `<button type="button" data-i="${i}">${esc(p.label)}</button>`).join("");
    input.placeholder = mode === "lookup" ? "Ticker or name, e.g. AAPL" : "0x… wallet or contract";
  };
  presetsEl.addEventListener("click", (e) => {
    const b = (e.target as HTMLElement).closest<HTMLElement>("[data-i]");
    if (!b) return;
    input.value = presets[mode][Number(b.dataset.i)]!.value;
    void run();
  });
  $$("[data-stock-mode]").forEach((b) =>
    b.addEventListener("click", () => {
      mode = b.dataset.stockMode as typeof mode;
      $$("[data-stock-mode]").forEach((x) => x.classList.toggle("on", x === b));
      renderPresets();
      input.value = presets[mode][0]!.value;
      void run();
    }),
  );

  async function run() {
    ctrl?.abort();
    ctrl = new AbortController();
    const v = input.value.trim();
    if (!v) return;
    if (mode === "portfolio" && !/^0x[0-9a-fA-F]{40}$/.test(v)) {
      out.innerHTML = `<p class="err">Paste a wallet or contract address (0x + 40 hex characters).</p>`;
      return;
    }
    const tool = mode === "lookup" ? "stocks_lookup" : "stocks_portfolio";
    const args = mode === "lookup" ? { query: v } : { address: v, limit: 40 };
    call.innerHTML = `→ tools/call <b>${tool}</b> ${esc(JSON.stringify(args).replace(v, mode === "portfolio" ? short(v) : v))}`;
    out.innerHTML = `<div class="result-empty">${mode === "lookup" ? "Reading supply on Ethereum and BNB Chain…" : "Scanning every tokenized stock on two chains…"}</div>`;
    try {
      const { data, ms } = await callTool<StockLookup & StockPortfolio>(tool, args, ctrl.signal);
      call.innerHTML += ` <span class="ms">· ${ms} ms</span>`;
      out.innerHTML = mode === "lookup" ? renderLookup(data) : renderPortfolio(data);
    } catch (e) {
      if ((e as Error).name === "AbortError") return;
      out.innerHTML = `<p class="err">${esc((e as Error).message)}</p>`;
    }
  }

  function renderLookup(d: StockLookup) {
    if (!d.found || !d.matches?.length) return `<p class="tool-d">${esc(d.message ?? "No match.")}</p>`;
    const m = d.matches[0]!;
    const max = Math.max(1, ...m.chains.map((c) => num(c.supply ?? "0")));
    const bars = m.chains
      .map((c) => `<div class="bar"><span class="bar-k">${esc(c.chain)}</span><span class="bar-t"><i style="transform:scaleX(${num(c.supply ?? "0") / max})"></i></span><span class="bar-v">${esc(compact(c.supply ?? "0"))}</span></div>`)
      .join("");
    const others = d.matches.slice(1).map((x) => `<button type="button" class="chip" data-q="${esc(x.ticker)}">${esc(x.symbol)} · ${esc(x.name)}</button>`).join("");
    return `<p class="tool-k">${esc(m.symbol)} · tokenized by Ondo Global Markets</p>
      <div class="big-num">${esc(m.name)}<small>${esc(m.ticker)}</small></div>
      <dl class="kv"><dt>Tokens on-chain</dt><dd>${esc(m.totalTokens)} ${esc(m.symbol)}</dd>
      <dt>Contracts</dt><dd>${m.chains.map((c) => (c.explorer ? `<a class="link" href="${esc(c.explorer)}" target="_blank" rel="noopener">${esc(c.chain)} ↗</a>` : esc(c.chain))).join(" · ")}</dd></dl>
      <div class="bar-list">${bars}</div>
      ${others ? `<p class="muted small">Also matched</p><div class="chips">${others}</div>` : ""}`;
  }

  function renderPortfolio(d: StockPortfolio) {
    const chips = d.holdings.map((h) => `<span class="chip ok" title="${esc(h.name)} · ${esc(h.chain)}">${esc(h.symbol)} ${esc(compact(h.amount))}</span>`).join("");
    return `<p class="tool-k">Tokenized stocks held</p>
      <div class="big-num">${d.positions}<small>position${d.positions === 1 ? "" : "s"}</small></div>
      ${d.positions ? `<div class="chips holdings">${chips}</div>${d.positions > d.holdings.length ? `<p class="muted small">Showing ${d.holdings.length} of ${d.positions}.</p>` : ""}` : `<p class="tool-d">No tokenized stocks or ETFs in this wallet.</p>`}
      <p class="muted small">Checked ${esc(d.checked)}.</p>`;
  }

  out.addEventListener("click", (e) => {
    const b = (e.target as HTMLElement).closest<HTMLElement>("[data-q]");
    if (!b) return;
    input.value = b.dataset.q!;
    void run();
  });
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    void run();
  });
  renderPresets();
  return { run };
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
  ["Trust", "lz_app_security", "Who verifies an app's messages, and who controls it.", "Is this bridge safe to use?"],
  ["ZRO", "zro_overview", "ZRO on every chain, and a wallet's ZRO everywhere.", "Is my wallet ready for Zero?"],
  ["Markets", "stocks_lookup", "Tokenized stocks and ETFs, supply on each chain.", "How much tokenized NVIDIA is on BNB Chain?"],
  ["Markets", "stocks_portfolio", "Every tokenized stock a wallet holds.", "Which stocks does this wallet hold on-chain?"],
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
