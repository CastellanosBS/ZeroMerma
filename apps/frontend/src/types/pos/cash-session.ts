export type CashSessionStatus = "OPEN" | "CLOSED" | "CANCELED";

export interface CashSessionPaymentMethodTotals {
    cash: string;
    card: string;
    transfer: string;
    other: string;
}

export interface CashSessionNonCashTotals {
    card: string;
    transfer: string;
    other: string;
}

export interface CashSessionReconciliationSnapshot {
    expected_payment_totals_by_method: CashSessionPaymentMethodTotals;
    expected_non_cash_totals_by_method: CashSessionNonCashTotals;
    counted_non_cash_totals_by_method: CashSessionNonCashTotals;
    non_cash_differences_by_method: CashSessionNonCashTotals;

    expected_cash: string;
    counted_cash: string;
    cash_difference: string;

    total_expected_non_cash: string;
    total_counted_non_cash: string;
    total_difference: string;

    assumed_counted_non_cash_methods: string[];
    note: string | null;
}

export interface CashSession {
    id: number;
    branch_id: number;
    opened_by_id: number;
    closed_by_id: number | null;

    opened_at: string;
    closed_at: string | null;

    opening_amount: string;
    closing_amount: string | null;
    expected_cash: string | null;

    reconciliation_snapshot: CashSessionReconciliationSnapshot | null;

    status: CashSessionStatus | string;

    created_at: string;
    updated_at: string;
}

export interface OpenCashSessionInput {
    branch_id: number;
    opening_amount: string;
}

export interface CloseCashSessionInput {
    closing_amount: string;
    counted_card_total?: string;
    counted_transfer_total?: string;
    counted_other_total?: string;
    note?: string;
}
