import { create } from "zustand";

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
  addPendingLine: () => void;
  cartLines: PosCartLine[];
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
  addPendingLine: () => set((state) => addPendingSelectionToCart(state)),
  clearCart: () => set((state) => clearCart(state)),
  clearQuantity: () => set((state) => clearPendingQuantity(state)),
  decrementLineQuantity: (lineKey) =>
    set((state) => decrementCartLineQuantity(state, lineKey)),
  decrementPendingQuantity: () => set((state) => decrementPendingQuantity(state)),
  dismissLastCompletedSale: () => set((state) => dismissLastCompletedSale(state)),
  enterPaymentCapture: () => set((state) => enterPaymentCapture(state)),
  goBack: () => set((state) => goBackFromControlState(state)),
  incrementLineQuantity: (lineKey) =>
    set((state) => incrementCartLineQuantity(state, lineKey)),
  incrementPendingQuantity: () => set((state) => incrementPendingQuantity(state)),
  markSaleCompleted: (sale) => set((state) => markSaleCompleted(state, sale)),
  removeLine: (lineKey) => set((state) => removeCartLine(state, lineKey)),
  repeatLastLine: () => set((state) => repeatLastCartLine(state)),
  reset: () => set(createInitialPosTerminalState()),
  selectClass: (productClass) => set((state) => beginSelectionFromClass(state, productClass)),
  selectProduct: (product) => set((state) => selectProductForPending(state, product)),
  setLineQuantity: (lineKey, quantityText) =>
    set((state) => setCartLineQuantity(state, lineKey, quantityText)),
  setQuantityText: (quantityText) => set((state) => setPendingQuantityText(state, quantityText)),
  setSearchText: (searchText) =>
    set((state) => ({
      ...state,
      lastCompletedSale: null,
      searchText,
    })),
}));
