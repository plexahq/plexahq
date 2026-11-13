import { createServer as createHttpServer, type IncomingMessage, type ServerResponse } from "node:http";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { ChainRegistry, loadChains } from "./chains.js";
import { createServer, VERSION } from "./server.js";

const PORT = Number(process.env.PORT ?? 3000);
const HOST = process.env.HOST ?? "127.0.0.1";
const MAX_BODY_BYTES = 1_000_000;

// Shared across requests so RPC clients and caches are reused.
const registry = new ChainRegistry(loadChains());

function setCors(res: ServerResponse): void {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "content-type, accept, mcp-protocol-version, mcp-session-id");
  res.setHeader("Access-Control-Expose-Headers", "mcp-session-id");
}

function sendJson(res: ServerResponse, status: number, body: unknown): void {
  res.writeHead(status, { "content-type": "application/json" });
  res.end(JSON.stringify(body));
}

async function readBody(req: IncomingMessage): Promise<unknown> {
  const chunks: Buffer[] = [];
  let size = 0;
  for await (const chunk of req) {
    size += (chunk as Buffer).length;
    if (size > MAX_BODY_BYTES) throw new Error("Request body too large");
    chunks.push(chunk as Buffer);
  }
  return JSON.parse(Buffer.concat(chunks).toString("utf8"));
}

const httpServer = createHttpServer(async (req, res) => {
  setCors(res);
  const { pathname } = new URL(req.url ?? "/", "http://localhost");

  if (req.method === "OPTIONS") {
    res.writeHead(204).end();
    return;
  }
  if (pathname === "/health") {
    sendJson(res, 200, { ok: true, name: "plexa", version: VERSION });
    return;
  }
  if (pathname !== "/mcp") {
    sendJson(res, 404, { error: "Not found. The MCP endpoint is /mcp" });
    return;
  }
  if (req.method !== "POST") {
    // Stateless server: no SSE stream (GET) or session teardown (DELETE).
    sendJson(res, 405, { jsonrpc: "2.0", error: { code: -32000, message: "Method not allowed" }, id: null });
    return;
  }

  let body: unknown;
  try {
    body = await readBody(req);
  } catch (error) {
    sendJson(res, 400, {
      jsonrpc: "2.0",
      error: { code: -32700, message: error instanceof Error ? error.message : "Invalid request body" },
      id: null,
    });
    return;
  }

  const server = createServer(registry);
  const transport = new StreamableHTTPServerTransport({ sessionIdGenerator: undefined, enableJsonResponse: true });
  res.on("close", () => {
    void transport.close();
    void server.close();
  });
  try {
    await server.connect(transport);
    await transport.handleRequest(req, res, body);
  } catch (error) {
    console.error("MCP request failed:", error);
    if (!res.headersSent) {
      sendJson(res, 500, { jsonrpc: "2.0", error: { code: -32603, message: "Internal server error" }, id: null });
    }
  }
});

httpServer.listen(PORT, HOST, () => {
  console.error(`Plexa MCP ${VERSION} listening on http://${HOST}:${PORT}/mcp`);
});
