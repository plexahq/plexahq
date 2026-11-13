import { encodeFunctionData, erc20Abi, maxUint256, parseAbi } from "viem";
import { describe, expect, it } from "vitest";
import { coerceArgs, decodeCall, isUnlimitedApproval, parseFunction } from "../src/abi.js";
import { classifyCode } from "../src/tools/evm.js";

describe("parseFunction", () => {
  it("accepts signatures with or without the function keyword", () => {
    expect(parseFunction("balanceOf(address) view returns (uint256)").name).toBe("balanceOf");
    expect(parseFunction("function totalSupply() view returns (uint256)").outputs).toHaveLength(1);
  });

  it("accepts a JSON ABI fragment", () => {
    const fn = parseFunction(
      JSON.stringify({ type: "function", name: "x", inputs: [], outputs: [], stateMutability: "view" }),
    );
    expect(fn.name).toBe("x");
  });

  it("rejects non-function items", () => {
    expect(() => parseFunction(JSON.stringify({ type: "event", name: "E", inputs: [] }))).toThrow();
  });
});

describe("coerceArgs", () => {
  const fn = parseFunction("f(uint256 a, bool b, address c, uint8[] d, (uint256 x, string y) t)");

  it("converts JSON-ish values to viem types", () => {
    const out = coerceArgs(fn.inputs, [
      "1000000000000000000000",
      "true",
      "0x0000000000000000000000000000000000000001",
      [1, "2"],
      { x: "5", y: "hi" },
    ]);
    expect(out[0]).toBe(1000000000000000000000n);
    expect(out[1]).toBe(true);
    expect(out[3]).toEqual([1n, 2n]);
    expect(out[4]).toEqual({ x: 5n, y: "hi" });
  });

  it("rejects wrong argument counts and unsafe numbers", () => {
    expect(() => coerceArgs(fn.inputs, [])).toThrow(/Expected 5/);
    const single = parseFunction("g(uint256 a)");
    expect(() => coerceArgs(single.inputs, [2 ** 60])).toThrow(/strings/);
  });
});

describe("decodeCall", () => {
  it("decodes ERC-20 approve", () => {
    const data = encodeFunctionData({
      abi: erc20Abi,
      functionName: "approve",
      args: ["0x000000000000000000000000000000000000dEaD", maxUint256],
    });
    const decoded = decodeCall(data)!;
    expect(decoded.functionName).toBe("approve");
    expect(decoded.source).toBe("erc20");
    expect(isUnlimitedApproval(decoded.args.amount)).toBe(true);
  });

  it("falls back to a verified ABI", () => {
    const abi = parseAbi(["function deposit(uint256 assets, address receiver)"]);
    const data = encodeFunctionData({
      abi,
      functionName: "deposit",
      args: [10n, "0x0000000000000000000000000000000000000002"],
    });
    expect(decodeCall(data)).toBeUndefined();
    const decoded = decodeCall(data, abi)!;
    expect(decoded.functionName).toBe("deposit");
    expect(decoded.args.assets).toBe(10n);
    expect(decoded.source).toBe("verified-abi");
  });
});

describe("classifyCode", () => {
  it("recognizes empty accounts, EIP-7702 delegations and contracts", () => {
    expect(classifyCode("0x")).toEqual({ kind: "empty" });
    expect(classifyCode(undefined)).toEqual({ kind: "empty" });
    expect(classifyCode("0xef01005a7fc11397e9a8ad41bf10bf13f22b0a63f96f6d")).toEqual({
      kind: "delegated",
      delegate: "0x5A7FC11397E9a8AD41BF10bf13F22B0a63f96f6d",
    });
    expect(classifyCode("0x6080604052")).toEqual({ kind: "contract", bytes: 5 });
  });
});
