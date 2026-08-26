import { useMutation } from "@tanstack/react-query";
import { Navigate, useNavigate, useRouterState } from "@tanstack/react-router";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { useAppShellRightPanel } from "../../components/app-shell-right-panel";
import {
  CopyFolioAction,
  PrintAction,
} from "../../components/document-actions";
import { OperationalStatus } from "../../components/operational-status";
import {
  PosErrorState,
  PosInlineValidationMessage,
} from "../../components/pos-feedback";
import { PosButton, PosStatusBadge } from "../../components/pos-foundations";
import {
  PosHistoryView,
  PosRecordTable,
  type PosRecordColumn,
  PosRecordDetailPanel,
} from "../../components/pos-records";
import { RotateCcwIcon } from "../../components/pos-icons";
import {
  CentralWorkspaceSheet,
  CompactPageHeader,
  FilterButton,
  KeyValueRow,
  ModuleStateChip,
  SearchField,
  ScrollPane,
} from "../../components/pos-module-primitives";
import { appEnv } from "../../env";
import type {
  TicketDetailResponse,
  TicketListItemView,
  TicketReprintRequest,
  TicketScopeView,
} from "../../lib/api-contracts";
import {
  formatCompactLocalDateTime,
  formatCurrency,
  formatLocalDateTime,
} from "../../lib/formatters";
import { toOperationalErrorMessage } from "../../lib/http";
import { isEditableTarget } from "../../lib/keyboard-shortcuts";
import { openBrowserPrintWindow } from "../../lib/browser-print";
import { matchesScannerValue, normalizeScannerText, parseTicketScannerValue } from "../../lib/scanner";
import { getDocumentActionAvailability } from "../../lib/document-actions";
import { usePosAuthStore } from "../auth/auth-store";
import { useCurrentCashSessionQuery } from "../cash-session-open/queries";
import { posInputClass } from "../pos-theme/theme";
import { useStatusMessageStore } from "../status-messages/store";
import { writeTicketToPrintWindow } from "./print";
import { useTicketDetailQuery, useTicketsBootstrapQuery, useTicketsListQuery } from "./queries";
import { reprintTicket } from "./tickets-api";

type TicketConsoleState =
  | "LOADING_RESULTS"
  | "NO_RESULTS"
  | "RESULTS_AVAILABLE"
  | "TICKET_SELECTED"
  | "REPRINTING"
  | "REPRINT_SUCCESS"
  | "REPRINT_ERROR";

type ReprintFeedbackState =
  | { kind: "idle"; ticketId: null }
  | { kind: "success"; ticketId: string }
  | { kind: "error"; ticketId: string };

function createRequestId(scope: string): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return `${scope}-${crypto.randomUUID()}`;
  }

  return `${scope}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function useDebouncedValue(value: string, delayMs: number): string {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const timeout = window.setTimeout(() => setDebouncedValue(value), delayMs);
    return () => window.clearTimeout(timeout);
  }, [delayMs, value]);

  return debouncedValue;
}

function formatQuantity(quantity: number | string): string {
  return new Intl.NumberFormat("es-MX", {
    maximumFractionDigits: 3,
    minimumFractionDigits: 0,
  }).format(Number(quantity));
}

function getPaymentMethodLabel(code: string): string {
  switch (code) {
    case "CASH":
      return "Efectivo";
    case "CARD":
      return "Tarjeta";
    case "MIXED":
      return "Mixto";
    default:
      return code;
  }
}

function getTicketStatusLabel(status: string): string {
  switch (status) {
    case "CONFIRMED":
      return "Confirmado";
    default:
      return status;
  }
}

function getTicketStatusTone(status: string) {
  switch (status) {
    case "CONFIRMED":
      return "confirmed" as const;
    default:
      return "draft" as const;
  }
}

function getTicketReturnStatusLabel(returnStatus: string): string | null {
  switch (returnStatus) {
    case "PARTIALLY_RETURNED":
      return "Devolucion parcial";
    case "FULLY_RETURNED":
      return "Devuelto";
    default:
      return null;
  }
}

function getTicketReturnStatusTone(returnStatus: string) {
  switch (returnStatus) {
    case "PARTIALLY_RETURNED":
      return "warning" as const;
    case "FULLY_RETURNED":
      return "success" as const;
    default:
      return "draft" as const;
  }
}

function getScopeContextLabel(scope: string): string {
  switch (scope) {
    case "CURRENT_SHIFT":
      return "Mostrando tickets del turno actual";
    case "TODAY":
      return "Mostrando tickets de hoy";
    case "RECENT":
      return "Mostrando tickets recientes";
    default:
      return "Mostrando tickets del alcance actual";
  }
}

function getPaymentSummaryLabel(
  payments: Array<{
    payment_method_code: string;
  }>,
): string {
  if (payments.length === 0) {
    return "Sin pagos registrados";
  }

  return payments.map((payment) => getPaymentMethodLabel(payment.payment_method_code)).join(" | ");
}

function formatTicketCountLabel(count: number): string {
  return `${count} ${count === 1 ? "ticket" : "tickets"}`;
}

function getTicketConsoleState({
  hasResults,
  isLoadingResults,
  isReprintPending,
  reprintFeedback,
  selectedTicket,
}: {
  hasResults: boolean;
  isLoadingResults: boolean;
  isReprintPending: boolean;
  reprintFeedback: ReprintFeedbackState;
  selectedTicket: TicketDetailResponse | null;
}): TicketConsoleState {
  if (isReprintPending) {
    return "REPRINTING";
  }

  if (
    selectedTicket &&
    reprintFeedback.kind === "success" &&
    reprintFeedback.ticketId === selectedTicket.id
  ) {
    return "REPRINT_SUCCESS";
  }

  if (
    selectedTicket &&
    reprintFeedback.kind === "error" &&
    reprintFeedback.ticketId === selectedTicket.id
  ) {
    return "REPRINT_ERROR";
  }

  if (selectedTicket) {
    return "TICKET_SELECTED";
  }

  if (isLoadingResults) {
    return "LOADING_RESULTS";
  }

  if (!hasResults) {
    return "NO_RESULTS";
  }

  return "RESULTS_AVAILABLE";
}

function getTicketConsoleStateLabel(state: TicketConsoleState): string {
  switch (state) {
    case "LOADING_RESULTS":
      return "Buscando";
    case "NO_RESULTS":
      return "Sin resultados";
    case "RESULTS_AVAILABLE":
      return "Lista disponible";
    case "TICKET_SELECTED":
      return "Listo para consulta";
    case "REPRINTING":
      return "Reimprimiendo";
    case "REPRINT_SUCCESS":
      return "Reimpresion enviada";
    case "REPRINT_ERROR":
      return "Error de reimpresion";
    default:
      return "Tickets";
  }
}

function getTicketConsoleStateTone(
  state: TicketConsoleState,
): "muted" | "primary" | "success" | "warning" {
  switch (state) {
    case "REPRINTING":
    case "TICKET_SELECTED":
    case "RESULTS_AVAILABLE":
      return "primary";
    case "REPRINT_SUCCESS":
      return "success";
    case "REPRINT_ERROR":
      return "warning";
    default:
      return "muted";
  }
}

function getReprintStateTone(
  state: TicketConsoleState,
): "draft" | "pending" | "ready" | "success" | "warning" {
  switch (state) {
    case "REPRINTING":
      return "pending";
    case "REPRINT_SUCCESS":
      return "success";
    case "REPRINT_ERROR":
      return "warning";
    case "TICKET_SELECTED":
    case "RESULTS_AVAILABLE":
      return "ready";
    default:
      return "draft";
  }
}

function getEmptyListDescription(scopeLabel: string, searchText: string): string {
  if (searchText.trim().length > 0) {
    return "No hay tickets con ese folio dentro del alcance actual.";
  }

  return `${scopeLabel}. Aun no hay tickets emitidos para esta consulta.`;
}

export function TicketSummaryPanel({
  consoleState,
  detailError,
  isDetailPending,
  isReprintPending,
  onReprint,
  onStartReturn,
  selectedTicket,
}: {
  consoleState: TicketConsoleState;
  detailError: unknown;
  isDetailPending: boolean;
  isReprintPending: boolean;
  onReprint: (ticketId: string) => void;
  onStartReturn: (saleId: string) => void;
  selectedTicket: TicketDetailResponse | null;
}) {
  const documentActionAvailability = getDocumentActionAvailability("saleTicket");

  return (
    <PosRecordDetailPanel
      badge={
        <PosStatusBadge status={getReprintStateTone(consoleState)}>
          {getTicketConsoleStateLabel(consoleState)}
        </PosStatusBadge>
      }
      description="Estado operativo del ticket y acciones disponibles."
      title="Ticket seleccionado"
      footer={
        selectedTicket ? (
          <div className="grid gap-2">
            <PrintAction
              disabled={
                isReprintPending ||
                !selectedTicket.can_reprint ||
                !documentActionAvailability.print.isAvailable
              }
              isPending={isReprintPending}
              label={selectedTicket.can_reprint ? "Reimprimir" : documentActionAvailability.print.label}
              onPrint={() => onReprint(selectedTicket.id)}
              title={
                !selectedTicket.can_reprint
                  ? "La reimpresion no esta disponible para este ticket."
                  : documentActionAvailability.print.unavailableReason
              }
              variant="primary"
            />
            <div className="grid grid-cols-[1fr_1fr] gap-2">
              <CopyFolioAction referenceValue={selectedTicket.folio} />
              {selectedTicket.has_returnable_quantity ? (
                <PosButton
                  leadingIcon={<RotateCcwIcon className="h-4 w-4" />}
                  onClick={() => onStartReturn(selectedTicket.id)}
                  variant="secondary"
                >
                  Iniciar devolucion
                </PosButton>
              ) : null}
            </div>
          </div>
        ) : undefined
      }
    >
      {isDetailPending ? (
        <OperationalStatus
          description="Consultando el detalle del ticket."
          title="Ticket seleccionado"
        />
      ) : detailError ? (
        <PosErrorState
          description={toOperationalErrorMessage(
            detailError,
            "No fue posible cargar el ticket seleccionado.",
          )}
          title="Ticket no disponible"
        />
      ) : !selectedTicket ? (
        <div className="grid h-full place-items-center rounded-xl border border-dashed border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-4 py-6 text-center">
          <p className="max-w-xs text-sm leading-6 text-slate-600">
            Selecciona un ticket para ver su detalle y acciones disponibles.
          </p>
        </div>
      ) : (
        <div className="grid h-full min-h-0 grid-rows-[auto_auto_minmax(0,1fr)_auto] gap-3">
          <div className="grid gap-2">
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-base font-semibold text-slate-950">{selectedTicket.folio}</p>
              <PosStatusBadge status={getTicketStatusTone(selectedTicket.status)}>
                {getTicketStatusLabel(selectedTicket.status)}
              </PosStatusBadge>
              {getTicketReturnStatusLabel(selectedTicket.return_status) ? (
                <PosStatusBadge status={getTicketReturnStatusTone(selectedTicket.return_status)}>
                  {getTicketReturnStatusLabel(selectedTicket.return_status)}
                </PosStatusBadge>
              ) : null}
            </div>
            <p className="text-sm text-slate-600">
              {formatLocalDateTime(selectedTicket.confirmed_at, selectedTicket.branch.timezone)}
            </p>
          </div>

          <div className="grid gap-1 rounded-xl border border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-3 py-2.5">
            <KeyValueRow label="Total" value={formatCurrency(selectedTicket.total_amount)} />
            {selectedTicket.change_amount !== "0.00" ? (
              <KeyValueRow label="Cambio" value={formatCurrency(selectedTicket.change_amount)} />
            ) : null}
            <KeyValueRow
              label="Metodo"
              title={getPaymentSummaryLabel(selectedTicket.payments)}
              value={getPaymentSummaryLabel(selectedTicket.payments)}
            />
            <KeyValueRow label="Cajero" title={selectedTicket.operator.full_name} value={selectedTicket.operator.full_name} />
            <KeyValueRow label="Sucursal" title={selectedTicket.branch.name} value={selectedTicket.branch.name} />
            <KeyValueRow label="Caja" title={selectedTicket.workstation.name} value={selectedTicket.workstation.name} />
            <KeyValueRow label="Estado" value={getTicketStatusLabel(selectedTicket.status)} />
          </div>

          <div className="min-h-0 overflow-hidden rounded-xl border border-[var(--pos-shell-border)] bg-white">
            <div className="grid grid-cols-[3.5rem_minmax(0,1fr)_4.75rem_5rem] gap-2 border-b border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-2.5 py-2 text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-500">
              <span className="text-right">Cant.</span>
              <span>Producto</span>
              <span className="text-right">P. unit.</span>
              <span className="text-right">Importe</span>
            </div>
            <ScrollPane className="max-h-[18rem] divide-y divide-[var(--pos-shell-border)]">
              {selectedTicket.lines.map((line) => (
                <div
                  className="grid grid-cols-[3.5rem_minmax(0,1fr)_4.75rem_5rem] items-center gap-2 px-2.5 py-2"
                  key={line.id}
                >
                  <span className="text-right text-sm font-semibold text-slate-700 [font-variant-numeric:tabular-nums]">
                    {formatQuantity(line.quantity)}
                  </span>
                  <span className="truncate text-sm font-medium text-slate-950" title={line.name}>
                    {line.name}
                  </span>
                  <span className="text-right text-sm text-slate-600 [font-variant-numeric:tabular-nums]">
                    {formatCurrency(line.unit_price)}
                  </span>
                  <span className="text-right text-sm font-semibold text-slate-950 [font-variant-numeric:tabular-nums]">
                    {formatCurrency(line.line_total_amount)}
                  </span>
                </div>
              ))}
            </ScrollPane>
          </div>

          <div className="grid gap-1.5">
            {selectedTicket.return_count > 0 ? (
              <PosInlineValidationMessage tone="info">
                Devoluciones registradas: {selectedTicket.return_count}. Monto devuelto{" "}
                {formatCurrency(selectedTicket.returned_amount)}.
              </PosInlineValidationMessage>
            ) : null}
            {!selectedTicket.has_returnable_quantity ? (
              <PosInlineValidationMessage tone="info">
                Este ticket no tiene productos disponibles para devolucion.
              </PosInlineValidationMessage>
            ) : null}
            {consoleState === "REPRINT_ERROR" ? (
              <PosInlineValidationMessage tone="error">
                No se pudo reimprimir. Intenta de nuevo.
              </PosInlineValidationMessage>
            ) : null}
            {!selectedTicket.can_reprint ? (
              <PosInlineValidationMessage tone="warning">
                La reimpresion no esta disponible para este ticket.
              </PosInlineValidationMessage>
            ) : null}
          </div>
        </div>
      )}
    </PosRecordDetailPanel>
  );
}

export function TicketsScreen() {
  const accessToken = usePosAuthStore((state) => state.accessToken);
  const navigate = useNavigate();
  const showError = useStatusMessageStore((state) => state.showError);
  const showSuccess = useStatusMessageStore((state) => state.showSuccess);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const ticketsBootstrapQuery = useTicketsBootstrapQuery();
  const currentCashSessionQuery = useCurrentCashSessionQuery();
  const [selectedScope, setSelectedScope] = useState("CURRENT_SHIFT");
  const [searchText, setSearchText] = useState("");
  const [pendingScannerFolio, setPendingScannerFolio] = useState<string | null>(null);
  const [selectedTicketId, setSelectedTicketId] = useState<string | null>(null);
  const [preferredTicketId, setPreferredTicketId] = useState<string | null>(null);
  const [reprintFeedback, setReprintFeedback] = useState<ReprintFeedbackState>({
    kind: "idle",
    ticketId: null,
  });
  const routeTicketId = useRouterState({
    select: (state) => {
      const rawTicketId = (state.location.search as Record<string, unknown> | undefined)?.ticketId;
      return typeof rawTicketId === "string" && rawTicketId.length > 0 ? rawTicketId : null;
    },
  });
  const debouncedSearchText = useDebouncedValue(searchText, 220);
  const ticketsListQuery = useTicketsListQuery(selectedScope, debouncedSearchText);
  const ticketDetailQuery = useTicketDetailQuery(selectedTicketId);

  useEffect(() => {
    if (!ticketsBootstrapQuery.data) {
      return;
    }

    setSelectedScope(ticketsBootstrapQuery.data.default_scope);
    requestAnimationFrame(() => {
      searchInputRef.current?.focus();
    });
  }, [ticketsBootstrapQuery.data]);

  useEffect(() => {
    if (!routeTicketId) {
      return;
    }

    setPreferredTicketId(routeTicketId);
  }, [routeTicketId]);

  useEffect(() => {
    if (!preferredTicketId) {
      return;
    }

    setSelectedTicketId(preferredTicketId);
  }, [preferredTicketId]);

  useEffect(() => {
    if (!preferredTicketId || selectedTicketId !== preferredTicketId) {
      return;
    }

    setPreferredTicketId(null);
  }, [preferredTicketId, selectedTicketId]);

  useEffect(() => {
    const tickets = ticketsListQuery.data?.tickets ?? [];

    if (preferredTicketId) {
      if (selectedTicketId !== preferredTicketId) {
        setSelectedTicketId(preferredTicketId);
      }
      return;
    }

    if (selectedTicketId === null) {
      return;
    }

    if (tickets.some((ticket) => ticket.id === selectedTicketId)) {
      return;
    }

    setSelectedTicketId(null);
  }, [preferredTicketId, selectedTicketId, ticketsListQuery.data]);

  useEffect(() => {
    if (pendingScannerFolio === null) {
      return;
    }

    const tickets = ticketsListQuery.data?.tickets ?? [];
    const exactMatch = tickets.find((ticket) => matchesScannerValue(ticket.folio, pendingScannerFolio));

    if (exactMatch) {
      setSelectedTicketId(exactMatch.id);
      setPendingScannerFolio(null);
      return;
    }

    if (tickets.length === 1) {
      setSelectedTicketId(tickets[0]!.id);
      setPendingScannerFolio(null);
    }
  }, [pendingScannerFolio, ticketsListQuery.data]);

  useEffect(() => {
    setReprintFeedback({ kind: "idle", ticketId: null });
  }, [selectedTicketId]);

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key !== "Escape" || isEditableTarget(event.target)) {
        return;
      }

      if (searchText.trim().length > 0) {
        event.preventDefault();
        setSearchText("");
        return;
      }

      if (selectedTicketId !== null) {
        event.preventDefault();
        setSelectedTicketId(null);
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [searchText, selectedTicketId]);

  const reprintMutation = useMutation({
    mutationFn: async (ticketId: string) => {
      const payload: TicketReprintRequest = {
        workstation_code: appEnv.VITE_POS_WORKSTATION_CODE,
      };

      return reprintTicket({
        accessToken: accessToken!,
        payload,
        requestId: createRequestId("ticket-reprint"),
        ticketId,
      });
    },
  });

  const selectedTicket = ticketDetailQuery.data ?? null;
  const scopeLabel = getScopeContextLabel(selectedScope);
  const consoleState = getTicketConsoleState({
    hasResults: (ticketsListQuery.data?.tickets.length ?? 0) > 0,
    isLoadingResults: ticketsListQuery.isPending,
    isReprintPending: reprintMutation.isPending,
    reprintFeedback,
    selectedTicket,
  });

  const handleReprintTicket = useCallback((ticketId: string) => {
    setSelectedTicketId(ticketId);

    const printWindow = openBrowserPrintWindow();
    if (!printWindow) {
      setReprintFeedback({ kind: "error", ticketId });
      showError(
        "El navegador bloqueo la ventana de impresion. Permite ventanas emergentes e intenta de nuevo.",
      );
      return;
    }

    reprintMutation
      .mutateAsync(ticketId)
      .then((ticketDetail) => {
        writeTicketToPrintWindow(printWindow, ticketDetail);
        setReprintFeedback({ kind: "success", ticketId: ticketDetail.id });
        showSuccess("Reimpresion enviada.");
      })
      .catch((error) => {
        printWindow.close();
        setReprintFeedback({ kind: "error", ticketId });
        showError(toOperationalErrorMessage(error, "No se pudo reimprimir. Intenta de nuevo."));
      });
  }, [reprintMutation, showError, showSuccess]);

  const handleStartReturn = useCallback((saleId: string) => {
    void navigate({
      search: { saleId } as never,
      to: "/devoluciones",
    });
  }, [navigate]);

  const summaryPanel = useMemo(
    () => (
      <TicketSummaryPanel
        consoleState={consoleState}
        detailError={ticketDetailQuery.error}
        isDetailPending={selectedTicketId !== null && ticketDetailQuery.isPending}
        isReprintPending={reprintMutation.isPending}
        onReprint={handleReprintTicket}
        onStartReturn={handleStartReturn}
        selectedTicket={selectedTicket}
      />
    ),
    [
      consoleState,
      reprintMutation.isPending,
      selectedTicket,
      selectedTicketId,
      ticketDetailQuery.error,
      ticketDetailQuery.isPending,
      handleReprintTicket,
      handleStartReturn,
    ],
  );
  useAppShellRightPanel(summaryPanel);

  const isContextPending = ticketsBootstrapQuery.isPending || currentCashSessionQuery.isPending;

  if (isContextPending) {
    return (
      <OperationalStatus
        description="Consultando la caja activa y el alcance inicial de tickets."
        title="Cargando tickets"
      />
    );
  }

  if (ticketsBootstrapQuery.error) {
    return (
      <OperationalStatus
        action={<PosButton onClick={() => ticketsBootstrapQuery.refetch()}>Reintentar</PosButton>}
        description={toOperationalErrorMessage(
          ticketsBootstrapQuery.error,
          "Confirma la configuracion de la estacion y el contexto operativo.",
        )}
        title="No fue posible cargar Tickets"
      />
    );
  }

  if (currentCashSessionQuery.error) {
    return (
      <OperationalStatus
        action={<PosButton onClick={() => currentCashSessionQuery.refetch()}>Reintentar</PosButton>}
        description={toOperationalErrorMessage(
          currentCashSessionQuery.error,
          "Confirma la conexion con la API y el estado actual de la caja.",
        )}
        title="No fue posible consultar la caja"
      />
    );
  }

  if (!currentCashSessionQuery.data) {
    return <Navigate to="/cash-session/open" />;
  }

  if (currentCashSessionQuery.data.user_id !== ticketsBootstrapQuery.data.user.id) {
    return (
      <OperationalStatus
        description="La caja abierta de esta estacion pertenece a otro cajero. Inicia sesion con el operador correcto o espera el relevo."
        title="La caja activa no coincide con este cajero"
      />
    );
  }

  const availableScopes: TicketScopeView[] = ticketsBootstrapQuery.data.available_scopes;
  const tickets = ticketsListQuery.data?.tickets ?? [];
  const ticketCountLabel = formatTicketCountLabel(tickets.length);
  const ticketColumns: PosRecordColumn<TicketListItemView>[] = [
    {
      header: "Ticket",
      key: "folio",
      renderCell: (ticket) => (
        <span className="font-semibold text-slate-950">{ticket.folio}</span>
      ),
      width: "18%",
    },
    {
      header: "Fecha/hora",
      key: "date",
      renderCell: (ticket) =>
        formatCompactLocalDateTime(ticket.confirmed_at, ticketsBootstrapQuery.data.branch.timezone),
      width: "18%",
    },
    {
      header: "Cajero",
      key: "operator",
      renderCell: (ticket) => (
        <span className="block truncate" title={ticket.operator_full_name}>
          {ticket.operator_full_name}
        </span>
      ),
      width: "22%",
    },
    {
      align: "right",
      header: "Total",
      key: "total",
      renderCell: (ticket) => formatCurrency(ticket.total_amount),
      width: "12%",
    },
    {
      header: "Metodo de pago",
      key: "payment",
      renderCell: (ticket) => (
        <span className="block truncate" title={getPaymentSummaryLabel(ticket.payment_summary)}>
          {getPaymentSummaryLabel(ticket.payment_summary)}
        </span>
      ),
      width: "18%",
    },
    {
      align: "right",
      header: "Estado",
      key: "status",
      renderCell: (ticket) => (
        <div className="flex justify-end gap-1.5">
          <PosStatusBadge status="draft">Emitido</PosStatusBadge>
          {getTicketReturnStatusLabel(ticket.return_status) ? (
            <PosStatusBadge status={getTicketReturnStatusTone(ticket.return_status)}>
              {getTicketReturnStatusLabel(ticket.return_status)}
            </PosStatusBadge>
          ) : null}
        </div>
      ),
      width: "12%",
    },
  ];

  function handleTicketScanSubmit() {
    const scannedValue =
      parseTicketScannerValue(searchText) ?? normalizeScannerText(searchText);

    if (scannedValue.length === 0) {
      return;
    }

    setPendingScannerFolio(scannedValue);
    setSearchText(scannedValue);
  }

  return (
    <CentralWorkspaceSheet
      className="lg:h-full"
      contentClassName="min-h-0 overflow-hidden px-3 pb-3 pt-2"
      header={
        <CompactPageHeader
          secondaryChips={<ModuleStateChip>{scopeLabel}</ModuleStateChip>}
          stateChip={
            <ModuleStateChip tone={getTicketConsoleStateTone(consoleState)}>
              {getTicketConsoleStateLabel(consoleState)}
            </ModuleStateChip>
          }
          title="Tickets"
        />
      }
    >
      <PosHistoryView
        className="h-full"
        title="Tickets emitidos"
        toolbar={
          <div className="grid gap-2 xl:grid-cols-[minmax(18rem,28rem)_auto_minmax(0,1fr)_auto] xl:items-center">
            <SearchField
              ariaLabel="Buscar o escanear folio de ticket"
              className="min-w-0"
              inputClassName={`h-10 rounded-lg text-sm shadow-sm ${posInputClass}`}
              inputRef={searchInputRef}
              onChange={(value) => {
                setPendingScannerFolio(null);
                setSearchText(value);
              }}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === "NumpadEnter") {
                  event.preventDefault();
                  handleTicketScanSubmit();
                }
              }}
              placeholder="Buscar o escanear folio"
              value={searchText}
            />
            <PosButton
              disabled={searchText.trim().length === 0}
              onClick={handleTicketScanSubmit}
              type="button"
              variant="neutral"
            >
              Buscar
            </PosButton>
            <div className="flex min-w-0 flex-wrap items-center gap-2">
              {availableScopes.map((scope) => (
                <FilterButton
                  isActive={selectedScope === scope.code}
                  key={scope.code}
                  label={scope.label}
                  onClick={() => setSelectedScope(scope.code)}
                />
              ))}
            </div>
            <PosStatusBadge className="justify-self-start whitespace-nowrap xl:justify-self-end" status="draft">
              {ticketCountLabel}
            </PosStatusBadge>
          </div>
        }
      >
        {ticketsListQuery.error ? (
          <PosErrorState
            action={<PosButton onClick={() => ticketsListQuery.refetch()}>Reintentar</PosButton>}
            description={toOperationalErrorMessage(
              ticketsListQuery.error,
              "No fue posible consultar los tickets.",
            )}
            title="La lista no esta disponible"
          />
        ) : (
          <PosRecordTable
            columns={ticketColumns}
            emptyDescription={getEmptyListDescription(scopeLabel, searchText)}
            emptyTitle="No hay tickets"
            getKey={(ticket) => ticket.id}
            loading={ticketsListQuery.isPending}
            loadingTitle="Buscando tickets"
            onSelect={(ticket) => setSelectedTicketId(ticket.id)}
            records={tickets}
            selectedKey={selectedTicketId}
            tableAriaLabel="Tabla de tickets"
          />
        )}
      </PosHistoryView>
    </CentralWorkspaceSheet>
  );
}
