import { appName, chainName, statusClass, type LiveFeed, type LiveSnapshot } from "../live";
import { ago, callTool, esc, short } from "../mcp";

const CHAINS: Record<string, string> = { ethereum: "Ethereum", base: "Base", arbitrum: "Arbitrum", hyperevm: "HyperEVM" };
const STOCKS = ["NVDA", "AAPL", "TSLA", "SPY", "QQQ", "MSFT"];
const $ = (id: string) => document.getElementById(id)!;

function topCounts(values: string[], n: number): [string, number][] {
  const m = new Map<string, number>();
  for (const v of values) m.set(v, (m.get(v) ?? 0) + 1);
  return [...m.entries()].sort((a, b) => b[1] - a[1]).slice(0, n);
}

function bars(el: HTMLElement, rows: [string, number][], total: number) {
  const max = Math.max(1, ...rows.map((r) => r[1]));
  el.innerHTML = rows
    .map(([k, v]) => `<div class="bar"><span class="bar-k">${esc(k)}</span><span class="bar-t"><i style="transform:scaleX(${v / max})"></i></span><span class="bar-v">${v} <small>${Math.round((v / total) * 100)}%</small></span></div>`)
    .join("");
}

export function initStats(feed: LiveFeed) {
  const prev = new Map<string, { block: number; at: number }>();
  const rates = new Map<string, number>();

  // gateway health and latency
  const ping = async () => {
    const t0 = performance.now();
    try {
      const r = await fetch("/health", { cache: "no-store" });
      const ok = r.ok && ((await r.json()) as { ok?: boolean }).ok;
      const ms = Math.round(performance.now() - t0);
      $("k-gw").textContent = ok ? `${ms} ms` : "down";
      $("st-dot").className = ok ? "dot dot-ok" : "dot";
      $("st-text").textContent = ok ? "All systems normal · refreshing live" : "Gateway not responding";
    } catch {
      $("k-gw").textContent = "down";
      $("st-text").textContent = "Gateway not responding";
    }
  };
  void ping();
  setInterval(() => !document.hidden && void ping(), 15000);

  const render = (s: LiveSnapshot) => {
    // chain heads with an observed block rate
    const now = Date.now();
    $("heads").innerHTML = s.blocks
      .map((b) => {
        const n = b.block ? Number(b.block) : null;
        const p = prev.get(b.chain);
        if (n && p && n > p.block && now > p.at) rates.set(b.chain, ((n - p.block) / (now - p.at)) * 60000);
        if (n) prev.set(b.chain, { block: n, at: now });
        const rate = rates.get(b.chain);
        return `<div class="head panel"><span class="kpi-k">${esc(CHAINS[b.chain] ?? b.chain)}</span><b>${n ? "#" + n.toLocaleString("en-US") : "—"}</b><small>${rate ? `${rate >= 100 ? Math.round(rate) : rate.toFixed(1)} blocks / min` : "measuring block rate…"}</small><i class="head-pulse"></i></div>`;
      })
      .join("");

    // LayerZero snapshot
    const msgs = s.messages;
    const total = msgs.length || 1;
    const delivered = msgs.filter((m) => m.status === "DELIVERED");
    const inflight = msgs.filter((m) => m.status === "INFLIGHT" || m.status === "CONFIRMING");
    const times = delivered.map((m) => m.deliverySeconds).filter((x): x is number => typeof x === "number").sort((a, b) => a - b);
    const median = times.length ? times[Math.floor(times.length / 2)]! : null;
    $("k-n").textContent = String(msgs.length);
    $("k-del").textContent = `${Math.round((delivered.length / total) * 100)}%`;
    $("k-fly").textContent = String(inflight.length);
    $("k-med").textContent = median !== null ? `${median}s` : "—";
    $("lz-scope").textContent = `Based on the ${msgs.length} most recent messages across LayerZero mainnet, as of ${new Date(s.generatedAt).toLocaleTimeString("en-GB", { hour12: false })}.`;
    const days = Math.max(0, Math.ceil((new Date(s.zero.mainnetAt).getTime() - now) / 86400000));
    $("k-zero").textContent = days > 0 ? String(days) : "Live";

    const byStatus = topCounts(msgs.map((m) => m.status), 6);
    $("sb").innerHTML = byStatus.map(([k, v]) => `<i class="sb-${statusClass(k)}" style="flex:${v}" title="${esc(k)}: ${v}"></i>`).join("");
    $("sb-legend").innerHTML = byStatus.map(([k, v]) => `<span><i class="sb-${statusClass(k)}"></i>${esc(k)} · ${v}</span>`).join("");
    bars($("apps"), topCounts(msgs.map((m) => appName(m.app)), 6), total);
    bars($("routes"), topCounts(msgs.map((m) => `${chainName(m.from)} → ${chainName(m.to)}`), 6), total);

    $("latest").innerHTML = msgs
      .slice(0, 20)
      .map((m) => {
        const cls = statusClass(m.status);
        return `<tr><td>${esc(appName(m.app))}</td><td>${esc(chainName(m.from))} → ${esc(chainName(m.to))}</td><td><span class="pill pill-${cls === "ok" ? "ok" : cls === "sig" ? "sig" : ""}">${esc(m.status)}</span></td><td>${m.dvnsVerified}/${m.dvnsRequired}</td><td>${m.deliverySeconds ? `${m.deliverySeconds}s` : "—"}</td><td>${esc(ago(m.sentAt))}</td><td>${m.scanUrl ? `<a class="link" href="${esc(m.scanUrl)}" target="_blank" rel="noopener">${esc(short(m.sourceTx))} ↗</a>` : ""}</td></tr>`;
      })
      .join("");
  };
  feed.on((s) => render(s));
}

const n = (s: string) => Number(s.replace(/,/g, ""));
const compact = (v: number) => (v >= 1e9 ? `${(v / 1e9).toFixed(2)}B` : v >= 1e6 ? `${(v / 1e6).toFixed(1)}M` : v >= 1e3 ? `${(v / 1e3).toFixed(1)}K` : v.toFixed(0));

/** ZRO supply per chain and a handful of tokenized stocks, read through Plexa's own tools. */
export async function initMarketStats() {
  const zroEl = $("zro-stats");
  const stockEl = $("stock-stats");
  if (!zroEl || !stockEl) return;
  callTool<{ supply: { countedOnTheseChains: string; byChain: { chain: string; supply: string; share: string }[] } }>("zro_overview", {})
    .then(({ data }) => {
      const rows = data.supply.byChain;
      const max = Math.max(...rows.map((r) => n(r.supply)));
      const w = (v: number) => Math.max(0.03, Math.log10(1 + v) / Math.log10(1 + max));
      $("zro-total-s").textContent = `${compact(n(data.supply.countedOnTheseChains))} ZRO`;
      zroEl.innerHTML = rows
        .map((r) => `<div class="bar"><span class="bar-k">${esc(r.chain)}</span><span class="bar-t"><i style="transform:scaleX(${w(n(r.supply))})"></i></span><span class="bar-v">${compact(n(r.supply))} <small>${esc(r.share)}</small></span></div>`)
        .join("");
    })
    .catch((e) => (zroEl.innerHTML = `<p class="err">${esc((e as Error).message)}</p>`));
  const results = await Promise.all(
    STOCKS.map((q) =>
      callTool<{ matches?: { symbol: string; name: string; totalTokens: string }[] }>("stocks_lookup", { query: q })
        .then(({ data }) => data.matches?.[0])
        .catch(() => undefined),
    ),
  );
  const rows = results.filter((r): r is { symbol: string; name: string; totalTokens: string } => Boolean(r));
  if (!rows.length) {
    stockEl.innerHTML = `<p class="err">Stock data is unavailable right now.</p>`;
    return;
  }
  rows.sort((a, b) => n(b.totalTokens) - n(a.totalTokens));
  const max = Math.max(...rows.map((r) => n(r.totalTokens)));
  stockEl.innerHTML = rows
    .map((r) => `<div class="bar"><span class="bar-k">${esc(r.name)}</span><span class="bar-t"><i style="transform:scaleX(${n(r.totalTokens) / max})"></i></span><span class="bar-v">${compact(n(r.totalTokens))} <small>${esc(r.symbol)}</small></span></div>`)
    .join("");
}

