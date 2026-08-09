import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import MessageCard from "../MessageCard";

const SOURCES = [
  {
    document: "Calendário de Graduação 2026.2",
    section: "Matrícula",
    excerpt: "O período de matrícula inicia em 27 de julho de 2026.",
    url: "https://saa.unb.br/calendario.pdf",
  },
  {
    document: "Documento sem URL",
    section: null,
    excerpt: "Trecho de documento sem endereço oficial.",
    url: null,
  },
];

describe("MessageCard — fontes clicáveis (T7.2 / RF2-02)", () => {
  it("exibe link 'Ver documento oficial' com target=_blank e rel seguro quando há url", async () => {
    render(<MessageCard agents_involved={["academico"]} sources={SOURCES} />);
    await userEvent.click(screen.getByText("Fontes"));

    const link = screen.getByRole("link", { name: /Abrir documento oficial/i });
    expect(link).toHaveTextContent("Ver documento oficial ↗");
    expect(link).toHaveAttribute("href", "https://saa.unb.br/calendario.pdf");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
    expect(link).toHaveAttribute(
      "aria-label",
      "Abrir documento oficial Calendário de Graduação 2026.2 em nova aba"
    );
  });

  it("não renderiza link para fonte sem url (sem link quebrado)", async () => {
    render(<MessageCard agents_involved={["academico"]} sources={SOURCES} />);
    await userEvent.click(screen.getByText("Fontes"));

    expect(screen.getByText("Documento sem URL")).toBeInTheDocument();
    expect(screen.getAllByRole("link")).toHaveLength(1);
  });

  it("exibe o trecho recuperado em destaque (.fonte-trecho)", async () => {
    const { container } = render(
      <MessageCard agents_involved={["academico"]} sources={SOURCES} />
    );
    await userEvent.click(screen.getByText("Fontes"));

    const trechos = container.querySelectorAll(".fonte-trecho");
    expect(trechos).toHaveLength(2);
    expect(trechos[0].textContent).toContain("matrícula inicia");
  });
});
