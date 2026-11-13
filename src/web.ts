import { WebStandardStreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/webStandardStreamableHttp.js";
import { ChainRegistry, loadChains } from "./chains.js";
import { createServer, VERSION } from "./server.js";

/**
 * Web-standard (Request -> Response) MCP endpoint, shared by the Node HTTP server
 * and serverless platforms such as Vercel. Stateless: one MCP server per request,
 * JSON responses, no SSE sessions.
 */

const MAX_BODY_BYTES = 1_000_000;

export const CORS_HEADERS: Record<string, string> = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "content-type, accept, mcp-protocol-version, mcp-session-id",
  "Access-Control-Expose-Headers": "mcp-session-id",
};

// Module scope so RPC clients and caches survive across requests (and warm serverless invocations).
let registry: ChainRegistry | undefined;
function getRegistry(): ChainRegistry {
  registry ??= new ChainRegistry(loadChains());
  return registry;
}

function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json", ...CORS_HEADERS },
  });
}

function rpcError(status: number, code: number, message: string): Response {
  return json(status, { jsonrpc: "2.0", error: { code, message }, id: null });
}

function withCors(res: Response): Response {
  const headers = new Headers(res.headers);
  for (const [k, v] of Object.entries(CORS_HEADERS)) headers.set(k, v);
  return new Response(res.body, { status: res.status, statusText: res.statusText, headers });
}

export function handleHealth(): Response {
  return json(200, { ok: true, name: "plexa", version: VERSION });
}

export async function handleMcpRequest(request: Request): Promise<Response> {
  if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: CORS_HEADERS });
  if (request.method === "GET") {
    // A plain GET (e.g. from a browser) gets a short pointer instead of an SSE stream.
    return json(405, {
      name: "plexa",
      version: VERSION,
      message: "This is an MCP endpoint. Add this URL to an MCP client (Claude, Cursor, VS Code...) as a remote server.",
    });
  }
  if (request.method !== "POST") return rpcError(405, -32000, "Method not allowed");

  const length = Number(request.headers.get("content-length") ?? 0);
  if (length > MAX_BODY_BYTES) return rpcError(413, -32600, "Request body too large");

  let body: unknown;
  try {
    const text = await request.text();
    if (text.length > MAX_BODY_BYTES) return rpcError(413, -32600, "Request body too large");
    body = JSON.parse(text);
  } catch (error) {
    return rpcError(400, -32700, error instanceof Error ? error.message : "Invalid JSON");
  }

  const server = createServer(getRegistry());
  const transport = new WebStandardStreamableHTTPServerTransport({
    sessionIdGenerator: undefined,
    enableJsonResponse: true,
  });
  try {
    await server.connect(transport);
    // In JSON mode the response is complete once this resolves, so closing afterwards is safe.
    return withCors(await transport.handleRequest(request, { parsedBody: body }));
  } catch (error) {
    console.error("MCP request failed:", error);
    return rpcError(500, -32603, "Internal server error");
  } finally {
    await transport.close().catch(() => undefined);
    await server.close().catch(() => undefined);
  }
}
