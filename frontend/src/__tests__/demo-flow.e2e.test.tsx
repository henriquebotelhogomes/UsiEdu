import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import App from "../App";

const MESSAGE_ID = "123e4567-e89b-12d3-a456-426614174000";

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function sseResponse() {
  const encoder = new TextEncoder();
  const body = [
    `data: ${JSON.stringify({ event: "meta", message_id: MESSAGE_ID })}\n\n`,
    `data: ${JSON.stringify({ event: "token", delta: "Resposta demo auditável." })}\n\n`,
    `data: ${JSON.stringify({
      event: "final",
      answer: "Resposta demo auditável.",
      agents: ["academico"],
      sources: [],
    })}\n\n`,
  ].join("");
  return new Response(
    new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode(body));
        controller.close();
      },
    }),
    { status: 200, headers: { "Content-Type": "text/event-stream" } }
  );
}

describe("fluxo demo E2E T03.2", () => {
  beforeEach(() => {
    localStorage.clear();
    Element.prototype.scrollIntoView = vi.fn();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it("executa login, chat, feedback e insights sem expor credenciais na evidência", async () => {
    const requests: Array<{ url: string; method: string; body?: unknown }> = [];
    let feedbackRegistered = false;
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? "GET";
      const request: { url: string; method: string; body?: unknown } = { url, method };
      if (init?.body) request.body = JSON.parse(String(init.body));
      requests.push(request);

      if (url === "/auth/login") {
        return jsonResponse({
          access_token: "e2e-token-not-exported",
          token_type: "bearer",
          profile: "student",
          display_name: "Ana Souza",
        });
      }
      if (url.startsWith("/chat/history")) {
        return jsonResponse({ detail: "Sessão ainda não existe" }, 404);
      }
      if (url === "/chat/stream") return sseResponse();
      if (url === "/feedback" && method === "POST") {
        feedbackRegistered = true;
        return jsonResponse({ feedback_id: 1 });
      }
      if (url === "/feedback/stats") {
        return jsonResponse({
          total: feedbackRegistered ? 1 : 0,
          up: feedbackRegistered ? 1 : 0,
          down: 0,
          satisfaction: feedbackRegistered ? 1 : 0,
        });
      }
      if (url.startsWith("/feedback/recent")) {
        return jsonResponse({
          items: feedbackRegistered
            ? [
                {
                  rating: "up",
                  comment: null,
                  profile: "student",
                  created_at: "2026-08-12T00:00:00+00:00",
                  message_ref: "e2e12345",
                },
              ]
            : [],
        });
      }
      throw new Error(`Requisição E2E inesperada: ${method} ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(
      <MemoryRouter initialEntries={["/login"]}>
        <App />
      </MemoryRouter>
    );

    await user.click(screen.getByText("Ana Souza"));
    await user.click(screen.getByRole("button", { name: "Entrar" }));
    expect(await screen.findByText("Bem-vindo ao UsiEdu!")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Notas e faltas" }));
    expect(await screen.findByText("Resposta demo auditável.")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Resposta útil" }));
    await waitFor(() => expect(feedbackRegistered).toBe(true));
    await user.click(screen.getByRole("link", { name: "Satisfação" }));

    expect(await screen.findByText("100%")).toBeInTheDocument();
    expect(screen.getByText("e2e12345")).toBeInTheDocument();

    const evidence = requests.map(({ url, method }) => ({ url, method }));
    const serializedEvidence = JSON.stringify(evidence);
    expect(serializedEvidence).not.toContain("estudante123");
    expect(serializedEvidence).not.toContain("e2e-token-not-exported");
    expect(evidence).toEqual(
      expect.arrayContaining([
        { url: "/auth/login", method: "POST" },
        { url: "/chat/stream", method: "POST" },
        { url: "/feedback", method: "POST" },
        { url: "/feedback/stats", method: "GET" },
        { url: "/feedback/recent?limit=20", method: "GET" },
      ])
    );
  });

  it("exibe uma mensagem útil quando o serviço de chat está indisponível", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/auth/login") {
        return jsonResponse({
          access_token: "e2e-token-not-exported",
          token_type: "bearer",
          profile: "student",
          display_name: "Ana Souza",
        });
      }
      if (url.startsWith("/chat/history")) {
        return jsonResponse({ detail: "Sessão ainda não existe" }, 404);
      }
      if (url === "/chat/stream" || url === "/chat") {
        return jsonResponse(
          { detail: "Chat temporariamente indisponível. Tente novamente mais tarde." },
          503
        );
      }
      throw new Error(`Requisição E2E inesperada: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(
      <MemoryRouter initialEntries={["/login"]}>
        <App />
      </MemoryRouter>
    );

    await user.click(screen.getByText("Ana Souza"));
    await user.click(screen.getByRole("button", { name: "Entrar" }));
    await screen.findByText("Bem-vindo ao UsiEdu!");
    await user.click(screen.getByRole("button", { name: "Notas e faltas" }));

    expect(
      await screen.findByText("Chat temporariamente indisponível. Tente novamente mais tarde.")
    ).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "/chat",
      expect.objectContaining({ method: "POST" })
    );
  });
});
