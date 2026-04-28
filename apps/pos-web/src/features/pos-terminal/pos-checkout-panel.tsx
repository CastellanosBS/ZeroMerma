import { useMutation } from "@tanstack/react-query";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
  type Ref,
} from "react";

import { PosInlineValidationMessage } from "../../components/pos-feedback";
import {
  PosPaymentInputCard,
  PosPaymentMethodButton,
  PosPaymentValueCard,
} from "../../components/pos-payment-controls";
import {
  CardIcon,
  CheckCircleIcon,
  ClockIcon,
  MoneyIcon,
  MinusIcon,
  PlusIcon,
  PrinterIcon,
  ReceiptIcon,
  SplitIcon,
  TrashIcon,
} from "../../components/pos-icons";
import { Button } from "../../components/ui/button";
import type { PosBootstrapResponse } from "../../lib/api-contracts";
import { openBrowserPrintWindow } from "../../lib/browser-print";
import { formatCurrency } from "../../lib/formatters";
import { isEditableTarget } from "../../lib/keyboard-shortcuts";
import { cn } from "../../lib/utils";
import { usePosAuthStore } from "../auth/auth-store";
import { useStatusMessageStore } from "../status-messages/store";
import { getTicketDetail } from "../tickets/tickets-api";
import { writeTicketToPrintWindow } from "../tickets/print";
import {
  buildConfirmSaleRequest,
  CASH_PAYMENT_METHOD_CODE,
  CARD_PAYMENT_METHOD_CODE,
  CONTROL_STATE_PAYMENT_CAPTURE,
  formatMoneyFromCents,
  formatQuantityFromMilliUnits,
  getCartTotalCents,
  getLineTotalCents,
  getPosCheckoutPaymentControlRows,
  MIXED_PAYMENT_METHOD_CODE,
  parseMoneyToCents,
  parseQuantityToMilliUnits,
  sanitizeQuantityInput,
  type PosPaymentMethodCode,
  type PosSplitPaymentMethodCode,
} from "./model";
import {
  SALE_FLOW_ACTIVE_SELECTION,
  SALE_FLOW_AMOUNT_CONFIRMED,
  SALE_FLOW_PAYMENT_AMOUNT_CAPTURE,
  SALE_FLOW_PROCESSING,
  SALE_FLOW_RECOVERABLE_ERROR,
  SALE_FLOW_QUANTITY_CAPTURE,
  useSaleFlowController,
} from "./sale-flow-controller";
import { confirmPosSale } from "./pos-terminal-api";
import { usePosTerminalStore } from "./store";
import {
  posInputClass,
  posOutlineButtonClass,
  posPrimaryButtonClass,
} from "../pos-theme/theme";

function isSubmitKey(key: string): boolean {
  return key === "Enter" || key === "NumpadEnter";
}

function getPaymentMethodFromShortcut(key: string): PosPaymentMethodCode | null {
  if (key === "/") {
    return CASH_PAYMENT_METHOD_CODE;
  }

  if (key === "*") {
    return CARD_PAYMENT_METHOD_CODE;
  }

  if (key === "-") {
    return MIXED_PAYMENT_METHOD_CODE;
  }

  return null;
}

function formatDisplayAmount(valueCents: number): string {
  return formatCurrency(formatMoneyFromCents(valueCents));
}

function getPaymentMethodShortcutLabel(code: PosPaymentMethodCode): string {
  if (code === CASH_PAYMENT_METHOD_CODE) {
    return "/";
  }

  if (code === CARD_PAYMENT_METHOD_CODE) {
    return "*";
  }

  return "-";
}

function TicketLineRow({
  amount,
  editingQuantityText,
  inputRef,
  isEditing,
  isSelected,
  name,
  onDecrement,
  onBeginEdit,
  onCancelEdit,
  onCommitEdit,
  onEditingQuantityChange,
  onIncrement,
  onRemove,
  onSelect,
  quantity,
}: {
  amount: string;
  editingQuantityText: string;
  inputRef: Ref<HTMLInputElement>;
  isEditing: boolean;
  isSelected: boolean;
  name: string;
  onDecrement: () => void;
  onBeginEdit: () => void;
  onCancelEdit: () => void;
  onCommitEdit: () => void;
  onEditingQuantityChange: (value: string) => void;
  onIncrement: () => void;
  onRemove: () => void;
  onSelect: () => void;
  quantity: string;
}) {
  return (
    <div
      aria-selected={isSelected}
      className={cn(
        "grid grid-cols-[minmax(0,1fr)_auto_auto_auto] items-center gap-1.5 border-t border-[var(--pos-shell-border)] px-2 py-1.5 first:border-t-0",
        isSelected && "bg-[var(--pos-primary-soft)]/70",
      )}
      onClick={onSelect}
      onFocusCapture={onSelect}
      role="row"
      tabIndex={0}
    >
      <p className="truncate text-[13px] font-medium leading-5 text-slate-950">{name}</p>

      <div className="flex items-center gap-0 rounded-md border border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-0.5 py-0.5">
        <button
          aria-label={`Restar cantidad de ${name}`}
          className="flex h-7 w-7 items-center justify-center rounded-sm text-slate-900 transition hover:bg-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--pos-ring)]"
          onClick={(event) => {
            event.stopPropagation();
            onDecrement();
          }}
          type="button"
        >
          <MinusIcon className="h-3 w-3" />
        </button>
        <div className="w-[3.1rem]">
          {isEditing ? (
            <input
              aria-label={`Cantidad de ${name}`}
              className={cn(
                "h-7 w-full rounded-sm px-1 text-center text-[13px] font-semibold text-slate-950 [font-variant-numeric:tabular-nums]",
                posInputClass,
              )}
              inputMode="decimal"
              onBlur={onCommitEdit}
              onChange={(event) => onEditingQuantityChange(event.target.value)}
              onClick={(event) => event.stopPropagation()}
              onKeyDown={(event) => {
                event.stopPropagation();
                if (event.key === "Enter" || event.key === "NumpadEnter") {
                  event.preventDefault();
                  onCommitEdit();
                  return;
                }

                if (event.key === "Escape") {
                  event.preventDefault();
                  onCancelEdit();
                }
              }}
              ref={inputRef}
              value={editingQuantityText}
            />
          ) : (
            <button
              aria-label={`Editar cantidad de ${name}`}
              className="h-7 w-full rounded-sm px-1 text-center text-[13px] font-semibold text-slate-950 transition hover:bg-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--pos-ring)] [font-variant-numeric:tabular-nums]"
              onClick={(event) => {
                event.stopPropagation();
                onBeginEdit();
              }}
              type="button"
            >
              {quantity}
            </button>
          )}
        </div>
        <button
          aria-label={`Sumar cantidad de ${name}`}
          className="flex h-7 w-7 items-center justify-center rounded-sm text-slate-900 transition hover:bg-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--pos-ring)]"
          onClick={(event) => {
            event.stopPropagation();
            onIncrement();
          }}
          type="button"
        >
          <PlusIcon className="h-3 w-3" />
        </button>
      </div>

      <div className="min-w-[3.8rem] overflow-hidden text-ellipsis whitespace-nowrap text-right text-[13px] font-semibold text-slate-950 [font-variant-numeric:tabular-nums]">
        {amount}
      </div>

      <button
        aria-label={`Eliminar ${name}`}
        className="flex h-7 w-7 items-center justify-center rounded-md text-[var(--ui-color-danger)] transition hover:bg-[var(--ui-color-danger-soft)] hover:text-[var(--ui-color-danger)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--pos-ring)]"
        onClick={(event) => {
          event.stopPropagation();
          onRemove();
        }}
        type="button"
      >
        <TrashIcon className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}

function PaymentMethodButton({
  code,
  icon,
  isActive,
  isDisabled = false,
  label,
  onClick,
}: {
  code: PosPaymentMethodCode;
  icon: ReactNode;
  isActive: boolean;
  isDisabled?: boolean;
  label: string;
  onClick: (paymentMethodCode: PosPaymentMethodCode) => void;
}) {
  return (
    <PosPaymentMethodButton
      disabled={isDisabled}
      icon={icon}
      isActive={isActive}
      label={label}
      onClick={() => onClick(code)}
      shortcutLabel={getPaymentMethodShortcutLabel(code)}
    />
  );
}

function CheckoutMetricTile({
  icon,
  label,
  tone = "default",
  value,
}: {
  icon: ReactNode;
  label: string;
  tone?: "default" | "financial" | "input" | "positive" | "warning";
  value: string;
}) {
  return (
    <PosPaymentValueCard
      icon={icon}
      label={label}
      tone={
        tone === "financial"
          ? "fixed"
          : tone === "input"
            ? "input"
            : tone === "positive"
              ? "success"
              : tone === "warning"
                ? "pending"
                : "default"
      }
      value={value}
    />
  );
}

function TicketRequestToggle({
  checked,
  disabled = false,
  onToggle,
}: {
  checked: boolean;
  disabled?: boolean;
  onToggle: () => void;
}) {
  return (
    <div className="flex items-center justify-between gap-3 px-1 py-0.5">
      <div className="flex min-w-0 items-center gap-2">
        <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[var(--pos-shell-muted)] text-[var(--pos-primary)]">
          <PrinterIcon className="h-3 w-3" />
        </span>
        <p className="pos-label-text text-slate-800">Ticket</p>
      </div>

      <button
        aria-checked={checked}
        aria-label="Solicitar ticket"
        className={cn(
          "pos-shortcut-corner relative inline-flex h-5 w-10 shrink-0 items-center rounded-full border transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--pos-ring)] focus-visible:ring-offset-1",
          checked
            ? "border-[var(--pos-primary)] bg-[var(--pos-primary)]"
            : "border-[var(--pos-shell-border)] bg-slate-300",
          disabled ? "cursor-not-allowed opacity-50" : "cursor-pointer",
        )}
        data-shortcut="."
        data-shortcut-tone={checked ? "primary" : "default"}
        disabled={disabled}
        onClick={() => {
          if (disabled) {
            return;
          }
          onToggle();
        }}
        onKeyDown={(event) => {
          if (disabled) {
            return;
          }
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            onToggle();
          }
        }}
        role="switch"
        type="button"
      >
        <span
          aria-hidden="true"
          className={cn(
            "pointer-events-none inline-block h-4 w-4 rounded-full bg-white shadow-sm transition-transform duration-150",
            checked ? "translate-x-[18px]" : "translate-x-[2px]",
          )}
        />
      </button>
    </div>
  );
}

function MixedLegSummary({
  amount,
  label,
}: {
  amount: string;
  label: string;
}) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-lg border border-[var(--pos-shell-border)] bg-white px-3 py-2">
      <span className="text-sm font-medium text-slate-700">{label}</span>
      <span className="text-sm font-semibold text-slate-950 [font-variant-numeric:tabular-nums]">
        {amount}
      </span>
    </div>
  );
}


export function PosCheckoutPanel({
  bootstrap,
}: {
  bootstrap: PosBootstrapResponse;
}) {
  const accessToken = usePosAuthStore((state) => state.accessToken);
  const showSuccess = useStatusMessageStore((state) => state.showSuccess);
  const showWarning = useStatusMessageStore((state) => state.showWarning);
  const primaryAmountInputRef = useRef<HTMLInputElement>(null);
  const mixedLegAmountInputRef = useRef<HTMLInputElement>(null);
  const inlineQuantityInputRef = useRef<HTMLInputElement>(null);
  const actionButtonRef = useRef<HTMLButtonElement>(null);
  const [isClearCartConfirming, setIsClearCartConfirming] = useState(false);
  const [paymentInlineError, setPaymentInlineError] = useState<string | null>(null);
  const [editingLineKey, setEditingLineKey] = useState<string | null>(null);
  const [editingQuantityText, setEditingQuantityText] = useState("");
  const [ticketInlineError, setTicketInlineError] = useState<string | null>(null);
  const cartLines = usePosTerminalStore((state) => state.cartLines);
  const controlState = usePosTerminalStore((state) => state.controlState);
  const incrementLineQuantity = usePosTerminalStore((state) => state.incrementLineQuantity);
  const decrementLineQuantity = usePosTerminalStore((state) => state.decrementLineQuantity);
  const removeLine = usePosTerminalStore((state) => state.removeLine);
  const repeatLastLine = usePosTerminalStore((state) => state.repeatLastLine);
  const clearCart = usePosTerminalStore((state) => state.clearCart);
  const openPaymentCapture = usePosTerminalStore((state) => state.enterPaymentCapture);
  const goBack = usePosTerminalStore((state) => state.goBack);
  const setLineQuantity = usePosTerminalStore((state) => state.setLineQuantity);
  const totalAmountCents = getCartTotalCents(cartLines);
  const hasTicket = cartLines.length > 0;
  const saleFlow = useSaleFlowController({
    cartLineCount: cartLines.length,
    controlState,
    hasCompletedSale: false,
    totalAmountCents,
  });
  const paymentControlRows = useMemo(() => getPosCheckoutPaymentControlRows(), []);
  const paymentControls = useMemo(() => paymentControlRows.flat(), [paymentControlRows]);
  const confirmSaleMutation = useMutation({
    mutationFn: () =>
      confirmPosSale(
        accessToken!,
        buildConfirmSaleRequest(bootstrap.workstation.code, cartLines, saleFlow.buildPaymentDraft()),
      ),
  });

  const isPaymentMode =
    saleFlow.state.mode === SALE_FLOW_PAYMENT_AMOUNT_CAPTURE ||
    saleFlow.state.mode === SALE_FLOW_AMOUNT_CONFIRMED ||
    saleFlow.state.mode === SALE_FLOW_RECOVERABLE_ERROR ||
    saleFlow.state.mode === SALE_FLOW_PROCESSING;
  const recoverableRetryMode = saleFlow.state.recoverableError?.retryMode ?? null;
  const isRecoverableConfirmed =
    saleFlow.state.mode === SALE_FLOW_RECOVERABLE_ERROR &&
    recoverableRetryMode === SALE_FLOW_AMOUNT_CONFIRMED;
  const isEditablePaymentState =
    saleFlow.state.mode === SALE_FLOW_PAYMENT_AMOUNT_CAPTURE ||
    (saleFlow.state.mode === SALE_FLOW_RECOVERABLE_ERROR &&
      recoverableRetryMode === SALE_FLOW_PAYMENT_AMOUNT_CAPTURE);
  const canToggleTicketRequest =
    saleFlow.state.mode === SALE_FLOW_AMOUNT_CONFIRMED || isRecoverableConfirmed;
  const showCashReceivedInput =
    hasTicket && saleFlow.state.paymentMethodCode === CASH_PAYMENT_METHOD_CODE;
  const canEnterPayment =
    hasTicket &&
    controlState !== CONTROL_STATE_PAYMENT_CAPTURE &&
    saleFlow.state.mode !== SALE_FLOW_QUANTITY_CAPTURE &&
    saleFlow.state.mode !== SALE_FLOW_PROCESSING;
  const canEditSelectedLine =
    saleFlow.state.selectedTicketLineId !== null && controlState !== CONTROL_STATE_PAYMENT_CAPTURE;
  const totalAmountText = formatDisplayAmount(totalAmountCents);
  const paymentComputation = saleFlow.paymentComputation;
  const effectiveReceivedAmountText =
    saleFlow.state.paymentMethodCode === MIXED_PAYMENT_METHOD_CODE
      ? formatDisplayAmount(
          saleFlow.state.mode === SALE_FLOW_AMOUNT_CONFIRMED
            ? paymentComputation.capturedAmountCents
            : paymentComputation.previewCapturedAmountCents,
        )
      : formatDisplayAmount(paymentComputation.capturedAmountCents);
  const effectiveResultValueText =
    saleFlow.state.paymentMethodCode === CARD_PAYMENT_METHOD_CODE
      ? "Cubierto"
      : saleFlow.state.mode === SALE_FLOW_AMOUNT_CONFIRMED
        ? paymentComputation.changeAmountCents > 0
          ? formatDisplayAmount(paymentComputation.changeAmountCents)
          : "$0.00"
        : paymentComputation.previewRemainingAmountCents > 0
          ? formatDisplayAmount(paymentComputation.previewRemainingAmountCents)
          : paymentComputation.previewChangeAmountCents > 0
            ? formatDisplayAmount(paymentComputation.previewChangeAmountCents)
            : "$0.00";
  const effectiveResultTone =
    saleFlow.state.paymentMethodCode === CARD_PAYMENT_METHOD_CODE
      ? "positive"
      : saleFlow.state.mode === SALE_FLOW_AMOUNT_CONFIRMED
        ? "positive"
        : paymentComputation.previewRemainingAmountCents > 0
          ? "warning"
          : "positive";
  const effectiveResultLabel =
    saleFlow.state.paymentMethodCode === CARD_PAYMENT_METHOD_CODE
      ? "Estado"
      : saleFlow.state.mode === SALE_FLOW_AMOUNT_CONFIRMED
        ? "Cambio"
        : paymentComputation.previewRemainingAmountCents > 0
          ? "Falta"
          : paymentComputation.previewChangeAmountCents > 0
            ? "Cambio"
            : "Cambio";
  const helperText =
    saleFlow.state.mode === SALE_FLOW_AMOUNT_CONFIRMED || isRecoverableConfirmed
      ? null
      : isEditablePaymentState
        ? null
        : hasTicket
          ? null
          : "Agrega al menos un producto para habilitar el cobro.";
  const stateLabel =
    saleFlow.state.mode === SALE_FLOW_PROCESSING
      ? "Procesando..."
      : saleFlow.state.mode === SALE_FLOW_AMOUNT_CONFIRMED
        ? "Monto confirmado"
        : isPaymentMode
          ? "Cobro abierto"
          : hasTicket
            ? "Ticket activo"
            : "Ticket vacio";

  const beginInlineLineEdit = useCallback(
    (lineKey: string, quantityText: string) => {
      if (controlState === CONTROL_STATE_PAYMENT_CAPTURE) {
        return;
      }

      setTicketInlineError(null);
      saleFlow.setSelectedTicketLineId(lineKey);
      setEditingLineKey(lineKey);
      setEditingQuantityText(quantityText);
    },
    [controlState, saleFlow],
  );

  const cancelInlineLineEdit = useCallback(() => {
    setEditingLineKey(null);
    setEditingQuantityText("");
    setTicketInlineError(null);
  }, []);

  const commitInlineLineEdit = useCallback(() => {
    if (editingLineKey === null) {
      return;
    }

    const normalizedQuantityText = sanitizeQuantityInput(editingQuantityText);
    if ((parseQuantityToMilliUnits(normalizedQuantityText) ?? 0) <= 0) {
      setTicketInlineError("Captura una cantidad valida antes de guardar.");
      return;
    }

    try {
      setLineQuantity(editingLineKey, normalizedQuantityText);
      setEditingLineKey(null);
      setEditingQuantityText("");
      setTicketInlineError(null);
    } catch (error) {
      void error;
      setTicketInlineError("Captura una cantidad valida antes de guardar.");
    }
  }, [editingLineKey, editingQuantityText, setLineQuantity]);

  const focusPrimaryPaymentInput = useCallback(() => {
    const target =
      saleFlow.state.paymentMethodCode === MIXED_PAYMENT_METHOD_CODE
        ? mixedLegAmountInputRef.current
        : saleFlow.state.paymentMethodCode === CASH_PAYMENT_METHOD_CODE
          ? primaryAmountInputRef.current
          : null;
    if (!target) {
      return;
    }

    target.focus();
    target.select();
  }, [saleFlow.state.paymentMethodCode]);

  useEffect(() => {
    if (saleFlow.state.mode !== SALE_FLOW_PAYMENT_AMOUNT_CAPTURE) {
      return;
    }

    window.setTimeout(() => {
      focusPrimaryPaymentInput();
    }, 0);
  }, [focusPrimaryPaymentInput, saleFlow.state.mode]);

  useEffect(() => {
    if (
      saleFlow.state.mode !== SALE_FLOW_AMOUNT_CONFIRMED &&
      !isRecoverableConfirmed
    ) {
      return;
    }

    window.setTimeout(() => {
      actionButtonRef.current?.focus();
    }, 0);
  }, [isRecoverableConfirmed, saleFlow.state.mode]);

  useEffect(() => {
    setPaymentInlineError(null);
  }, [
    saleFlow.state.cashReceivedText,
    saleFlow.state.mixedCurrentLegAmountText,
    saleFlow.state.mixedCurrentLegMethodCode,
    saleFlow.state.paymentMethodCode,
  ]);

  useEffect(() => {
    if (editingLineKey === null) {
      return;
    }

    window.setTimeout(() => {
      inlineQuantityInputRef.current?.focus();
      inlineQuantityInputRef.current?.select();
    }, 0);
  }, [editingLineKey]);

  useEffect(() => {
    if (hasTicket) {
      return;
    }

    setIsClearCartConfirming(false);
    cancelInlineLineEdit();
  }, [cancelInlineLineEdit, hasTicket]);

  useEffect(() => {
    if (editingLineKey === null) {
      return;
    }

    if (controlState === CONTROL_STATE_PAYMENT_CAPTURE) {
      cancelInlineLineEdit();
      return;
    }

    const currentLine = cartLines.find((line) => line.key === editingLineKey);
    if (!currentLine) {
      cancelInlineLineEdit();
    }
  }, [cancelInlineLineEdit, cartLines, controlState, editingLineKey]);

  const printTicketForSale = useCallback(
    async (saleId: string, existingPrintWindow: Window | null) => {
      const ticket = await getTicketDetail({
        accessToken: accessToken!,
        ticketId: saleId,
        workstationCode: bootstrap.workstation.code,
      });
      const printWindow = existingPrintWindow ?? openBrowserPrintWindow();
      if (printWindow === null) {
        throw new Error("No se pudo abrir la ventana del ticket.");
      }

      writeTicketToPrintWindow(printWindow, ticket, {
        variant: "sale",
      });
      return ticket;
    },
    [accessToken, bootstrap.workstation.code],
  );

  const beginPaymentCapture = useCallback(
    (paymentMethodCode?: PosPaymentMethodCode) => {
      if (!hasTicket) {
        setPaymentInlineError("Agrega al menos un producto antes de cobrar.");
        return;
      }

      if (controlState === CONTROL_STATE_PAYMENT_CAPTURE && paymentMethodCode === undefined) {
        return;
      }

      setPaymentInlineError(null);
      openPaymentCapture();
      saleFlow.enterPaymentCapture(paymentMethodCode);
    },
    [controlState, hasTicket, openPaymentCapture, saleFlow],
  );

  const activateCashPaymentInput = useCallback(() => {
    if (!hasTicket || saleFlow.state.mode === SALE_FLOW_PROCESSING) {
      return;
    }

    setPaymentInlineError(null);

    if (saleFlow.state.mode === SALE_FLOW_AMOUNT_CONFIRMED) {
      saleFlow.returnToPaymentEdit();
      window.setTimeout(() => {
        primaryAmountInputRef.current?.focus();
        primaryAmountInputRef.current?.select();
      }, 0);
      return;
    }

    if (saleFlow.state.mode === SALE_FLOW_RECOVERABLE_ERROR) {
      saleFlow.clearRecoverableError(SALE_FLOW_PAYMENT_AMOUNT_CAPTURE);
      window.setTimeout(() => {
        primaryAmountInputRef.current?.focus();
        primaryAmountInputRef.current?.select();
      }, 0);
      return;
    }

    if (controlState !== CONTROL_STATE_PAYMENT_CAPTURE) {
      beginPaymentCapture(CASH_PAYMENT_METHOD_CODE);
      return;
    }

    window.setTimeout(() => {
      primaryAmountInputRef.current?.focus();
      primaryAmountInputRef.current?.select();
    }, 0);
  }, [beginPaymentCapture, controlState, hasTicket, saleFlow]);

  const switchPaymentMethod = useCallback(
    (paymentMethodCode: PosPaymentMethodCode) => {
      if (saleFlow.state.mode === SALE_FLOW_AMOUNT_CONFIRMED) {
        saleFlow.switchPaymentMethod(paymentMethodCode);
        return;
      }

      if (controlState !== CONTROL_STATE_PAYMENT_CAPTURE) {
        beginPaymentCapture(paymentMethodCode);
        return;
      }

      saleFlow.switchPaymentMethod(paymentMethodCode);
    },
    [beginPaymentCapture, controlState, saleFlow],
  );

  const confirmAmount = useCallback(() => {
    if (saleFlow.state.mode !== SALE_FLOW_PAYMENT_AMOUNT_CAPTURE) {
      return;
    }

    const result = saleFlow.confirmAmount(totalAmountCents);
    if (!result.ok) {
      setPaymentInlineError(result.error);
      focusPrimaryPaymentInput();
      return;
    }

    setPaymentInlineError(null);
  }, [focusPrimaryPaymentInput, saleFlow, totalAmountCents]);

  const finalizeSale = useCallback(async () => {
    if (
      saleFlow.state.mode !== SALE_FLOW_AMOUNT_CONFIRMED &&
      saleFlow.state.mode !== SALE_FLOW_RECOVERABLE_ERROR
    ) {
      return;
    }

    if (confirmSaleMutation.isPending) {
      return;
    }

    confirmSaleMutation.reset();
    setPaymentInlineError(null);
    saleFlow.clearRecoverableError(SALE_FLOW_AMOUNT_CONFIRMED);
    saleFlow.startProcessing();

    let printWindow: Window | null = null;
    if (saleFlow.state.ticketRequested) {
      printWindow = openBrowserPrintWindow();
    }

    try {
      const sale = await confirmSaleMutation.mutateAsync();
      saleFlow.clearPrintFailure();
      const shouldPrintTicket = saleFlow.state.ticketRequested;
      const successMessage =
        (parseMoneyToCents(String(sale.change_amount)) ?? 0) > 0
          ? `Venta registrada. Cambio ${formatDisplayAmount(parseMoneyToCents(String(sale.change_amount)) ?? 0)}.`
          : "Venta registrada.";

      clearCart();
      saleFlow.resetAfterFinish();

      if (shouldPrintTicket) {
        try {
          await printTicketForSale(sale.id, printWindow);
          showSuccess(successMessage);
        } catch (error) {
          printWindow?.close();
          void error;
          showWarning("Venta registrada, pero no se pudo imprimir.");
        }
      } else {
        printWindow?.close();
        showSuccess(successMessage);
      }
    } catch (error) {
      printWindow?.close();
      void error;
      saleFlow.registerRecoverableError({
        kind: "operation",
        message: "No se pudo registrar la venta. Reintenta o vuelve al cobro.",
        retryMode: SALE_FLOW_AMOUNT_CONFIRMED,
      });
    }
  }, [
    clearCart,
    confirmSaleMutation,
    printTicketForSale,
    saleFlow,
    showSuccess,
    showWarning,
  ]);

  useEffect(() => {
    function handleCheckoutKeyboard(event: KeyboardEvent) {
      if (event.defaultPrevented) {
        return;
      }

      const activeTarget = event.target;
      const isKnownPaymentInput =
        activeTarget === primaryAmountInputRef.current || activeTarget === mixedLegAmountInputRef.current;

      if (isClearCartConfirming && event.key === "Escape") {
        event.preventDefault();
        setIsClearCartConfirming(false);
        return;
      }

      if (
        saleFlow.state.mode === SALE_FLOW_ACTIVE_SELECTION &&
        saleFlow.state.selectedTicketLineId !== null &&
        !isEditableTarget(activeTarget)
      ) {
        if (event.key === "Delete") {
          event.preventDefault();
          removeLine(saleFlow.state.selectedTicketLineId);
          if (editingLineKey === saleFlow.state.selectedTicketLineId) {
            cancelInlineLineEdit();
          }
          saleFlow.setSelectedTicketLineId(null);
          return;
        }

        if (event.key === "=") {
          event.preventDefault();
          const selectedLine = cartLines.find(
            (line) => line.key === saleFlow.state.selectedTicketLineId,
          );
          if (selectedLine) {
            beginInlineLineEdit(selectedLine.key, selectedLine.quantityText);
          }
          return;
        }

        if (event.key === "Escape") {
          event.preventDefault();
          saleFlow.setSelectedTicketLineId(null);
          return;
        }
      }

      if (!isEditablePaymentState && saleFlow.state.mode !== SALE_FLOW_AMOUNT_CONFIRMED && !isRecoverableConfirmed) {
        return;
      }

      if (isEditableTarget(activeTarget) && !isKnownPaymentInput) {
        return;
      }

      const shortcutPaymentMethod = getPaymentMethodFromShortcut(event.key);
      if (shortcutPaymentMethod) {
        event.preventDefault();
        switchPaymentMethod(shortcutPaymentMethod);
        return;
      }

      if (saleFlow.state.mode === SALE_FLOW_AMOUNT_CONFIRMED || isRecoverableConfirmed) {
        if (event.key === "." || event.code === "NumpadDecimal") {
          event.preventDefault();
          saleFlow.toggleTicketRequested();
          return;
        }

        if (event.key === "Escape") {
          event.preventDefault();
          if (isRecoverableConfirmed) {
            saleFlow.clearRecoverableError(SALE_FLOW_AMOUNT_CONFIRMED);
            return;
          }

          saleFlow.returnToPaymentEdit();
          return;
        }

        if (isSubmitKey(event.key)) {
          event.preventDefault();
          void finalizeSale();
        }
        return;
      }

      if (event.key === "Escape") {
        event.preventDefault();
        setPaymentInlineError(null);
        if (saleFlow.state.mode === SALE_FLOW_RECOVERABLE_ERROR) {
          saleFlow.clearRecoverableError(SALE_FLOW_PAYMENT_AMOUNT_CAPTURE);
        } else {
          goBack();
        }
        return;
      }

      if (isSubmitKey(event.key)) {
        event.preventDefault();
        confirmAmount();
      }
    }

    window.addEventListener("keydown", handleCheckoutKeyboard);
    return () => window.removeEventListener("keydown", handleCheckoutKeyboard);
  }, [
    beginInlineLineEdit,
    cancelInlineLineEdit,
    cartLines,
    confirmAmount,
    editingLineKey,
    finalizeSale,
    goBack,
    isEditablePaymentState,
    isRecoverableConfirmed,
    isClearCartConfirming,
    removeLine,
    saleFlow,
    switchPaymentMethod,
  ]);

  const actionButtonLabel =
    saleFlow.state.mode === SALE_FLOW_PROCESSING
      ? "Procesando..."
      : isEditablePaymentState
          ? saleFlow.state.paymentMethodCode === MIXED_PAYMENT_METHOD_CODE &&
              paymentComputation.remainingAmountCents > 0
            ? "Confirmar tramo"
            : "Cobrar"
          : "Cobrar";

  return (
    <div className="grid h-full min-h-0 grid-rows-[auto_minmax(0,1fr)_auto] gap-2 overflow-hidden rounded-xl border border-[var(--pos-shell-border)] bg-[var(--pos-shell-surface)] p-2.5 shadow-[var(--pos-subtle-shadow)]">
      <div className="grid gap-2">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[var(--pos-shell-muted)] text-[var(--pos-primary)]">
                <ReceiptIcon className="h-4 w-4" />
              </span>
              <div className="min-w-0">
                <p className="pos-label-text">Ticket actual</p>
              </div>
            </div>
          </div>

          <span
            className="pos-chip"
            data-tone={
              saleFlow.state.mode === SALE_FLOW_PROCESSING ||
              saleFlow.state.mode === SALE_FLOW_AMOUNT_CONFIRMED
                ? "primary"
                : "muted"
            }
          >
            {stateLabel}
          </span>
        </div>

        {isClearCartConfirming ? (
          <div className="grid gap-2 rounded-lg border border-[var(--ui-color-danger-soft)] bg-[var(--ui-color-danger-soft)] px-3 py-2">
            <p className="text-sm font-medium text-[var(--ui-color-danger)]">
              Vaciar ticket actual?
            </p>
            <div className="flex flex-wrap items-center justify-end gap-1.5">
              <Button
                className={cn("h-8 px-2.5 text-xs", posOutlineButtonClass)}
                onClick={() => setIsClearCartConfirming(false)}
                type="button"
              >
                Cancelar
              </Button>
              <Button
                className={cn("h-8 px-2.5 text-xs", posPrimaryButtonClass)}
                onClick={() => {
                  clearCart();
                  setIsClearCartConfirming(false);
                }}
                type="button"
              >
                Confirmar vaciado
              </Button>
            </div>
          </div>
        ) : (
          <div className="flex flex-wrap items-center justify-end gap-1.5">
            <Button
              className={cn("h-8 px-2.5 text-xs", posOutlineButtonClass)}
              disabled={!hasTicket || saleFlow.state.mode === SALE_FLOW_PROCESSING}
              onClick={repeatLastLine}
              type="button"
            >
              Repetir
            </Button>
            <Button
              className={cn("h-8 px-2.5 text-xs", posOutlineButtonClass)}
              disabled={!hasTicket || saleFlow.state.mode === SALE_FLOW_PROCESSING}
              onClick={() => setIsClearCartConfirming(true)}
              type="button"
            >
              Vaciar ticket
            </Button>
          </div>
        )}
      </div>

      <div className="min-h-0 overflow-hidden rounded-xl border border-[var(--pos-shell-border)] bg-white">
        {cartLines.length === 0 ? (
          <div className="grid h-full min-h-[7rem]">
            <div className="flex items-center justify-center px-4 py-4 text-center text-sm leading-6 text-slate-600">
              El ticket esta vacio. Agrega productos desde el catalogo para empezar la venta.
            </div>
          </div>
        ) : (
          <div className="grid h-full min-h-0 grid-rows-[minmax(0,1fr)_auto]">
            <div className="min-h-0 overflow-y-auto" role="grid">
              {cartLines.map((line) => (
                <TicketLineRow
                  amount={formatDisplayAmount(getLineTotalCents(line))}
                  editingQuantityText={
                    editingLineKey === line.key ? editingQuantityText : line.quantityText
                  }
                  inputRef={inlineQuantityInputRef}
                  isEditing={editingLineKey === line.key}
                  isSelected={saleFlow.state.selectedTicketLineId === line.key}
                  key={line.key}
                  name={line.catalogNameSnapshot}
                  onDecrement={() => decrementLineQuantity(line.key)}
                  onBeginEdit={() => beginInlineLineEdit(line.key, line.quantityText)}
                  onCancelEdit={cancelInlineLineEdit}
                  onCommitEdit={commitInlineLineEdit}
                  onEditingQuantityChange={(value) => {
                    setTicketInlineError(null);
                    setEditingQuantityText(sanitizeQuantityInput(value));
                  }}
                  onIncrement={() => incrementLineQuantity(line.key)}
                  onRemove={() => {
                    if (editingLineKey === line.key) {
                      cancelInlineLineEdit();
                    }
                    removeLine(line.key);
                  }}
                  onSelect={() => saleFlow.setSelectedTicketLineId(line.key)}
                  quantity={formatQuantityFromMilliUnits(line.quantityMilliUnits)}
                />
              ))}
            </div>
            {ticketInlineError ? (
              <div className="border-t border-[var(--pos-shell-border)] px-3 py-2">
                <PosInlineValidationMessage tone="warning">
                  {ticketInlineError}
                </PosInlineValidationMessage>
              </div>
            ) : null}
          </div>
        )}
      </div>

      {hasTicket ? (
        <div className="grid gap-3 rounded-xl border border-[var(--pos-shell-border)] bg-white p-3 shadow-[var(--ui-shadow-subtle)]">
          <div className="grid gap-2">
            <div className="flex items-center justify-between gap-3">
              <div className="flex min-w-0 items-center gap-2">
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[var(--pos-shell-muted)] text-[var(--pos-primary)]">
                  <MoneyIcon className="h-4 w-4" />
                </span>
                <div className="min-w-0">
                  <p className="truncate whitespace-nowrap text-[15px] font-semibold leading-5 text-slate-950">
                    {saleFlow.state.paymentMethodCode === MIXED_PAYMENT_METHOD_CODE
                      ? "Cobro mixto"
                      : saleFlow.state.paymentMethodCode === CARD_PAYMENT_METHOD_CODE
                        ? "Cobro con tarjeta"
                        : "Cobro efectivo"}
                  </p>
                </div>
              </div>
              {saleFlow.state.paymentMethodCode === MIXED_PAYMENT_METHOD_CODE ? (
                <span className="pos-chip" data-tone="primary">
                  Efectivo + tarjeta
                </span>
              ) : null}
            </div>

            <div className="grid grid-cols-3 gap-2">
              {paymentControls.map((paymentMethod) => (
                <PaymentMethodButton
                  code={paymentMethod.code}
                  icon={
                    paymentMethod.code === CASH_PAYMENT_METHOD_CODE ? (
                      <MoneyIcon className="h-5 w-5" />
                    ) : paymentMethod.code === MIXED_PAYMENT_METHOD_CODE ? (
                      <SplitIcon className="h-5 w-5" />
                    ) : (
                      <CardIcon className="h-5 w-5" />
                    )
                  }
                  isActive={paymentMethod.code === saleFlow.state.paymentMethodCode}
                  isDisabled={saleFlow.state.mode === SALE_FLOW_PROCESSING}
                  key={paymentMethod.code}
                  label={paymentMethod.label}
                  onClick={switchPaymentMethod}
                />
              ))}
            </div>
          </div>

          {isEditablePaymentState || showCashReceivedInput ? (
            <div className="grid gap-2">
              {showCashReceivedInput ? (
                <PosPaymentInputCard icon={<MoneyIcon className="h-5 w-5" />} label="Recibe">
                  <input
                    aria-label="Dinero recibido"
                    className={cn(
                      "h-11 w-full rounded-xl px-3 text-right text-[1.35rem] font-semibold leading-none tracking-tight [font-variant-numeric:tabular-nums]",
                      posInputClass,
                      "border-[var(--pos-primary)] ring-2 ring-[var(--pos-ring)]",
                    )}
                    disabled={saleFlow.state.mode === SALE_FLOW_PROCESSING}
                    inputMode="decimal"
                    onChange={(event) => saleFlow.updateCashReceivedText(event.target.value)}
                    onFocus={() => activateCashPaymentInput()}
                    onKeyDown={(event) => {
                      const shortcutPaymentMethod = getPaymentMethodFromShortcut(event.key);
                      if (shortcutPaymentMethod) {
                        event.preventDefault();
                        event.stopPropagation();
                        switchPaymentMethod(shortcutPaymentMethod);
                        return;
                      }

                      if (event.key === "Escape") {
                        event.preventDefault();
                        event.stopPropagation();
                        setPaymentInlineError(null);
                        goBack();
                        return;
                      }

                      if (isSubmitKey(event.key)) {
                        event.preventDefault();
                        event.stopPropagation();
                        confirmAmount();
                      }
                    }}
                    placeholder="0.00"
                    ref={primaryAmountInputRef}
                    value={saleFlow.state.cashReceivedText}
                  />
                </PosPaymentInputCard>
              ) : null}

              {isEditablePaymentState &&
              saleFlow.state.paymentMethodCode === CARD_PAYMENT_METHOD_CODE ? (
                <PosPaymentValueCard
                  icon={<CardIcon className="h-5 w-5" />}
                  label="Tarjeta"
                  tone="input"
                  value={totalAmountText}
                />
              ) : null}

              {isEditablePaymentState &&
              saleFlow.state.paymentMethodCode === MIXED_PAYMENT_METHOD_CODE ? (
                <div className="grid gap-2">
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      aria-pressed={
                        saleFlow.state.mixedCurrentLegMethodCode === CASH_PAYMENT_METHOD_CODE
                      }
                      className={cn(
                        "pos-shortcut-corner rounded-lg border px-3 py-2 text-sm font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--pos-ring)]",
                        saleFlow.state.mixedCurrentLegMethodCode === CASH_PAYMENT_METHOD_CODE
                          ? "border-[var(--pos-primary)] bg-[var(--pos-primary-soft)] text-[var(--pos-primary)]"
                          : "border-[var(--pos-shell-border)] bg-white text-slate-700",
                      )}
                      data-shortcut="/"
                      data-shortcut-tone={
                        saleFlow.state.mixedCurrentLegMethodCode === CASH_PAYMENT_METHOD_CODE
                          ? "primary"
                          : "default"
                      }
                      onClick={() => saleFlow.setMixedCurrentLegMethodCode(CASH_PAYMENT_METHOD_CODE)}
                      type="button"
                    >
                      / Efectivo
                    </button>
                    <button
                      aria-pressed={
                        saleFlow.state.mixedCurrentLegMethodCode === CARD_PAYMENT_METHOD_CODE
                      }
                      className={cn(
                        "pos-shortcut-corner rounded-lg border px-3 py-2 text-sm font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--pos-ring)]",
                        saleFlow.state.mixedCurrentLegMethodCode === CARD_PAYMENT_METHOD_CODE
                          ? "border-[var(--pos-primary)] bg-[var(--pos-primary-soft)] text-[var(--pos-primary)]"
                          : "border-[var(--pos-shell-border)] bg-white text-slate-700",
                      )}
                      data-shortcut="*"
                      data-shortcut-tone={
                        saleFlow.state.mixedCurrentLegMethodCode === CARD_PAYMENT_METHOD_CODE
                          ? "primary"
                          : "default"
                      }
                      onClick={() => saleFlow.setMixedCurrentLegMethodCode(CARD_PAYMENT_METHOD_CODE)}
                      type="button"
                    >
                      * Tarjeta
                    </button>
                  </div>

                  <PosPaymentInputCard icon={<SplitIcon className="h-5 w-5" />} label="Monto del tramo">
                    <input
                      aria-label="Monto del tramo"
                      className={cn(
                        "h-11 w-full rounded-xl px-3 text-right text-[1.35rem] font-semibold leading-none tracking-tight [font-variant-numeric:tabular-nums]",
                        posInputClass,
                        "border-[var(--pos-primary)] ring-2 ring-[var(--pos-ring)]",
                      )}
                      inputMode="decimal"
                      onChange={(event) =>
                        saleFlow.updateMixedCurrentLegAmountText(event.target.value)
                      }
                      onFocus={(event) => event.currentTarget.select()}
                      onKeyDown={(event) => {
                        const shortcutPaymentMethod = getPaymentMethodFromShortcut(event.key);
                        if (
                          shortcutPaymentMethod === CASH_PAYMENT_METHOD_CODE ||
                          shortcutPaymentMethod === CARD_PAYMENT_METHOD_CODE
                        ) {
                          event.preventDefault();
                          event.stopPropagation();
                          saleFlow.setMixedCurrentLegMethodCode(
                            shortcutPaymentMethod as PosSplitPaymentMethodCode,
                          );
                          return;
                        }

                        if (shortcutPaymentMethod === MIXED_PAYMENT_METHOD_CODE) {
                          event.preventDefault();
                          event.stopPropagation();
                          return;
                        }

                        if (event.key === "Escape") {
                          event.preventDefault();
                          event.stopPropagation();
                          setPaymentInlineError(null);
                          goBack();
                          return;
                        }

                        if (isSubmitKey(event.key)) {
                          event.preventDefault();
                          event.stopPropagation();
                          confirmAmount();
                        }
                      }}
                      placeholder="0.00"
                      ref={mixedLegAmountInputRef}
                      value={saleFlow.state.mixedCurrentLegAmountText}
                    />
                  </PosPaymentInputCard>

                  <div className="grid gap-2">
                    <MixedLegSummary
                      amount={formatDisplayAmount(paymentComputation.remainingAmountCents)}
                      label="Restante confirmado"
                    />
                    <MixedLegSummary
                      amount={formatDisplayAmount(paymentComputation.previewRemainingAmountCents)}
                      label="Restante despues del tramo"
                    />
                    {saleFlow.state.mixedConfirmedLegs.map((leg) => (
                      <MixedLegSummary
                        amount={formatDisplayAmount(leg.amountCents)}
                        key={leg.key}
                        label={leg.methodCode === CASH_PAYMENT_METHOD_CODE ? "Efectivo" : "Tarjeta"}
                      />
                    ))}
                  </div>
                </div>
              ) : null}

              {paymentInlineError ? (
                <PosInlineValidationMessage tone="warning">
                  {paymentInlineError}
                </PosInlineValidationMessage>
              ) : null}
            </div>
          ) : null}

          <div className="grid gap-2">
            {!isEditablePaymentState && !showCashReceivedInput ? (
              <CheckoutMetricTile
                icon={
                  saleFlow.state.paymentMethodCode === CARD_PAYMENT_METHOD_CODE ? (
                    <CardIcon className="h-5 w-5" />
                  ) : (
                    <MoneyIcon className="h-5 w-5" />
                  )
                }
                label={
                  saleFlow.state.paymentMethodCode === CARD_PAYMENT_METHOD_CODE ? "Tarjeta" : "Recibe"
                }
                tone="input"
                value={effectiveReceivedAmountText}
              />
            ) : null}
            <CheckoutMetricTile
              icon={<ReceiptIcon className="h-5 w-5" />}
              label="Total"
              tone="financial"
              value={totalAmountText}
            />
            <CheckoutMetricTile
              icon={
                saleFlow.state.mode === SALE_FLOW_PROCESSING ? (
                  <ClockIcon className="h-5 w-5" />
                ) : paymentComputation.previewRemainingAmountCents > 0 &&
                    saleFlow.state.mode !== SALE_FLOW_AMOUNT_CONFIRMED ? (
                    <MoneyIcon className="h-5 w-5" />
                  ) : (
                    <CheckCircleIcon className="h-5 w-5" />
                  )
              }
              label={
                effectiveResultLabel === "Falta"
                  ? "Pendiente"
                  : effectiveResultLabel
              }
              tone={effectiveResultTone}
              value={effectiveResultValueText}
            />
          </div>

          {(saleFlow.state.mode === SALE_FLOW_AMOUNT_CONFIRMED || isRecoverableConfirmed) &&
          saleFlow.state.paymentMethodCode === MIXED_PAYMENT_METHOD_CODE ? (
            <div className="grid gap-2 rounded-xl border border-[#82d7ac] bg-[#eafaf1] p-3">
              <div className="grid gap-2">
                {saleFlow.state.mixedConfirmedLegs.map((leg) => (
                  <MixedLegSummary
                    amount={formatDisplayAmount(leg.amountCents)}
                    key={leg.key}
                    label={leg.methodCode === CASH_PAYMENT_METHOD_CODE ? "Efectivo" : "Tarjeta"}
                  />
                ))}
              </div>
            </div>
          ) : null}

          {saleFlow.state.recoverableError ? (
            <PosInlineValidationMessage
              action={
                <div className="flex items-center gap-2">
                  <Button
                    className={cn("h-8 px-2.5 text-xs", posOutlineButtonClass)}
                    onClick={() =>
                      saleFlow.clearRecoverableError(
                        saleFlow.state.recoverableError?.retryMode ??
                          SALE_FLOW_PAYMENT_AMOUNT_CAPTURE,
                      )
                    }
                    type="button"
                  >
                    {saleFlow.state.recoverableError.retryMode === SALE_FLOW_AMOUNT_CONFIRMED
                      ? "Volver al cierre"
                      : "Volver al cobro"}
                  </Button>
                  <Button
                    className={cn("h-8 px-2.5 text-xs", posPrimaryButtonClass)}
                    onClick={() =>
                      saleFlow.state.recoverableError?.retryMode === SALE_FLOW_AMOUNT_CONFIRMED
                        ? void finalizeSale()
                        : confirmAmount()
                    }
                    type="button"
                  >
                    Reintentar
                  </Button>
                </div>
              }
              tone="error"
            >
              {saleFlow.state.recoverableError.message}
            </PosInlineValidationMessage>
          ) : null}

          {saleFlow.state.mode === SALE_FLOW_PROCESSING ? (
            <PosInlineValidationMessage tone="info">
              Procesando la venta. Espera la respuesta para evitar cobros duplicados.
            </PosInlineValidationMessage>
          ) : null}

          {helperText ? <p className="text-sm leading-5 text-slate-600">{helperText}</p> : null}

          <div className="grid gap-1.5">
            <TicketRequestToggle
              checked={saleFlow.state.ticketRequested}
              disabled={saleFlow.state.mode === SALE_FLOW_PROCESSING || !canToggleTicketRequest}
              onToggle={saleFlow.toggleTicketRequested}
            />
            <Button
              ref={actionButtonRef}
              className={cn(
                "h-12 w-full text-base",
                posPrimaryButtonClass,
                saleFlow.state.mode === SALE_FLOW_AMOUNT_CONFIRMED ||
                  isRecoverableConfirmed ||
                  isEditablePaymentState
                  ? "pos-shortcut-corner"
                  : null,
              )}
              data-shortcut={
                saleFlow.state.mode === SALE_FLOW_AMOUNT_CONFIRMED ||
                isRecoverableConfirmed ||
                isEditablePaymentState
                  ? "Enter"
                  : undefined
              }
              data-shortcut-tone="inverted"
              disabled={
                saleFlow.state.mode === SALE_FLOW_PROCESSING ||
                (!canEnterPayment &&
                  !isEditablePaymentState &&
                  saleFlow.state.mode !== SALE_FLOW_AMOUNT_CONFIRMED &&
                  !isRecoverableConfirmed)
              }
              onClick={() => {
                if (isEditablePaymentState) {
                  confirmAmount();
                  return;
                }

                if (
                  saleFlow.state.mode === SALE_FLOW_AMOUNT_CONFIRMED ||
                  isRecoverableConfirmed
                ) {
                  void finalizeSale();
                  return;
                }

                beginPaymentCapture();
              }}
              type="button"
            >
              {actionButtonLabel}
            </Button>
            {canEditSelectedLine ? (
              <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
                <span className="pos-chip" data-tone="muted">
                  Delete: eliminar
                </span>
                <span className="pos-chip" data-tone="muted">
                  =: editar cantidad
                </span>
              </div>
            ) : null}
          </div>
        </div>
      ) : (
        <div className="grid gap-2 rounded-xl border border-dashed border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)]/80 px-3 py-3 text-slate-600">
          <div className="flex items-center gap-2">
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white text-[var(--pos-primary)]">
              <MoneyIcon className="h-4 w-4" />
            </span>
            <div className="min-w-0">
              <p className="pos-label-text">Cobro</p>
              <p className="mt-0.5 text-sm leading-5 text-slate-600">
                Agrega una linea para habilitar el cobro del ticket.
              </p>
            </div>
          </div>
          <Button
            className={cn("h-11 w-full text-base opacity-80", posPrimaryButtonClass)}
            disabled
            type="button"
          >
            Cobrar
          </Button>
        </div>
      )}
    </div>
  );
}

