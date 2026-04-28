import { useMutation } from "@tanstack/react-query";
import { Navigate, useNavigate, useRouterState } from "@tanstack/react-router";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { useAppShellRightPanel } from "../../components/app-shell-right-panel";
import {
  CopyFolioAction,
  DocumentActionsMenu,
  PrintAction,
} from "../../components/document-actions";
import { OperationalStatus } from "../../components/operational-status";
import {
  PosEmptyState,
  PosErrorState,
  PosInlineValidationMessage,
  PosLoadingState,
} from "../../components/pos-feedback";
import { PosButton, PosPanel, PosStatusBadge } from "../../components/pos-foundations";
import { PosScannerInput } from "../../components/pos-scanner-input";
import {
  PosFilterBar,
  PosHistoryView,
  type PosRecordAction,
  PosRecordDetailPanel,
  PosRecordList,
} from "../../components/pos-records";
import {
  DownloadIcon,
  MoneyIcon,
  OperatorIcon,
  RotateCcwIcon,
  StationIcon,
  StoreIcon,
} from "../../components/pos-icons";
import {
  CentralWorkspaceSheet,
  FlowGuide,
  ModuleStateChip,
  CompactPageHeader,
  ResponsivePaneLayout,
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
import {
  getCustomerCommunicationActionState,
  getCustomerCommunicationReadinessNote,
} from "../../lib/customer-communication";
import { getDocumentActionAvailability } from "../../lib/document-actions";
import { usePosAuthStore } from "../auth/auth-store";
import { useCurrentCashSessionQuery } from "../cash-session-open/queries";
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
      return "Venta confirmada";
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

function TicketMetricTile({
  label,
  tone = "muted",
  value,
}: {
  label: string;
  tone?: "financial" | "muted";
  value: string;
}) {
  return (
    <div
      className="rounded-[var(--pos-radius-panel)] border border-[var(--pos-shell-border)] px-3 py-3"
      data-tone={tone}
    >
      <p className="pos-label-text">{label}</p>
      <p className="mt-1 text-lg font-semibold leading-tight text-slate-950 [font-variant-numeric:tabular-nums]">
        {value}
      </p>
    </div>
  );
}

export function TicketRecordCard({
  isSelected,
  ticket,
  timeZone,
}: {
  isSelected: boolean;
  ticket: TicketListItemView;
  timeZone: string;
}) {
  return (
    <div className="grid gap-2">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <p className="truncate text-sm font-semibold text-slate-950">{ticket.folio}</p>
            <PosStatusBadge status={isSelected ? "ready" : "draft"}>
              {isSelected ? "Activo" : "Emitido"}
            </PosStatusBadge>
            {getTicketReturnStatusLabel(ticket.return_status) ? (
              <PosStatusBadge status={getTicketReturnStatusTone(ticket.return_status)}>
                {getTicketReturnStatusLabel(ticket.return_status)}
              </PosStatusBadge>
            ) : null}
          </div>
          <p className="mt-1 text-sm font-semibold text-slate-900">
            {formatCompactLocalDateTime(ticket.confirmed_at, timeZone)}
          </p>
          <p className="mt-1 truncate text-xs text-slate-600">{ticket.operator_full_name}</p>
        </div>
        <div className="text-right">
          <p className="text-sm font-semibold text-slate-950">{formatCurrency(ticket.total_amount)}</p>
          <p
            className="mt-1 max-w-[10rem] truncate text-xs text-slate-500"
            title={getPaymentSummaryLabel(ticket.payment_summary)}
          >
            {getPaymentSummaryLabel(ticket.payment_summary)}
          </p>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-1.5 text-[12px] font-medium text-slate-500">
        <span className="rounded-full bg-[var(--pos-shell-muted)] px-2 py-1">
          {ticket.item_count} art.
        </span>
        <span className="rounded-full bg-[var(--pos-shell-muted)] px-2 py-1">
          {formatQuantity(ticket.total_quantity)} uds
        </span>
        <span className="rounded-full bg-[var(--pos-shell-muted)] px-2 py-1">
          Cambio {formatCurrency(ticket.change_amount)}
        </span>
        {ticket.return_count > 0 ? (
          <span className="rounded-full bg-[var(--pos-shell-muted)] px-2 py-1">
            Devuelto {formatCurrency(ticket.returned_amount)}
          </span>
        ) : null}
      </div>
    </div>
  );
}

function TicketLinesTable({ ticket }: { ticket: TicketDetailResponse }) {
  return (
    <PosPanel className="flex min-h-0 flex-col overflow-hidden px-0 py-0">
      <div className="flex items-center justify-between gap-3 border-b border-[var(--pos-shell-border)] px-3 py-2.5">
        <p className="text-sm font-semibold text-slate-950">Lineas del ticket</p>
        <PosStatusBadge status="draft">{ticket.lines.length}</PosStatusBadge>
      </div>
      <div className="grid shrink-0 grid-cols-[minmax(10rem,1fr)_5rem_6rem_6.5rem] gap-2 border-b border-[var(--pos-shell-border)] px-3 py-2 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
        <span>Articulo</span>
        <span className="text-right">Cant.</span>
        <span className="text-right">Precio</span>
        <span className="text-right">Importe</span>
      </div>
      <ScrollPane className="min-h-0 flex-1 divide-y divide-[var(--pos-shell-border)]">
        {ticket.lines.map((line) => (
          <div
            className="grid grid-cols-[minmax(10rem,1fr)_5rem_6rem_6.5rem] gap-2 px-3 py-2.5"
            key={line.id}
          >
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-slate-950" title={line.name}>
                {line.name}
              </p>
              <p className="mt-0.5 text-xs text-slate-500">Linea {line.sequence}</p>
            </div>
            <p className="text-right text-sm text-slate-600">{formatQuantity(line.quantity)}</p>
            <p className="text-right text-sm text-slate-600">{formatCurrency(line.unit_price)}</p>
            <p className="text-right text-sm font-semibold text-slate-950">
              {formatCurrency(line.line_total_amount)}
            </p>
          </div>
        ))}
      </ScrollPane>
    </PosPanel>
  );
}

function TicketPaymentsTable({ ticket }: { ticket: TicketDetailResponse }) {
  return (
    <PosPanel className="overflow-hidden px-0 py-0">
      <div className="flex items-center justify-between gap-3 border-b border-[var(--pos-shell-border)] px-3 py-2.5">
        <p className="text-sm font-semibold text-slate-950">Pagos registrados</p>
        <PosStatusBadge status="draft">{ticket.payments.length}</PosStatusBadge>
      </div>
      <div className="grid grid-cols-[minmax(6rem,1fr)_6rem_6rem_6rem_7rem] gap-2 border-b border-[var(--pos-shell-border)] px-3 py-2 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
        <span>Metodo</span>
        <span className="text-right">Aplicado</span>
        <span className="text-right">Recibido</span>
        <span className="text-right">Cambio</span>
        <span className="text-right">Hora</span>
      </div>
      <div className="divide-y divide-[var(--pos-shell-border)]">
        {ticket.payments.map((payment) => (
          <div
            className="grid grid-cols-[minmax(6rem,1fr)_6rem_6rem_6rem_7rem] gap-2 px-3 py-2.5"
            key={payment.id}
          >
            <p className="truncate text-sm font-medium text-slate-950">
              {getPaymentMethodLabel(payment.payment_method_code)}
            </p>
            <p className="text-right text-sm font-medium text-slate-950">
              {formatCurrency(payment.applied_amount)}
            </p>
            <p className="text-right text-sm text-slate-600">
              {formatCurrency(payment.tendered_amount)}
            </p>
            <p className="text-right text-sm text-slate-600">
              {formatCurrency(payment.change_amount)}
            </p>
            <p
              className="text-right text-sm text-slate-500"
              title={formatLocalDateTime(payment.received_at, ticket.branch.timezone)}
            >
              {formatCompactLocalDateTime(payment.received_at, ticket.branch.timezone)}
            </p>
          </div>
        ))}
      </div>
    </PosPanel>
  );
}

export function TicketDetailSurface({
  detailError,
  isLoadingDetail,
  selectedTicket,
}: {
  detailError: unknown;
  isLoadingDetail: boolean;
  selectedTicket: TicketDetailResponse | null;
}) {
  return (
    <PosRecordDetailPanel
      description="Consulta lineas, pagos y contexto operativo del ticket emitido."
      title="Detalle del ticket"
    >
      {isLoadingDetail ? (
        <PosLoadingState
          description="Consultando el ticket seleccionado."
          title="Buscando ticket"
        />
      ) : detailError ? (
        <PosErrorState
          description={toOperationalErrorMessage(
            detailError,
            "No fue posible cargar el detalle del ticket seleccionado.",
          )}
          title="Detalle no disponible"
        />
      ) : !selectedTicket ? (
        <PosEmptyState
          description="Selecciona un ticket para revisar su detalle completo sin salir de esta vista."
          title="Selecciona un ticket"
        />
      ) : (
        <div className="grid h-full min-h-0 gap-3">
          <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_auto]">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <p className="text-lg font-semibold text-slate-950">{selectedTicket.folio}</p>
                <PosStatusBadge status={getTicketStatusTone(selectedTicket.status)}>
                  {getTicketStatusLabel(selectedTicket.status)}
                </PosStatusBadge>
                {getTicketReturnStatusLabel(selectedTicket.return_status) ? (
                  <PosStatusBadge status={getTicketReturnStatusTone(selectedTicket.return_status)}>
                    {getTicketReturnStatusLabel(selectedTicket.return_status)}
                  </PosStatusBadge>
                ) : null}
              </div>
              <p className="mt-1 text-sm text-slate-600">
                {formatLocalDateTime(selectedTicket.confirmed_at, selectedTicket.branch.timezone)}
              </p>
            </div>
            <PosStatusBadge status="draft">Solo lectura</PosStatusBadge>
          </div>

          <div className="grid gap-2 md:grid-cols-4">
            <TicketMetricTile label="Total" tone="financial" value={formatCurrency(selectedTicket.total_amount)} />
            <TicketMetricTile label="Cambio" value={formatCurrency(selectedTicket.change_amount)} />
            <TicketMetricTile label="Articulos" value={String(selectedTicket.item_count)} />
            <TicketMetricTile
              label="Unidades"
              value={formatQuantity(selectedTicket.total_quantity)}
            />
          </div>

          {selectedTicket.return_count > 0 ? (
            <div className="grid gap-2 md:grid-cols-2">
              <TicketMetricTile
                label="Devoluciones"
                value={String(selectedTicket.return_count)}
              />
              <TicketMetricTile
                label="Monto devuelto"
                tone="financial"
                value={formatCurrency(selectedTicket.returned_amount)}
              />
            </div>
          ) : null}

          <div className="grid gap-2 md:grid-cols-4">
            <PosPanel className="px-3 py-3">
              <div className="flex items-start gap-2">
                <OperatorIcon className="mt-0.5 h-4 w-4 text-slate-500" />
                <div className="min-w-0">
                  <p className="pos-label-text">Cajero</p>
                  <p className="mt-1 truncate text-sm font-semibold text-slate-950" title={selectedTicket.operator.full_name}>
                    {selectedTicket.operator.full_name}
                  </p>
                </div>
              </div>
            </PosPanel>
            <PosPanel className="px-3 py-3">
              <div className="flex items-start gap-2">
                <StoreIcon className="mt-0.5 h-4 w-4 text-slate-500" />
                <div className="min-w-0">
                  <p className="pos-label-text">Sucursal</p>
                  <p className="mt-1 truncate text-sm font-semibold text-slate-950" title={selectedTicket.branch.name}>
                    {selectedTicket.branch.name}
                  </p>
                </div>
              </div>
            </PosPanel>
            <PosPanel className="px-3 py-3">
              <div className="flex items-start gap-2">
                <StationIcon className="mt-0.5 h-4 w-4 text-slate-500" />
                <div className="min-w-0">
                  <p className="pos-label-text">Caja</p>
                  <p className="mt-1 truncate text-sm font-semibold text-slate-950" title={selectedTicket.workstation.name}>
                    {selectedTicket.workstation.name}
                  </p>
                </div>
              </div>
            </PosPanel>
            <PosPanel className="px-3 py-3">
              <div className="flex items-start gap-2">
                <MoneyIcon className="mt-0.5 h-4 w-4 text-slate-500" />
                <div className="min-w-0">
                  <p className="pos-label-text">Metodo</p>
                  <p
                    className="mt-1 truncate text-sm font-semibold text-slate-950"
                    title={getPaymentSummaryLabel(selectedTicket.payments)}
                  >
                    {getPaymentSummaryLabel(selectedTicket.payments)}
                  </p>
                </div>
              </div>
            </PosPanel>
          </div>

          <div className="grid min-h-0 gap-3 xl:grid-cols-[minmax(0,1fr)_minmax(20rem,24rem)]">
            <TicketLinesTable ticket={selectedTicket} />
            <TicketPaymentsTable ticket={selectedTicket} />
          </div>
        </div>
      )}
    </PosRecordDetailPanel>
  );
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
  const sendTicketByEmailAction = getCustomerCommunicationActionState({
    channel: "email",
    intent: "saleTicket",
  });
  const sendTicketBySmsAction = getCustomerCommunicationActionState({
    channel: "sms",
    intent: "saleTicket",
  });
  const communicationNote = getCustomerCommunicationReadinessNote("saleTicket");

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
            <PosButton
              disabled={!selectedTicket.has_returnable_quantity}
              leadingIcon={<RotateCcwIcon className="h-4 w-4" />}
              onClick={() => onStartReturn(selectedTicket.id)}
              variant="secondary"
            >
              Iniciar devolucion
            </PosButton>
            <div className="flex flex-wrap items-center gap-2">
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
              <CopyFolioAction referenceValue={selectedTicket.folio} />
              <DocumentActionsMenu
                actions={[
                  {
                    disabled: sendTicketByEmailAction.disabled,
                    disabledReason: sendTicketByEmailAction.disabledReason,
                    key: `ticket-email-${selectedTicket.id}`,
                    label: sendTicketByEmailAction.label,
                    onSelect: () => undefined,
                  },
                  {
                    disabled: sendTicketBySmsAction.disabled,
                    disabledReason: sendTicketBySmsAction.disabledReason,
                    key: `ticket-sms-${selectedTicket.id}`,
                    label: sendTicketBySmsAction.label,
                    onSelect: () => undefined,
                  },
                  {
                    disabled: !documentActionAvailability.exportPdf.isAvailable,
                    disabledReason: documentActionAvailability.exportPdf.unavailableReason,
                    key: `ticket-export-${selectedTicket.id}`,
                    label: documentActionAvailability.exportPdf.label,
                    leadingIcon: <DownloadIcon className="h-4 w-4" />,
                    onSelect: () => undefined,
                  },
                ]}
              />
            </div>
          </div>
        ) : undefined
      }
    >
      {isDetailPending ? (
        <PosLoadingState
          description="Cargando el ticket seleccionado para operar sobre el."
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
        <PosEmptyState
          description="Selecciona un ticket para reimprimirlo, copiar su folio o iniciar una devolucion."
          title="Selecciona un ticket"
        />
      ) : (
        <div className="grid gap-3">
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

          <div className="grid gap-2">
            <TicketMetricTile label="Total" tone="financial" value={formatCurrency(selectedTicket.total_amount)} />
            <TicketMetricTile label="Cambio" value={formatCurrency(selectedTicket.change_amount)} />
            {selectedTicket.return_count > 0 ? (
              <TicketMetricTile
                label="Monto devuelto"
                tone="financial"
                value={formatCurrency(selectedTicket.returned_amount)}
              />
            ) : null}
          </div>

          <PosPanel className="px-3 py-3">
            <div className="grid gap-2 text-sm">
              <div className="flex items-start gap-2">
                <OperatorIcon className="mt-0.5 h-4 w-4 text-slate-500" />
                <div className="min-w-0">
                  <p className="pos-label-text">Cajero</p>
                  <p className="mt-1 truncate font-semibold text-slate-950">
                    {selectedTicket.operator.full_name}
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-2">
                <StoreIcon className="mt-0.5 h-4 w-4 text-slate-500" />
                <div className="min-w-0">
                  <p className="pos-label-text">Sucursal</p>
                  <p className="mt-1 truncate font-semibold text-slate-950">
                    {selectedTicket.branch.name}
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-2">
                <StationIcon className="mt-0.5 h-4 w-4 text-slate-500" />
                <div className="min-w-0">
                  <p className="pos-label-text">Caja</p>
                  <p className="mt-1 truncate font-semibold text-slate-950">
                    {selectedTicket.workstation.name}
                  </p>
                </div>
              </div>
            </div>
          </PosPanel>

          <PosInlineValidationMessage tone="info">
            Usa Devoluciones para ventas confirmadas.
          </PosInlineValidationMessage>

          <PosInlineValidationMessage tone="info">
            {communicationNote}
          </PosInlineValidationMessage>

          {consoleState === "REPRINT_SUCCESS" ? (
            <PosInlineValidationMessage tone="success">
              Reimpresion enviada.
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
  const scannerInputRef = useRef<HTMLInputElement>(null);
  const ticketsBootstrapQuery = useTicketsBootstrapQuery();
  const currentCashSessionQuery = useCurrentCashSessionQuery();
  const [selectedScope, setSelectedScope] = useState("CURRENT_SHIFT");
  const [searchText, setSearchText] = useState("");
  const [scannerText, setScannerText] = useState("");
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

    if (tickets.length === 0) {
      if (preferredTicketId === null) {
        setSelectedTicketId(null);
      }
      return;
    }

    if (preferredTicketId) {
      if (selectedTicketId !== preferredTicketId) {
        setSelectedTicketId(preferredTicketId);
      }
      return;
    }

    if (selectedTicketId && tickets.some((ticket) => ticket.id === selectedTicketId)) {
      return;
    }

    setSelectedTicketId(tickets[0]?.id ?? null);
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

  const handleCopyFolio = useCallback((folio: string) => {
    if (!navigator.clipboard) {
      showError("No se pudo copiar el folio en este navegador.");
      return;
    }

    void navigator.clipboard
      .writeText(folio)
      .then(() => showSuccess("Folio copiado."))
      .catch(() => showError("No se pudo copiar el folio."));
  }, [showError, showSuccess]);

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

  const ticketRowActions = useMemo(
    () => (ticket: TicketListItemView): PosRecordAction[] => [
      {
        key: `copy-${ticket.id}`,
        label: "Copiar folio",
        onSelect: () => handleCopyFolio(ticket.folio),
      },
      {
        key: `reprint-${ticket.id}`,
        label: "Reimprimir",
        onSelect: () => handleReprintTicket(ticket.id),
      },
      {
        key: `return-${ticket.id}`,
        label: "Iniciar devolucion",
        disabled: !ticket.has_returnable_quantity,
        onSelect: () => handleStartReturn(ticket.id),
      },
    ],
    [handleCopyFolio, handleReprintTicket, handleStartReturn],
  );

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

  function handleTicketScanSubmit() {
    const scannedValue =
      parseTicketScannerValue(scannerText) ?? normalizeScannerText(scannerText);

    if (scannedValue.length === 0) {
      return;
    }

    setScannerText("");
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
        >
          <FlowGuide
            activeStepKey={selectedTicket ? "detail" : "list"}
            steps={[
              { key: "list", label: "Consulta", state: selectedTicket ? "completed" : "current" },
              { key: "detail", label: "Detalle", state: selectedTicket ? "current" : "upcoming" },
              { key: "action", label: "Accion", state: selectedTicket ? "upcoming" : "blocked" },
            ]}
            variant="compact"
          />
        </CompactPageHeader>
      }
    >
      <ResponsivePaneLayout
        className="h-full gap-2.5"
        compactMode="stack"
        detail={
          <TicketDetailSurface
            detailError={ticketDetailQuery.error}
            isLoadingDetail={selectedTicketId !== null && ticketDetailQuery.isPending}
            selectedTicket={selectedTicket}
          />
        }
        detailClassName="min-h-0"
        list={
          <PosHistoryView
            className="h-full"
            description="Busca por folio, revisa el detalle y ejecuta acciones operativas sin salir del historial."
            title="Tickets emitidos"
            toolbar={
              <div className="grid gap-3">
                <PosScannerInput
                  ariaLabel="Escanear folio de ticket"
                  inputRef={scannerInputRef}
                  modeLabel="Escaneo de ticket"
                  onChange={setScannerText}
                  onSubmit={handleTicketScanSubmit}
                  placeholder="Escanear folio de ticket"
                  submitLabel="Buscar folio"
                  value={scannerText}
                />
                <PosFilterBar
                  chipFilters={availableScopes.map((scope) => ({
                    isActive: selectedScope === scope.code,
                    key: scope.code,
                    label: scope.label,
                    onSelect: () => setSelectedScope(scope.code),
                  }))}
                  countLabel={<PosStatusBadge status="draft">{tickets.length} tickets</PosStatusBadge>}
                  searchInput={{
                    ariaLabel: "Buscar ticket por folio",
                    hotkeyDescription: "Enfoca la busqueda de tickets.",
                    inputRef: searchInputRef,
                    onChange: (value) => {
                      setPendingScannerFolio(null);
                      setSearchText(value);
                    },
                    placeholder: "Buscar por folio",
                    value: searchText,
                  }}
                />
              </div>
            }
          >
            {ticketsListQuery.error ? (
              <PosErrorState
                action={<PosButton onClick={() => ticketsListQuery.refetch()}>Reintentar</PosButton>}
                description={toOperationalErrorMessage(
                  ticketsListQuery.error,
                  "No fue posible consultar los tickets del alcance actual.",
                )}
                title="La lista no esta disponible"
              />
            ) : (
              <PosRecordList
                emptyDescription={getEmptyListDescription(scopeLabel, searchText)}
                emptyTitle="No hay tickets para mostrar"
                getKey={(ticket) => ticket.id}
                getRowActions={ticketRowActions}
                loading={ticketsListQuery.isPending}
                loadingTitle="Buscando tickets"
                onSelect={(ticket) => setSelectedTicketId(ticket.id)}
                records={tickets}
                renderContent={(ticket, state) => (
                  <TicketRecordCard
                    isSelected={state.isSelected}
                    ticket={ticket}
                    timeZone={ticketsBootstrapQuery.data.branch.timezone}
                  />
                )}
                selectedKey={selectedTicketId}
              />
            )}
          </PosHistoryView>
        }
        listClassName="min-h-0"
      />
    </CentralWorkspaceSheet>
  );
}
