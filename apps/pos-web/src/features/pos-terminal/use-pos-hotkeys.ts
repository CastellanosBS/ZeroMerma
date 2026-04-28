import { useEffect } from "react";

import type { PosCatalogClassView, PosCatalogProductView } from "../../lib/api-contracts";
import {
  getSelectionShortcutIndex,
  isEditableTarget,
} from "../../lib/keyboard-shortcuts";
import type { PosControlState } from "./model";
import {
  CONTROL_STATE_CLASS_SELECTION,
  CONTROL_STATE_PAYMENT_CAPTURE,
  CONTROL_STATE_PRODUCT_SELECTION,
  CONTROL_STATE_QUANTITY_CAPTURE,
} from "./model";

export function usePosHotkeys({
  cartLineCount,
  controlState,
  enterPaymentCapture,
  focusSearch,
  goBack,
  onBlockedPaymentCapture,
  searchText,
  selectClass,
  selectProduct,
  setQuantityText,
  setSearchText,
  showSearch,
  sortedClasses,
  sortedProducts,
}: {
  cartLineCount: number;
  controlState: PosControlState;
  enterPaymentCapture: () => void;
  focusSearch: () => void;
  goBack: () => void;
  onBlockedPaymentCapture: (message: string) => void;
  searchText: string;
  selectClass: (productClass: PosCatalogClassView) => void;
  selectProduct: (product: PosCatalogProductView) => void;
  setQuantityText: (quantityText: string) => void;
  setSearchText: (searchText: string) => void;
  showSearch: boolean;
  sortedClasses: PosCatalogClassView[];
  sortedProducts: PosCatalogProductView[];
}) {
  useEffect(() => {
    let pendingPaymentIntentAt: number | null = null;

    function clearPaymentIntent() {
      pendingPaymentIntentAt = null;
    }

    function attemptEnterPaymentCapture() {
      clearPaymentIntent();
      if (cartLineCount <= 0) {
        onBlockedPaymentCapture("Agrega al menos un producto antes de cobrar");
        return;
      }

      enterPaymentCapture();
    }

    function handleKeyboard(event: KeyboardEvent) {
      const isSelectionContext =
        controlState === CONTROL_STATE_CLASS_SELECTION ||
        controlState === CONTROL_STATE_PRODUCT_SELECTION;

      if (event.key === "Escape") {
        clearPaymentIntent();
        if (
          controlState === CONTROL_STATE_PRODUCT_SELECTION ||
          controlState === CONTROL_STATE_QUANTITY_CAPTURE ||
          controlState === CONTROL_STATE_PAYMENT_CAPTURE
        ) {
          event.preventDefault();
          goBack();
          return;
        }

        if (searchText.trim().length > 0) {
          event.preventDefault();
          setSearchText("");
        }

        return;
      }

      if (showSearch && (event.key === "/" || (event.ctrlKey && event.key.toLowerCase() === "f"))) {
        if (isEditableTarget(event.target)) {
          return;
        }

        clearPaymentIntent();
        event.preventDefault();
        focusSearch();
        return;
      }

      if (
        isSelectionContext &&
        !event.ctrlKey &&
        !event.altKey &&
        !event.metaKey &&
        !event.shiftKey &&
        event.code === "NumpadDecimal"
      ) {
        pendingPaymentIntentAt = Date.now();
        return;
      }

      if (
        isSelectionContext &&
        !event.ctrlKey &&
        !event.altKey &&
        !event.metaKey &&
        !event.shiftKey &&
        event.code === "NumpadEnter"
      ) {
        if (
          pendingPaymentIntentAt !== null &&
          Date.now() - pendingPaymentIntentAt <= 300
        ) {
          event.preventDefault();
          attemptEnterPaymentCapture();
          return;
        }

        clearPaymentIntent();
      } else if (pendingPaymentIntentAt !== null && event.code !== "NumpadDecimal") {
        clearPaymentIntent();
      }

      if (isEditableTarget(event.target)) {
        return;
      }

      if (
        controlState !== CONTROL_STATE_PAYMENT_CAPTURE &&
        controlState !== CONTROL_STATE_QUANTITY_CAPTURE &&
        event.key === "F2"
      ) {
        event.preventDefault();
        attemptEnterPaymentCapture();
        return;
      }

      if (
        controlState === CONTROL_STATE_QUANTITY_CAPTURE &&
        event.altKey &&
        !event.ctrlKey &&
        !event.metaKey &&
        !event.shiftKey
      ) {
        const quickQuantityMap: Record<string, string> = {
          "1": "1",
          "2": "2",
          "3": "3",
          "6": "6",
        };
        const preset = quickQuantityMap[event.key];
        if (preset) {
          event.preventDefault();
          setQuantityText(preset);
          return;
        }
      }

      const shortcutIndex = getSelectionShortcutIndex(event.key);
      if (shortcutIndex === null) {
        return;
      }

      if (controlState === CONTROL_STATE_CLASS_SELECTION) {
        const productClass = sortedClasses[shortcutIndex];
        if (productClass) {
          event.preventDefault();
          selectClass(productClass);
        }
        return;
      }

      if (controlState === CONTROL_STATE_PRODUCT_SELECTION) {
        const product = sortedProducts[shortcutIndex];
        if (product) {
          event.preventDefault();
          selectProduct(product);
        }
      }
    }

    window.addEventListener("keydown", handleKeyboard);
    return () => window.removeEventListener("keydown", handleKeyboard);
  }, [
    cartLineCount,
    controlState,
    enterPaymentCapture,
    focusSearch,
    goBack,
    onBlockedPaymentCapture,
    searchText,
    selectClass,
    selectProduct,
    setQuantityText,
    setSearchText,
    showSearch,
    sortedClasses,
    sortedProducts,
  ]);
}
