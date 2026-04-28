// @vitest-environment jsdom

import { renderToStaticMarkup } from "react-dom/server";
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  OperationConfirmationDialog,
  OperationDocumentResult,
  OperationDocumentSummaryPanel,
  OperationHistoryList,
} from "./operation-documents";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT =
  true;

let mountedRoots: Array<() => void> = [];

afterEach(() => {
  for (const unmount of mountedRoots) {
    unmount();
  }
  mountedRoots = [];
  document.body.innerHTML = "";
});

function renderUi(element: React.ReactElement) {
  const container = document.createElement("div");
  document.body.appendChild(container);

  const root = createRoot(container);
  act(() => {
    root.render(element);
  });

  return {
    container,
    unmount: () => {
      act(() => {
        root.unmount();
      });
      container.remove();
    },
  };
}

describe("operation document shared infrastructure", () => {
  it("renders a canonical confirmation dialog with summary details", () => {
    const markup = renderToStaticMarkup(
      <OperationConfirmationDialog
        confirmLabel="Confirmar envio"
        context={{
          branchName: "Main Branch",
          userName: "Main Branch Cashier",
          workstationName: "POS-01",
        }}
        isOpen
        kind="branchShipment"
        lines={[
          {
            key: "line-1",
            quantityText: "12 uds",
            secondaryText: "PAN-DULCE / PAN001",
            title: "Caja de pan dulce",
          },
        ]}
        metrics={[
          { key: "line-count", label: "Lineas", value: "1" },
          { key: "units", label: "Unidades", tone: "financial", value: "12.000" },
        ]}
        onCancel={() => {}}
        onConfirm={() => {}}
        referenceValue="ENV-001"
        timestamps={{
          committedAtValue: "22 abr 2026, 5:00 p.m.",
          createdAtValue: "22 abr 2026, 4:58 p.m.",
        }}
      />,
    );

    expect(markup).toContain('data-operation-confirmation-dialog="true"');
    expect(markup).toContain("Confirmar envio");
    expect(markup).toContain("ENV-001");
    expect(markup).toContain("Caja de pan dulce");
    expect(markup).toContain("Main Branch");
  });

  it("renders a result panel and summary panel with operational actions", () => {
    const onPrint = vi.fn();
    const onHistory = vi.fn();
    const onNewOperation = vi.fn();
    const onCopy = vi.fn();

    const resultView = renderUi(
      <OperationDocumentResult
        actions={[
          { key: "print", label: "Imprimir", onSelect: onPrint, variant: "secondary" },
          { key: "history", label: "Ver historial", onSelect: onHistory, variant: "neutral" },
          { key: "new", label: "Nueva operacion", onSelect: onNewOperation, variant: "primary" },
        ]}
        context={{
          branchName: "Main Branch",
          userName: "Main Branch Cashier",
          workstationName: "POS-01",
        }}
        kind="waste"
        metrics={[{ key: "units", label: "Unidades", value: "4.000" }]}
        referenceValue="MER-001"
        timestamps={{ committedAtValue: "22 abr 2026, 5:15 p.m." }}
      />,
    );
    mountedRoots.push(resultView.unmount);

    const resultButtons = Array.from(resultView.container.querySelectorAll("button"));
    expect(resultButtons.length).toBeGreaterThanOrEqual(4);

    act(() => {
      resultButtons[0]?.click();
      resultButtons[1]?.click();
      resultButtons[2]?.click();
    });

    expect(onPrint).toHaveBeenCalledTimes(1);
    expect(onHistory).toHaveBeenCalledTimes(1);
    expect(onNewOperation).toHaveBeenCalledTimes(1);

    const summaryView = renderUi(
      <OperationDocumentSummaryPanel
        actions={[{ key: "copy", label: "Copiar folio", onSelect: onCopy, variant: "neutral" }]}
        blockers={[{ key: "missing-line", message: "Agrega al menos una linea.", tone: "warning" }]}
        kind="correction"
        lines={[
          {
            key: "line-1",
            quantityText: "-2 uds",
            secondaryText: "BOLILLO / BOL001",
            statusLabel: "Ajuste",
            statusTone: "warning",
            title: "Bolillo",
          },
        ]}
        referenceValue="COR-001"
        stateLabel="Listo para confirmar"
      />,
    );
    mountedRoots.push(summaryView.unmount);

    expect(summaryView.container.textContent).toContain("COR-001");
    expect(summaryView.container.textContent).toContain("Agrega al menos una linea.");

    const copyButton = Array.from(summaryView.container.querySelectorAll("button")).find((button) =>
      button.textContent?.includes("Copiar folio"),
    );

    act(() => {
      copyButton?.click();
    });

    expect(onCopy).toHaveBeenCalledTimes(1);
  });

  it("renders a reusable operation history list", () => {
    const markup = renderToStaticMarkup(
      <OperationHistoryList
        onSelect={() => {}}
        records={[
          {
            folio: "REC-001",
            id: "history-1",
            metrics: [{ key: "units", label: "Unidades", value: "10.000" }],
            primaryTimestampLabel: "Confirmado",
            primaryTimestampValue: "22 abr 2026, 5:20 p.m.",
            statusLabel: "Confirmado",
            statusTone: "success",
            subtitle: "Sucursal Norte -> Main Branch",
            title: "Recepcion de envio",
          },
        ]}
        selectedRecordId="history-1"
      />,
    );

    expect(markup).toContain('data-operation-history-list="true"');
    expect(markup).toContain("REC-001");
    expect(markup).toContain("Recepcion de envio");
    expect(markup).toContain("Unidades: 10.000");
  });
});
