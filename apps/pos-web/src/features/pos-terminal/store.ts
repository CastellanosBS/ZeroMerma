import { create } from "zustand";
import type { SaleIntentionMetadata } from "./sale-confirmation-intent";
import { isCommandIntentionPending } from "@zeromerma/api-client";

import type {
  PosCatalogClassView,
  PosCatalogProductView,
  SaleDetailView,
} from "../../lib/api-contracts";
import {
  addPendingSelectionToCart,
  beginSelectionFromClass,
  clearCart,
  clearPendingQuantity,
  createInitialPosTerminalState,
  decrementCartLineQuantity,
  decrementPendingQuantity,
  dismissLastCompletedSale,
  enterPaymentCapture,
  goBackFromControlState,
  incrementCartLineQuantity,
  incrementPendingQuantity,
  markSaleCompleted,
  removeCartLine,
  repeatLastCartLine,
  selectProductForPending,
  setCartLineQuantity,
  setPendingQuantityText,
  type PendingSelection,
  type PosCartLine,
  type PosControlState,
} from "./model";

interface PosTerminalStore {
  cartMutationBlocked: boolean;
  saleSubmissionPending: boolean;
  saleIntentionPending: boolean;
  setSaleSubmissionPending: (pending: boolean) => void;
  clearConfirmedSale: () => void;
  saleDraftIntentionKey: string | null | undefined;
  observeSaleIntention: (metadata: SaleIntentionMetadata | null) => void;
  addPendingLine: () => void;
  cartLines: PosCartLine[];
  replaceReviewedPrices: (original: PosCartLine[], updated: PosCartLine[]) => boolean;
  clearCart: () => void;
  clearQuantity: () => void;
  controlState: PosControlState;
  decrementLineQuantity: (lineKey: string) => void;
  decrementPendingQuantity: () => void;
  dismissLastCompletedSale: () => void;
  enterPaymentCapture: () => void;
  goBack: () => void;
  incrementLineQuantity: (lineKey: string) => void;
  incrementPendingQuantity: () => void;
  lastCompletedSale: SaleDetailView | null;
  markSaleCompleted: (sale: SaleDetailView) => void;
  pendingSelection: PendingSelection | null;
  removeLine: (lineKey: string) => void;
  repeatLastLine: () => void;
  reset: () => void;
  searchText: string;
  selectClass: (productClass: PosCatalogClassView) => void;
  selectProduct: (product: PosCatalogProductView) => void;
  setLineQuantity: (lineKey: string, quantityText: string) => void;
  setQuantityText: (quantityText: string) => void;
  setSearchText: (searchText: string) => void;
}

const initialState = createInitialPosTerminalState();

export const usePosTerminalStore = create<PosTerminalStore>()((set) => ({
  ...initialState,
  cartMutationBlocked: false,
  saleSubmissionPending: false,
  saleIntentionPending: false,
  setSaleSubmissionPending: (pending) => set((state) => ({
    saleSubmissionPending: pending,
    cartMutationBlocked: pending || state.saleIntentionPending,
  })),
  clearConfirmedSale: () => set((state) => clearCart(state)),
  replaceReviewedPrices: (original, updated) => {
    let applied = false;
    set((state) => {
      if (state.cartMutationBlocked || state.cartLines !== original) return state;
      applied = true;
      return { cartLines: updated };
    });
    return applied;
  },
  saleDraftIntentionKey: undefined,
  observeSaleIntention: (metadata) =>
    set((state) => {
      const key = metadata?.key ?? null;
      const saleIntentionPending = isCommandIntentionPending(metadata);
      const cartMutationBlocked = state.saleSubmissionPending || saleIntentionPending;
      const lock = { saleIntentionPending, cartMutationBlocked };
      if (
        state.saleDraftIntentionKey === undefined ||
        state.cartLines.length === 0 ||
        metadata?.status === "REJECTED"
      ) {
        return state.saleDraftIntentionKey === key && state.cartMutationBlocked === cartMutationBlocked && state.saleIntentionPending === saleIntentionPending
          ? state : { saleDraftIntentionKey: key, ...lock };
      }
      if (metadata?.status === "CONFIRMED" && state.saleDraftIntentionKey !== key) {
        return { ...clearCart(state), saleDraftIntentionKey: key, ...lock };
      }
      return state.cartMutationBlocked === cartMutationBlocked && state.saleIntentionPending === saleIntentionPending ? state : lock;
    }),
  addPendingLine: () => set((state) => state.cartMutationBlocked ? state : addPendingSelectionToCart(state)),
  clearCart: () => set((state) => state.cartMutationBlocked ? state : clearCart(state)),
  clearQuantity: () => set((state) => state.cartMutationBlocked ? state : clearPendingQuantity(state)),
  decrementLineQuantity: (lineKey) => set((state) => state.cartMutationBlocked ? state : decrementCartLineQuantity(state, lineKey)),
  decrementPendingQuantity: () => set((state) => state.cartMutationBlocked ? state : decrementPendingQuantity(state)),
  dismissLastCompletedSale: () => set((state) => dismissLastCompletedSale(state)),
  enterPaymentCapture: () => set((state) => state.cartMutationBlocked ? state : enterPaymentCapture(state)),
  goBack: () => set((state) => state.cartMutationBlocked ? state : goBackFromControlState(state)),
  incrementLineQuantity: (lineKey) => set((state) => state.cartMutationBlocked ? state : incrementCartLineQuantity(state, lineKey)),
  incrementPendingQuantity: () => set((state) => state.cartMutationBlocked ? state : incrementPendingQuantity(state)),
  markSaleCompleted: (sale) => set((state) => markSaleCompleted(state, sale)),
  removeLine: (lineKey) => set((state) => state.cartMutationBlocked ? state : removeCartLine(state, lineKey)),
  repeatLastLine: () => set((state) => state.cartMutationBlocked ? state : repeatLastCartLine(state)),
  reset: () => set({ ...createInitialPosTerminalState(), saleDraftIntentionKey: undefined, cartMutationBlocked: false, saleSubmissionPending: false, saleIntentionPending: false }),
  selectClass: (productClass) => set((state) => state.cartMutationBlocked ? state : beginSelectionFromClass(state, productClass)),
  selectProduct: (product) => set((state) => state.cartMutationBlocked ? state : selectProductForPending(state, product)),
  setLineQuantity: (lineKey, quantityText) =>
    set((state) => state.cartMutationBlocked ? state : setCartLineQuantity(state, lineKey, quantityText)),
  setQuantityText: (quantityText) => set((state) => state.cartMutationBlocked ? state : setPendingQuantityText(state, quantityText)),
  setSearchText: (searchText) =>
    set((state) => ({
      ...state,
      lastCompletedSale: null,
      searchText,
    })),
}));
