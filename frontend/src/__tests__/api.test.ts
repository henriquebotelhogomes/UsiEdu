import { afterEach, beforeEach, describe, expect, it } from "vitest";
import {
  clearStoredSession,
  getSessionIdFor,
  loadStoredSession,
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
