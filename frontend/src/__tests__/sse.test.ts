import { describe, expect, it } from "vitest";
import { parseSseEvents } from "../api";

describe("parseSseEvents (T7.3)", () => {
  it("extrai eventos completos separados por linha em branco", () => {
    const buffer =
      'data: {"event": "meta", "session_id": "s1", "message_id": "m1"}\n\n' +
      'data: {"event": "token", "delta": "Olá"}\n\n';
    const { events, rest } = parseSseEvents(buffer);
    expect(events).toHaveLength(2);
    expect(events[0]).toEqual({ event: "meta", session_id: "s1", message_id: "m1" });
    expect(events[1]).toEqual({ event: "token", delta: "Olá" });
    expect(rest).toBe("");
  });

  it("mantém evento parcial no resto do buffer", () => {
    const buffer = 'data: {"event": "token", "delta": "A"}\n\ndata: {"event": "tok';
    const { events, rest } = parseSseEvents(buffer);
    expect(events).toHaveLength(1);
    expect(events[0]).toEqual({ event: "token", delta: "A" });
    expect(rest).toBe('data: {"event": "tok');
  });

  it("ignora linhas que não são data:", () => {
    const buffer = ': comentario keep-alive\nevent: x\ndata: {"event": "final", "agents": [], "sources": [], "usage": {}, "answer": "ok"}\n\n';
    const { events } = parseSseEvents(buffer);
    expect(events).toHaveLength(1);
    expect(events[0].event).toBe("final");
  });

  it("buffer vazio não produz eventos", () => {
    const { events, rest } = parseSseEvents("");
    expect(events).toHaveLength(0);
    expect(rest).toBe("");
  });
});
