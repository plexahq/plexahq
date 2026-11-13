/** Minimal client for Plexa's own MCP endpoint (same origin). */

let nextId = 0;

export class ToolError extends Error {}

export function mcpUrl(): string {
  return `${location.origin}/mcp`;
}

export async function callTool<T = Record<string, unknown>>(
  name: string,
  args: Record<string, unknown>,
  signal?: AbortSignal,
): Promise<{ data: T; ms: number }> {
  const t0 = performance.now();
  const res = await fetch("/mcp", {
    method: "POST",
    signal,
    headers: {
      "content-type": "application/json",
      accept: "application/json, text/event-stream",
      "mcp-protocol-version": "2025-06-18",
    },
    body: JSON.stringify({ jsonrpc: "2.0", id: ++nextId, method: "tools/call", params: { name, arguments: args } }),
  });
  const ms = Math.round(performance.now() - t0);
  const body = (await res.json()) as {
    error?: { message: string };
    result?: { isError?: boolean; content?: { text?: string }[] };
  };
  if (body.error) throw new ToolError(body.error.message);
  const text = body.result?.content?.[0]?.text ?? "";
  if (body.result?.isError) throw new ToolError(text);
  return { data: JSON.parse(text) as T, ms };
}

export const short = (s: string | undefined | null, head = 6, tail = 4): string =>
  !s ? "—" : s.length <= head + tail + 1 ? s : `${s.slice(0, head)}…${s.slice(-tail)}`;

export const esc = (s: unknown): string =>
  String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]!);

export function ago(iso?: string): string {
  if (!iso) return "";
  const s = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 1000));
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  return `${Math.floor(s / 3600)}h ago`;
}
