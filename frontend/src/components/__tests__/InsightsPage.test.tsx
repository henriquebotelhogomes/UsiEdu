import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import InsightsPage from "../InsightsPage";
import type { StoredUser } from "../../types";

const USER: StoredUser = {
  access_token: "token",
  token_type: "bearer",
  profile: "student",
  display_name: "Ana",
  email: "ana@demo.usiedu",
};

function renderPage(onLogout = () => {}) {
  return render(
    <MemoryRouter>
      <InsightsPage user={USER} onLogout={onLogout} />
    </MemoryRouter>
  );
}

function mockFetch(stats: unknown, recent: unknown, status = 200) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    const body = url.includes("/feedback/stats") ? stats : recent;
    return new Response(JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
});

describe("InsightsPage — página de satisfação (T8.2)", () => {
  it("exibe os cards de métricas e a tabela de feedbacks recentes", async () => {
    mockFetch(
      { total: 3, up: 2, down: 1, satisfaction: 0.6667 },
      {
        items: [
          {
            rating: "down",
            comment: "resposta incompleta",
            profile: "student",
            created_at: "2026-08-01T10:00:00+00:00",
            message_ref: "abcd1234",
          },
        ],
      }
    );

    renderPage();

    expect(await screen.findByText("3")).toBeInTheDocument();
    expect(screen.getByText(/Taxa de satisfação/)).toBeInTheDocument();
    expect(screen.getByText("67%")).toBeInTheDocument();
    expect(screen.getByText("resposta incompleta")).toBeInTheDocument();
    expect(screen.getByText("Estudante")).toBeInTheDocument();
    expect(screen.getByText("abcd1234")).toBeInTheDocument();
  });

  it("exibe estado vazio quando não há feedback registrado", async () => {
    mockFetch({ total: 0, up: 0, down: 0, satisfaction: 0 }, { items: [] });

    renderPage();

    expect(
      await screen.findByText("Ainda não há feedback registrado")
    ).toBeInTheDocument();
    // Sem feedbacks, a taxa mostra "—" (não 0%)
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("chama onLogout quando a API retorna 401 (sessão expirada)", async () => {
    mockFetch({}, {}, 401);
    const onLogout = vi.fn();

    renderPage(onLogout);

    await waitFor(() => expect(onLogout).toHaveBeenCalled());
  });
});
