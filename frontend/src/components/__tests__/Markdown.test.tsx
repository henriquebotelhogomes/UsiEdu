import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import Markdown from "../Markdown";

describe("Markdown (T7.1 / RF2-01)", () => {
  it("renderiza negrito e título sem marcadores visíveis", () => {
    render(<Markdown content={"### Feriados 2026\nResposta com **negrito** aqui."} />);
    expect(screen.getByText("Feriados 2026")).toBeInTheDocument();
    expect(screen.getByText("Feriados 2026").tagName).toBe("H3");
    expect(screen.getByText("negrito")).toBeInTheDocument();
    expect(screen.getByText("negrito").tagName).toBe("STRONG");
    expect(screen.getByText(/feriados/i)).not.toHaveTextContent("###");
    expect(screen.getByText(/negrito/i)).not.toHaveTextContent("**");
  });

  it("renderiza lista numerada e lista com marcadores", () => {
    render(<Markdown content={"1. Primeiro\n2. Segundo\n\n- Item A\n- Item B"} />);
    const items = screen.getAllByRole("listitem");
    expect(items.map((li) => li.textContent)).toEqual([
      "Primeiro",
      "Segundo",
      "Item A",
      "Item B",
    ]);
  });

  it("renderiza link com target=_blank e rel seguro", () => {
    render(<Markdown content={"Veja o [calendário](https://example.com/cal.pdf) oficial."} />);
    const link = screen.getByRole("link", { name: "calendário" });
    expect(link).toHaveAttribute("href", "https://example.com/cal.pdf");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("renderiza tabela GFM com cabeçalho e células", () => {
    render(<Markdown content={"| Data | Feriado |\n|---|---|\n| 01/01 | Confraternização |"} />);
    const table = screen.getByRole("table");
    expect(table).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Data" })).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "Confraternização" })).toBeInTheDocument();
  });

  it("não executa HTML cru presente na resposta", () => {
    const malicious =
      'Tentativa: <img src="x" onerror="window.__pwned = true"><script>window.__pwned = true</script>';
    render(<Markdown content={malicious} />);
    expect(document.querySelector("img")).toBeNull();
    expect(document.querySelector("script")).toBeNull();
    expect((window as unknown as { __pwned?: boolean }).__pwned).toBeUndefined();
  });

  it("mantém quebras de linha simples como <br> (remark-breaks)", () => {
    const { container } = render(<Markdown content={"linha um\nlinha dois"} />);
    expect(container.querySelector("br")).not.toBeNull();
  });
});
