import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  RATE_LIMIT_MESSAGE,
  RateLimitError,
  clearStoredSession,
  getSessionIdFor,
  loadStoredSession,
  sendChat,
  sendChatStream,
  setToken,
  storeSession,
  storeSessionId,
} from "../api";
import type { StoredUser } from "../types";

const USER: StoredUser = {
  access_token: "token-123",
  token_type: "bearer",
  profile: "student",
  display_name: "Ana Souza",
  email: "ana@demo.usiedu",
};

describe("persistência de sessão (T7.4)", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    localStorage.clear();
    setToken(null);
  });

  it("storeSession + loadStoredSession fazem round-trip", () => {
    storeSession(USER);
    const restored = loadStoredSession();
    expect(restored).not.toBeNull();
    expect(restored?.email).toBe("ana@demo.usiedu");
    expect(restored?.access_token).toBe("token-123");
    expect(restored?.profile).toBe("student");
  });

  it("loadStoredSession retorna null sem dados", () => {
    expect(loadStoredSession()).toBeNull();
  });

  it("loadStoredSession retorna null sem token", () => {
    storeSession(USER);
    localStorage.removeItem("usiedu_token");
    expect(loadStoredSession()).toBeNull();
  });

  it("clearStoredSession remove token e usuário", () => {
    storeSession(USER);
    clearStoredSession();
    expect(loadStoredSession()).toBeNull();
  });

  it("session id do chat é persistido por usuário", () => {
    storeSessionId("ana@demo.usiedu", "sess-1");
    storeSessionId("carlos@demo.usiedu", "sess-2");
    expect(getSessionIdFor("ana@demo.usiedu")).toBe("sess-1");
    expect(getSessionIdFor("carlos@demo.usiedu")).toBe("sess-2");
    expect(getSessionIdFor("ninguem@demo.usiedu")).toBeNull();
  });

  it("setToken persiste e remove o token no localStorage", () => {
    setToken("tok-abc");
    expect(localStorage.getItem("usiedu_token")).toBe("tok-abc");
    setToken(null);
    expect(localStorage.getItem("usiedu_token")).toBeNull();
  });
});

describe("rate limiting 429 (T9.1)", () => {
  beforeEach(() => {
    localStorage.clear();
    setToken("token-123");
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    localStorage.clear();
    setToken(null);
  });

  function mockFetch429() {
    const fetchMock = vi.fn(async () =>
      new Response(JSON.stringify({ detail: "Limite de requisições excedido" }), {
        status: 429,
        headers: { "Content-Type": "application/json", "Retry-After": "30" },
      })
    );
    vi.stubGlobal("fetch", fetchMock);
  }

  it("sendChat lança RateLimitError com mensagem amigável no 429", async () => {
    mockFetch429();
    await expect(
      sendChat({ session_id: "s1", message: "olá" })
    ).rejects.toThrow(RateLimitError);
    await expect(
      sendChat({ session_id: "s1", message: "olá" })
    ).rejects.toThrow(RATE_LIMIT_MESSAGE);
  });

  it("sendChatStream lança RateLimitError com mensagem amigável no 429", async () => {
    mockFetch429();
    await expect(
      sendChatStream({ session_id: "s1", message: "olá" }, {})
    ).rejects.toThrow(RATE_LIMIT_MESSAGE);
  });
});
