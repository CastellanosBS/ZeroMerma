// @vitest-environment jsdom

import { act, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, describe, expect, it } from "vitest";

import { KeyboardShortcutRegistry } from "../features/pos-shell/keyboard";
import {
  PosFilterBar,
  PosRecordList,
  PosRecordTable,
  PosSearchInput,
  type PosRecordColumn,
} from "./pos-records";

(
  globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }
).IS_REACT_ACT_ENVIRONMENT = true;

function renderUi(element: React.ReactElement) {
  const container = document.createElement("div");
  document.body.appendChild(container);

  const root = createRoot(container);
  act(() => {
    root.render(element);
  });

  return {
    container,
    root,
    unmount: () => {
      act(() => {
        root.unmount();
      });
      container.remove();
    },
  };
}

function dispatchKey(target: EventTarget, key: string, options?: Partial<KeyboardEventInit>) {
  const event = new KeyboardEvent("keydown", {
    bubbles: true,
    cancelable: true,
    key,
    ...options,
  });

  act(() => {
    target.dispatchEvent(event);
  });

  return event;
}

function focusElement(element: HTMLElement) {
  act(() => {
    element.focus();
  });
}

type DemoRecord = {
  id: string;
  label: string;
  status: "pending" | "success";
};

const demoRecords: DemoRecord[] = [
  { id: "record-1", label: "Pedido pendiente", status: "pending" },
  { id: "record-2", label: "Pedido entregado", status: "success" },
];

function SearchDemo() {
  const [value, setValue] = useState("");

  return (
    <KeyboardShortcutRegistry>
      <PosSearchInput
        ariaLabel="Buscar registros"
        onChange={setValue}
        placeholder="Buscar"
        value={value}
      />
    </KeyboardShortcutRegistry>
  );
}

function FilteredListDemo() {
  const [activeFilter, setActiveFilter] = useState<"all" | DemoRecord["status"]>("all");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const filteredRecords = useMemo(
    () =>
      activeFilter === "all"
        ? demoRecords
        : demoRecords.filter((record) => record.status === activeFilter),
    [activeFilter],
  );

  return (
    <div>
      <PosFilterBar
        chipFilters={[
          {
            isActive: activeFilter === "all",
            key: "all",
            label: "Todos",
            onSelect: () => setActiveFilter("all"),
          },
          {
            isActive: activeFilter === "pending",
            key: "pending",
            label: "Pendientes",
            onSelect: () => setActiveFilter("pending"),
          },
        ]}
        title="Historial"
      />
      <PosRecordList
        getKey={(record) => record.id}
        onSelect={(record) => setSelectedId(record.id)}
        records={filteredRecords}
        renderContent={(record) => <span>{record.label}</span>}
        selectedKey={selectedId}
      />
      <output data-testid="visible-count">{filteredRecords.length}</output>
      <output data-testid="selected-record">{selectedId ?? ""}</output>
    </div>
  );
}

function TableDemo() {
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const columns: PosRecordColumn<DemoRecord>[] = [
    {
      header: "Registro",
      key: "label",
      renderCell: (record) => record.label,
      width: "70%",
    },
    {
      align: "right",
      header: "Estado",
      key: "status",
      renderCell: (record) => record.status,
      width: "30%",
    },
  ];

  return (
    <div>
      <PosRecordTable
        columns={columns}
        getKey={(record) => record.id}
        getRowClassName={(record) => `status-row-${record.status.toLowerCase()}`}
        onSelect={(record) => setSelectedId(record.id)}
        records={demoRecords}
        selectedKey={selectedId}
        tableAriaLabel="Tabla de prueba"
      />
      <output data-testid="selected-table-record">{selectedId ?? ""}</output>
    </div>
  );
}

let mountedRoots: Array<() => void> = [];

afterEach(() => {
  for (const unmount of mountedRoots) {
    unmount();
  }
  mountedRoots = [];
  document.body.innerHTML = "";
});

describe("POS record primitives", () => {
  it("focuses the search input with Ctrl+F", () => {
    const view = renderUi(<SearchDemo />);
    mountedRoots.push(view.unmount);

    const input = view.container.querySelector("input");
    expect(input).not.toBeNull();

    dispatchKey(window, "f", { ctrlKey: true });

    expect(document.activeElement).toBe(input);
  });

  it("filters list records through the shared filter bar and selects a record", () => {
    const view = renderUi(<FilteredListDemo />);
    mountedRoots.push(view.unmount);

    const pendingFilter = Array.from(view.container.querySelectorAll("button")).find((button) =>
      button.textContent?.includes("Pendientes"),
    );
    expect(pendingFilter).not.toBeUndefined();

    act(() => {
      pendingFilter?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });

    expect(view.container.querySelector('[data-testid="visible-count"]')?.textContent).toBe("1");
    expect(view.container.textContent).toContain("Pedido pendiente");
    expect(view.container.textContent).not.toContain("Pedido entregado");

    const firstListButton = view.container.querySelector(
      ".pos-record-card__button",
    ) as HTMLButtonElement;
    expect(firstListButton).not.toBeNull();

    act(() => {
      firstListButton.click();
    });

    expect(view.container.querySelector('[data-testid="selected-record"]')?.textContent).toBe(
      "record-1",
    );
  });

  it("navigates table rows with arrows and selects with Enter", () => {
    const view = renderUi(<TableDemo />);
    mountedRoots.push(view.unmount);

    const rows = Array.from(view.container.querySelectorAll("tbody tr"));
    expect(rows).toHaveLength(2);
    expect(rows[0]?.classList.contains("status-row-pending")).toBe(true);

    focusElement(rows[0] as HTMLElement);
    expect(document.activeElement).toBe(rows[0]);

    dispatchKey(rows[0]!, "ArrowDown");
    expect(document.activeElement).toBe(rows[1]);

    dispatchKey(rows[1]!, "Enter");
    expect(view.container.querySelector('[data-testid="selected-table-record"]')?.textContent).toBe(
      "record-2",
    );
  });
});
