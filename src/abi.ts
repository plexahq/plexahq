import {
  decodeFunctionData,
  erc20Abi,
  formatUnits,
  maxUint256,
  parseAbiItem,
  type Abi,
  type AbiFunction,
  type AbiParameter,
} from "viem";

/**
 * Parses a function given either as a human-readable signature
 * ("function balanceOf(address) view returns (uint256)", or just "balanceOf(address)")
 * or as a JSON ABI fragment.
 */
export function parseFunction(signature: string): AbiFunction {
  const trimmed = signature.trim();
  if (trimmed.startsWith("{")) {
    const item = JSON.parse(trimmed) as AbiFunction;
    if (item.type !== "function") throw new Error("ABI fragment must have type \"function\"");
    return item;
  }
  const withKeyword = trimmed.startsWith("function ") ? trimmed : `function ${trimmed}`;
  const item = parseAbiItem(withKeyword);
  if (item.type !== "function") throw new Error("Signature must describe a function");
  return item as AbiFunction;
}

/**
 * Converts loosely-typed JSON arguments (as an AI client sends them) into the types viem expects:
 * integers become bigint, "true"/"false" become booleans, tuples and arrays are converted recursively.
 */
export function coerceArgs(params: readonly AbiParameter[], args: readonly unknown[]): unknown[] {
  if (args.length !== params.length) {
    throw new Error(`Expected ${params.length} argument(s), got ${args.length}`);
  }
  return params.map((p, i) => coerceValue(p, args[i]));
}

function coerceValue(param: AbiParameter, value: unknown): unknown {
  const type = param.type;
  const arrayMatch = /^(.*)\[(\d*)\]$/.exec(type);
  if (arrayMatch) {
    if (!Array.isArray(value)) throw new Error(`Argument "${param.name ?? type}" must be an array`);
    const inner = { ...param, type: arrayMatch[1]! } as AbiParameter;
    return value.map((v) => coerceValue(inner, v));
  }
  if (type === "tuple") {
    const components = (param as { components?: readonly AbiParameter[] }).components ?? [];
    if (Array.isArray(value)) return coerceArgs(components, value);
    if (typeof value === "object" && value !== null) {
      const obj = value as Record<string, unknown>;
      return Object.fromEntries(components.map((c) => [c.name, coerceValue(c, obj[c.name ?? ""])]));
    }
    throw new Error(`Argument "${param.name ?? type}" must be an object or array`);
  }
  if (/^u?int\d*$/.test(type)) {
    if (typeof value === "bigint") return value;
    if (typeof value === "number") {
      if (!Number.isSafeInteger(value)) throw new Error(`Pass large integers as strings (argument "${param.name ?? type}")`);
      return BigInt(value);
    }
    if (typeof value === "string" && /^-?(0x[0-9a-fA-F]+|\d+)$/.test(value.trim())) return BigInt(value.trim());
    throw new Error(`Argument "${param.name ?? type}" must be an integer`);
  }
  if (type === "bool") {
    if (typeof value === "boolean") return value;
    if (value === "true") return true;
    if (value === "false") return false;
    throw new Error(`Argument "${param.name ?? type}" must be a boolean`);
  }
  return value;
}

export interface DecodedCall {
  functionName: string;
  args: Record<string, unknown>;
  source: "erc20" | "verified-abi";
}

/** Decodes calldata against the ERC-20 ABI first, then against an optional verified ABI. */
export function decodeCall(data: `0x${string}`, verifiedAbi?: Abi): DecodedCall | undefined {
  const attempts: [Abi, DecodedCall["source"]][] = [[erc20Abi, "erc20"]];
  if (verifiedAbi && verifiedAbi.length > 0) attempts.push([verifiedAbi, "verified-abi"]);
  for (const [abi, source] of attempts) {
    try {
      const decoded = decodeFunctionData({ abi, data });
      const fn = abi.find(
        (item): item is AbiFunction => item.type === "function" && item.name === decoded.functionName,
      );
      const args: Record<string, unknown> = {};
      (decoded.args ?? []).forEach((value, i) => {
        args[fn?.inputs[i]?.name || `arg${i}`] = value;
      });
      return { functionName: decoded.functionName, args, source };
    } catch {
      // try the next ABI
    }
  }
  return undefined;
}

export function isUnlimitedApproval(amount: unknown): boolean {
  return typeof amount === "bigint" && amount >= maxUint256 / 2n;
}

export function formatAmount(raw: bigint, decimals: number, symbol?: string): string {
  const formatted = formatUnits(raw, decimals);
  return symbol ? `${formatted} ${symbol}` : formatted;
}
