import { ago, esc, short } from "./mcp";

export interface LiveMessage {
  status: string;
  from: string;
  to: string;
  app?: string;
  sentAt?: string;
  deliverySeconds?: number;
  dvnsVerified: number;
  dvnsRequired: number;
  sourceTx?: string;
  scanUrl?: string;
}
export interface LiveSnapshot {
  generatedAt: string;
  messages: LiveMessage[];
  blocks: { chain: string; block: string | null }[];
  zero: { mainnetAt: string; rpcConfigured: boolean };
}

type Listener = (s: LiveSnapshot, fresh: LiveMessage[]) => void;

const CHAIN_NAMES: Record<string, string> = { ethereum: "Ethereum", base: "Base", arbitrum: "Arbitrum", hyperevm: "HyperEVM" };
export const ZERO_AT_DEFAULT = "2026-11-30T00:00:00Z";

export function statusClass(s: string): string {
  if (s === "DELIVERED") return "ok";
  if (s === "INFLIGHT" || s === "CONFIRMING") return "sig";
  return "bad";
}

/** Scan labels unidentified senders "unknown"; show something friendlier. */
export function appName(a?: string): string {
  return !a || a === "unknown" ? "Unlabeled OApp" : a;
}

export function chainName(c: string): string {
  const map: Record<string, string> = { bsc: "BNB", hyperliquid: "HyperEVM", subtensorevm: "Subtensor" };
  return map[c] ?? c.charAt(0).toUpperCase() + c.slice(1);
}

/** Polls /api/live while the page is visible and fans out updates. */
export class LiveFeed {
  private listeners: Listener[] = [];
  private seen = new Set<string>();
  last: LiveSnapshot | null = null;
  private timer = 0;

  constructor(private url = "/api/live") {}

  on(fn: Listener) {
    this.listeners.push(fn);
    if (this.last) fn(this.last, []);
  }

  start(intervalMs = 12000) {
    const tick = async () => {
      if (!document.hidden) await this.poll();
      this.timer = window.setTimeout(tick, intervalMs);
    };
    void tick();
  }

  stop() {
    clearTimeout(this.timer);
  }

  private async poll() {
    try {
      const res = await fetch(this.url, { cache: "no-store" });
      if (!res.ok) return;
      const snap = (await res.json()) as LiveSnapshot;
      const fresh = snap.messages.filter((m) => m.sourceTx && !this.seen.has(m.sourceTx + m.status));
      for (const m of snap.messages) if (m.sourceTx) this.seen.add(m.sourceTx + m.status);
      this.last = snap;
      for (const fn of this.listeners) fn(snap, fresh);
    } catch {
      // offline or blocked: keep showing the last snapshot
    }
  }
}

/** Hero ticker: rebuilt at most once a minute so the marquee doesn't jump. */
export function bindTicker(feed: LiveFeed, move: HTMLElement) {
  let builtAt = 0;
  feed.on((s) => {
    if (Date.now() - builtAt < 60000 && builtAt) return;
    builtAt = Date.now();
    const items: string[] = [];
    for (const m of s.messages.slice(0, 10)) {
      const cls = statusClass(m.status);
      const st = m.status === "DELIVERED" && m.deliverySeconds ? `DELIVERED ${m.deliverySeconds}s` : m.status === "INFLIGHT" ? `INFLIGHT · ${m.dvnsVerified}/${m.dvnsRequired} DVNs` : m.status;
      items.push(`<span class="tk"><b>${esc(appName(m.app))}</b>${esc(chainName(m.from))} → ${esc(chainName(m.to))} <span class="s-${cls}">${esc(st)}</span></span>`);
    }
    for (const b of s.blocks) if (b.block) items.push(`<span class="tk"><b>${esc(CHAIN_NAMES[b.chain] ?? b.chain)}</b>block ${Number(b.block).toLocaleString("en-US")}</span>`);
    const days = Math.max(0, Math.ceil((new Date(s.zero.mainnetAt).getTime() - Date.now()) / 86400000));
    items.push(`<span class="tk"><b>Zero</b>${days > 0 ? `mainnet in ${days} days` : "mainnet live"}</span>`);
    const html = items.join("");
    move.innerHTML = html + html;
  });
}

/** Cross-chain chapter: latest messages and block heights. */
export function bindFeed(feed: LiveFeed, list: HTMLElement, blocks: HTMLElement, meta: HTMLElement, onPick: (tx: string) => void) {
  const prevBlocks = new Map<string, string>();
  list.addEventListener("click", (e) => {
    const row = (e.target as HTMLElement).closest<HTMLElement>("[data-tx]");
    if (row?.dataset.tx) onPick(row.dataset.tx);
  });
  const render = (s: LiveSnapshot) => {
    list.innerHTML = s.messages
      .slice(0, 7)
      .map((m) => {
        const cls = statusClass(m.status);
        const meta2 = m.status === "DELIVERED" && m.deliverySeconds ? `${m.deliverySeconds}s` : `${m.dvnsVerified}/${m.dvnsRequired} DVNs`;
        return `<div class="fr" data-tx="${esc(m.sourceTx)}" title="Track this message">
          <span class="fr-app">${esc(appName(m.app))}</span><span class="fr-st ${cls}">${esc(m.status)}</span>
          <span class="fr-route">${esc(chainName(m.from))} → ${esc(chainName(m.to))} · ${esc(short(m.sourceTx))}</span><span class="fr-meta">${esc(meta2)} · ${esc(ago(m.sentAt))}</span>
        </div>`;
      })
      .join("");
    blocks.innerHTML = s.blocks
      .map((b) => {
        const bump = b.block && prevBlocks.get(b.chain) && prevBlocks.get(b.chain) !== b.block ? " bump" : "";
        if (b.block) prevBlocks.set(b.chain, b.block);
        return `<div class="blk">${esc(CHAIN_NAMES[b.chain] ?? b.chain)}<b class="${bump}">${b.block ? "#" + Number(b.block).toLocaleString("en-US") : "—"}</b></div>`;
      })
      .join("");
    setTimeout(() => blocks.querySelectorAll(".bump").forEach((el) => el.classList.remove("bump")), 1200);
    meta.textContent = `updated ${new Date(s.generatedAt).toLocaleTimeString("en-GB", { hour12: false })}`;
  };
  feed.on((s) => render(s));
}
