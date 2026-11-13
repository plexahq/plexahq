import type { CallToolResult } from "@modelcontextprotocol/sdk/types.js";
import { BaseError } from "viem";

/** JSON.stringify that turns bigint into decimal strings. */
export function toJson(value: unknown): string {
  return JSON.stringify(value, (_k, v) => (typeof v === "bigint" ? v.toString() : v), 2);
}

export function ok(value: unknown): CallToolResult {
  return { content: [{ type: "text", text: toJson(value) }] };
}

export function fail(error: unknown): CallToolResult {
  return { isError: true, content: [{ type: "text", text: errorMessage(error) }] };
}

export function errorMessage(error: unknown): string {
  if (error instanceof BaseError) return error.shortMessage || error.message;
  if (error instanceof Error) return error.message;
  return String(error);
}

/** Wraps a tool handler so thrown errors become MCP tool errors instead of protocol errors. */
export function safe<A>(handler: (args: A) => Promise<unknown>): (args: A) => Promise<CallToolResult> {
  return async (args: A) => {
    try {
      return ok(await handler(args));
    } catch (error) {
      return fail(error);
    }
  };
}
