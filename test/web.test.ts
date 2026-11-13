import { describe, expect, it } from "vitest";
import { handleHealth, handleMcpRequest } from "../src/web.js";

const MCP_HEADERS = {
  "content-type": "application/json",
  accept: "application/json, text/event-stream",
  "mcp-protocol-version": "2025-06-18",
};

function post(body: unknown): Request {
  return new Request("http://localhost/mcp", { method: "POST", headers: MCP_HEADERS, body: JSON.stringify(body) });
}

describe("handleMcpRequest", () => {
  it("initializes and lists tools statelessly", async () => {
    const init = await handleMcpRequest(
      post({
        jsonrpc: "2.0",
        id: 1,
        method: "initialize",
        params: { protocolVersion: "2025-06-18", capabilities: {}, clientInfo: { name: "t", version: "0" } },
      }),
    );
    expect(init.status).toBe(200);
    expect(init.headers.get("access-control-allow-origin")).toBe("*");
    const initBody = (await init.json()) as { result: { serverInfo: { name: string } } };
    expect(initBody.result.serverInfo.name).toBe("plexa");

    const list = await handleMcpRequest(post({ jsonrpc: "2.0", id: 2, method: "tools/list" }));
    const listBody = (await list.json()) as { result: { tools: { name: string }[] } };
    expect(listBody.result.tools.map((t) => t.name)).toContain("simulate_transaction");
  });

  it("runs a tool that needs no network", async () => {
    const res = await handleMcpRequest(
      post({ jsonrpc: "2.0", id: 3, method: "tools/call", params: { name: "list_chains", arguments: {} } }),
    );
    const body = (await res.json()) as { result: { content: { text: string }[] } };
    expect(body.result.content[0]!.text).toContain("zero-atlas");
  });

  it("handles CORS preflight, GET and bad JSON", async () => {
    expect((await handleMcpRequest(new Request("http://localhost/mcp", { method: "OPTIONS" }))).status).toBe(204);
    const get = await handleMcpRequest(new Request("http://localhost/mcp"));
    expect(get.status).toBe(405);
    expect(((await get.json()) as { message: string }).message).toMatch(/MCP endpoint/);
    const bad = await handleMcpRequest(
      new Request("http://localhost/mcp", { method: "POST", headers: MCP_HEADERS, body: "{bad" }),
    );
    expect(bad.status).toBe(400);
  });
});

describe("handleHealth", () => {
  it("reports ok", async () => {
    expect(await handleHealth().json()).toMatchObject({ ok: true, name: "plexa" });
  });
});
