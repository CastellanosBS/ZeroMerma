import { useEffect, useMemo, useRef, useState } from "react";

import { CatalogSelectionCard } from "../../components/catalog-selection-card";
import { CatalogVisual } from "../../components/catalog-visual";
import { OperationalStatus } from "../../components/operational-status";
import { PosScannerInput } from "../../components/pos-scanner-input";
import {
  CentralWorkspaceSheet,
  FlowGuide,
  ModuleStateChip,
  CompactPageHeader,
  SearchField,
} from "../../components/pos-module-primitives";
import {
  ArrowLeftIcon,
  HashIcon,
  MoneyIcon,
  PackageIcon,
  StoreIcon,
  XIcon,
} from "../../components/pos-icons";
import { Button } from "../../components/ui/button";
import { getSelectionShortcutLabel } from "../../lib/keyboard-shortcuts";
import { matchesScannerValue, parseProductScannerValue } from "../../lib/scanner";
import { toOperationalErrorMessage } from "../../lib/http";
import { cn } from "../../lib/utils";
import { useRovingFocusGrid } from "../pos-shell/keyboard";
import {
  CLASS_CAPTURE_MODE,
  CONTROL_STATE_CLASS_SELECTION,
  CONTROL_STATE_PAYMENT_CAPTURE,
  CONTROL_STATE_PRODUCT_SELECTION,
  CONTROL_STATE_QUANTITY_CAPTURE,
  getPendingCaptureTargetKey,
  hasCapturedQuantity,
  PRODUCT_DIRECT_MODE,
  sortCatalogClasses,
  sortCatalogProducts,
} from "./model";
import { usePosCatalogQuery, usePosClassProductsQuery } from "./queries";
import { usePosTerminalStore } from "./store";
import { usePosHotkeys } from "./use-pos-hotkeys";
import { posInputClass, posOutlineButtonClass, posPrimaryButtonClass } from "../pos-theme/theme";

function useDebouncedValue(value: string, delayMs: number): string {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const timeout = window.setTimeout(() => setDebouncedValue(value), delayMs);
    return () => window.clearTimeout(timeout);
  }, [delayMs, value]);

  return debouncedValue;
}

export function PosTerminalWorkspace() {
  const quantityInputRef = useRef<HTMLInputElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const scannerInputRef = useRef<HTMLInputElement>(null);
  const quantityFocusTargetRef = useRef<string | null>(null);
  const lastAutoFocusedGridKeyRef = useRef<string | null>(null);
  const [selectionError, setSelectionError] = useState<string | null>(null);
  const [scannerText, setScannerText] = useState("");
  const [pendingScannerCode, setPendingScannerCode] = useState<string | null>(null);
  const searchText = usePosTerminalStore((state) => state.searchText);
  const setSearchText = usePosTerminalStore((state) => state.setSearchText);
  const controlState = usePosTerminalStore((state) => state.controlState);
  const pendingSelection = usePosTerminalStore((state) => state.pendingSelection);
  const cartLines = usePosTerminalStore((state) => state.cartLines);
  const selectClass = usePosTerminalStore((state) => state.selectClass);
  const selectProduct = usePosTerminalStore((state) => state.selectProduct);
  const clearQuantity = usePosTerminalStore((state) => state.clearQuantity);
  const enterPaymentCapture = usePosTerminalStore((state) => state.enterPaymentCapture);
  const setQuantityText = usePosTerminalStore((state) => state.setQuantityText);
  const incrementPendingQuantity = usePosTerminalStore((state) => state.incrementPendingQuantity);
  const decrementPendingQuantity = usePosTerminalStore((state) => state.decrementPendingQuantity);
  const addPendingLine = usePosTerminalStore((state) => state.addPendingLine);
  const goBack = usePosTerminalStore((state) => state.goBack);
  const debouncedSearchText = useDebouncedValue(searchText, 180);
  const currentCatalogQuery = usePosCatalogQuery(
    controlState === CONTROL_STATE_CLASS_SELECTION || controlState === CONTROL_STATE_PAYMENT_CAPTURE
      ? debouncedSearchText
      : "",
  );
  const currentProductsQuery = usePosClassProductsQuery(
    pendingSelection?.productClass.id ?? null,
    controlState === CONTROL_STATE_PRODUCT_SELECTION ? debouncedSearchText : "",
  );

  useEffect(() => {
    setSelectionError(null);
  }, [controlState, pendingSelection]);

  useEffect(() => {
    if (
      controlState !== CONTROL_STATE_CLASS_SELECTION &&
      controlState !== CONTROL_STATE_PRODUCT_SELECTION
    ) {
      setPendingScannerCode(null);
    }
  }, [controlState]);

  const quantityCaptureFocusTarget = useMemo(() => {
    if (controlState !== CONTROL_STATE_QUANTITY_CAPTURE || pendingSelection === null) {
      return null;
    }

    return getPendingCaptureTargetKey(pendingSelection);
  }, [controlState, pendingSelection]);

  useEffect(() => {
    if (!quantityCaptureFocusTarget) {
      quantityFocusTargetRef.current = null;
      return;
    }

    if (quantityFocusTargetRef.current === quantityCaptureFocusTarget) {
      return;
    }

    quantityFocusTargetRef.current = quantityCaptureFocusTarget;
    quantityInputRef.current?.focus();
    quantityInputRef.current?.select();
  }, [quantityCaptureFocusTarget]);

  const sortedClasses = useMemo(
    () => sortCatalogClasses(currentCatalogQuery.data?.classes ?? []),
    [currentCatalogQuery.data?.classes],
  );
  const sortedProducts = useMemo(
    () => sortCatalogProducts(currentProductsQuery.data?.products ?? []),
    [currentProductsQuery.data?.products],
  );

  const isSelectionLoading =
    ((controlState === CONTROL_STATE_CLASS_SELECTION ||
      controlState === CONTROL_STATE_PAYMENT_CAPTURE) &&
      currentCatalogQuery.isPending) ||
    (controlState === CONTROL_STATE_PRODUCT_SELECTION && currentProductsQuery.isPending);
  const selectionLoadError =
    controlState === CONTROL_STATE_PRODUCT_SELECTION
      ? currentProductsQuery.error
      : currentCatalogQuery.error;
  const isSelectionDisabled = controlState === CONTROL_STATE_PAYMENT_CAPTURE;
  const showSearch =
    controlState === CONTROL_STATE_CLASS_SELECTION ||
    controlState === CONTROL_STATE_PRODUCT_SELECTION;
  const showStageBackAction =
    controlState === CONTROL_STATE_PRODUCT_SELECTION ||
    controlState === CONTROL_STATE_QUANTITY_CAPTURE;

  const flowActiveStepKey = useMemo(() => {
    if (controlState === CONTROL_STATE_PRODUCT_SELECTION) {
      return "product";
    }

    if (controlState === CONTROL_STATE_QUANTITY_CAPTURE) {
      return "quantity";
    }

    if (controlState === CONTROL_STATE_PAYMENT_CAPTURE) {
      return "payment";
    }

    return "class";
  }, [controlState]);

  const classGridFocus = useRovingFocusGrid({
    itemCount: sortedClasses.length,
    onActivate: (index) => {
      const productClass = sortedClasses[index];
      if (productClass && !isSelectionDisabled) {
        selectClass(productClass);
      }
    },
  });
  const productGridFocus = useRovingFocusGrid({
    itemCount: sortedProducts.length,
    onActivate: (index) => {
      const product = sortedProducts[index];
      if (product) {
        selectProduct(product);
      }
    },
  });
  const {
    activeIndex: classActiveIndex,
    focusIndex: focusClassIndex,
    getItemProps: getClassItemProps,
  } = classGridFocus;
  const {
    activeIndex: productActiveIndex,
    focusIndex: focusProductIndex,
    getItemProps: getProductItemProps,
  } = productGridFocus;

  const activeGridKey = useMemo(() => {
    if (controlState === CONTROL_STATE_CLASS_SELECTION) {
      return "classes";
    }

    if (controlState === CONTROL_STATE_PRODUCT_SELECTION && pendingSelection !== null) {
      return `products:${pendingSelection.productClass.id}`;
    }

    return null;
  }, [controlState, pendingSelection]);

  useEffect(() => {
    if (activeGridKey === null) {
      lastAutoFocusedGridKeyRef.current = null;
    }
  }, [activeGridKey]);

  useEffect(() => {
    if (isSelectionLoading || selectionLoadError || activeGridKey === null) {
      return;
    }

    if (lastAutoFocusedGridKeyRef.current === activeGridKey) {
      return;
    }

    if (controlState === CONTROL_STATE_CLASS_SELECTION) {
      if (sortedClasses.length > 0) {
        lastAutoFocusedGridKeyRef.current = activeGridKey;
        focusClassIndex(0);
      }
      return;
    }

    if (controlState === CONTROL_STATE_PRODUCT_SELECTION && sortedProducts.length > 0) {
      lastAutoFocusedGridKeyRef.current = activeGridKey;
      focusProductIndex(0);
    }
  }, [
    activeGridKey,
    controlState,
    focusClassIndex,
    focusProductIndex,
    isSelectionLoading,
    selectionLoadError,
    sortedClasses.length,
    sortedProducts.length,
  ]);

  const selectionKeyboardHint =
    isSelectionDisabled
      ? "Seleccion bloqueada mientras capturas el cobro."
      : controlState === CONTROL_STATE_PRODUCT_SELECTION
        ? "Enter: seleccionar · .+Enter: cobrar · Esc: volver"
        : "Enter: seleccionar · .+Enter: cobrar · Esc: cancelar";

  useEffect(() => {
    if (pendingScannerCode === null || isSelectionLoading || selectionLoadError) {
      return;
    }

    if (controlState === CONTROL_STATE_CLASS_SELECTION) {
      const exactClassMatch = sortedClasses.find((productClass) =>
        matchesScannerValue(productClass.code, pendingScannerCode),
      );

      if (exactClassMatch) {
        setPendingScannerCode(null);
        selectClass(exactClassMatch);
        return;
      }

      if (sortedClasses.length === 1) {
        selectClass(sortedClasses[0]!);
      }
      return;
    }

    if (controlState === CONTROL_STATE_PRODUCT_SELECTION) {
      const exactProductMatch = sortedProducts.find((product) =>
        matchesScannerValue(product.code, pendingScannerCode),
      );

      if (exactProductMatch) {
        setPendingScannerCode(null);
        selectProduct(exactProductMatch);
        return;
      }

      if (sortedProducts.length === 1) {
        setPendingScannerCode(null);
        selectProduct(sortedProducts[0]!);
      }
    }
  }, [
    controlState,
    isSelectionLoading,
    pendingScannerCode,
    selectClass,
    selectProduct,
    selectionLoadError,
    sortedClasses,
    sortedProducts,
  ]);

  function handleScannerSubmit() {
    const scannedCode = parseProductScannerValue(scannerText);
    if (scannedCode === null) {
      setSelectionError("No se pudo interpretar el codigo escaneado.");
      return;
    }

    setSelectionError(null);
    setScannerText("");
    setPendingScannerCode(scannedCode);
    setSearchText(scannedCode);
  }

  function handleAddLine() {
    if (pendingSelection !== null && !hasCapturedQuantity(pendingSelection.quantityText)) {
      setSelectionError("Ingresa una cantidad valida antes de agregar la linea.");
      return;
    }

    try {
      addPendingLine();
      setSelectionError(null);
    } catch (error) {
      setSelectionError(
        toOperationalErrorMessage(
          error,
          "Confirma la seleccion y la cantidad antes de agregar la linea.",
        ),
      );
    }
  }

  const quantityPresets = ["1", "2", "3", "6", "12"];
  const ticketLineSummary =
    cartLines.length === 0
      ? null
      : `${cartLines.length} ${cartLines.length === 1 ? "linea" : "lineas"} en ticket`;
  const isQuantityReady =
    pendingSelection !== null && hasCapturedQuantity(pendingSelection.quantityText);
  const isQuantityPending =
    pendingSelection !== null && !hasCapturedQuantity(pendingSelection.quantityText);
  const quantityActionLabel =
    pendingSelection?.editingLine !== null ? "Guardar cantidad" : "Agregar";

  usePosHotkeys({
    cartLineCount: cartLines.length,
    controlState,
    enterPaymentCapture,
    focusSearch: () => {
      searchInputRef.current?.focus();
      searchInputRef.current?.select();
    },
    goBack,
    onBlockedPaymentCapture: (message) => {
      setSelectionError(message);
    },
    searchText,
    selectClass,
    selectProduct,
    setQuantityText,
    setSearchText,
    showSearch,
    sortedClasses,
    sortedProducts,
  });

  return (
    <div className="grid gap-2.5 lg:h-full lg:grid-rows-[minmax(0,1fr)_auto]">
      <CentralWorkspaceSheet
        className="lg:h-full"
        contentClassName="min-h-0 overflow-y-auto px-3 pb-3 pt-2"
        header={
          <CompactPageHeader
            secondaryChips={
              ticketLineSummary ? (
                <ModuleStateChip tone="muted">{ticketLineSummary}</ModuleStateChip>
              ) : null
            }
            stateChip={
              <ModuleStateChip tone={cartLines.length > 0 ? "primary" : "muted"}>
                {cartLines.length > 0 ? "En construccion" : "Ticket vacio"}
              </ModuleStateChip>
            }
            title="Punto de venta"
          >
            <FlowGuide
              activeStepKey={flowActiveStepKey}
              steps={[
                {
                  icon: <StoreIcon className="h-3.5 w-3.5" />,
                  key: "class",
                  label: "Clase",
                },
                {
                  icon: <PackageIcon className="h-3.5 w-3.5" />,
                  key: "product",
                  label: "Producto",
                },
                {
                  icon: <HashIcon className="h-3.5 w-3.5" />,
                  key: "quantity",
                  label: "Cantidad",
                },
                {
                  icon: <MoneyIcon className="h-3.5 w-3.5" />,
                  key: "payment",
                  label: "Cobro",
                },
              ]}
              variant="process"
            />
          </CompactPageHeader>
        }
        toolbar={
          showStageBackAction || showSearch ? (
            <div className="grid w-full gap-3">
              <div className="flex min-w-0 flex-wrap items-start justify-between gap-3">
                <div className="flex min-w-0 items-center gap-3">
                  {showStageBackAction ? (
                    <Button
                      aria-label="Regresar"
                      className={cn("h-10 px-3", posOutlineButtonClass)}
                      onClick={goBack}
                      title="Regresar"
                      type="button"
                    >
                      <ArrowLeftIcon className="h-4 w-4" />
                    </Button>
                  ) : null}
                </div>

                {showSearch ? (
                  <div className="flex min-w-0 flex-1 justify-end">
                    <SearchField
                      ariaLabel="Buscar en la etapa actual"
                      className="w-full max-w-sm"
                      disabled={isSelectionDisabled}
                      inputClassName={cn("h-9 rounded-lg text-sm shadow-sm", posInputClass)}
                      inputRef={searchInputRef}
                      onChange={(value) => {
                        setPendingScannerCode(null);
                        setSelectionError(null);
                        setSearchText(value);
                      }}
                      placeholder={
                        controlState === CONTROL_STATE_PRODUCT_SELECTION
                          ? "Filtrar producto"
                          : "Filtrar clase"
                      }
                      value={searchText}
                    />
                  </div>
                ) : null}
              </div>

              {showSearch ? (
                <PosScannerInput
                  ariaLabel={
                    controlState === CONTROL_STATE_PRODUCT_SELECTION
                      ? "Escanear codigo de producto"
                      : "Escanear codigo de producto o clase"
                  }
                  description="El escaner funciona como teclado y no interfiere con cantidad o cobro."
                  disabled={isSelectionDisabled}
                  inputRef={scannerInputRef}
                  modeLabel="Escaneo de producto"
                  onChange={setScannerText}
                  onSubmit={handleScannerSubmit}
                  placeholder={
                    controlState === CONTROL_STATE_PRODUCT_SELECTION
                      ? "Escanear producto"
                      : "Escanear producto o clase"
                  }
                  submitLabel="Aplicar codigo"
                  value={scannerText}
                />
              ) : null}
            </div>
          ) : undefined
        }
        toolbarClassName="py-2"
      >
        {isSelectionLoading ? (
          <OperationalStatus
            description="Cargando el catalogo operativo de este POS."
            title="Cargando seleccion"
          />
        ) : null}

        {!isSelectionLoading && selectionLoadError ? (
          <OperationalStatus
            action={
              <Button
                className={posPrimaryButtonClass}
                onClick={() =>
                  controlState === CONTROL_STATE_PRODUCT_SELECTION
                    ? currentProductsQuery.refetch()
                    : currentCatalogQuery.refetch()
                }
              >
                Reintentar
              </Button>
            }
            description={toOperationalErrorMessage(
              selectionLoadError,
              "Confirma el contexto de la estacion y la disponibilidad del catalogo.",
            )}
            title="La seleccion no esta disponible"
          />
        ) : null}

        {selectionError && controlState !== CONTROL_STATE_QUANTITY_CAPTURE ? (
          <div className="mb-2 flex items-start justify-between gap-3 rounded-lg border border-[var(--ui-color-danger-soft)] bg-[var(--ui-color-danger-soft)] px-3 py-2 text-sm text-[var(--ui-color-danger)]">
            <p className="leading-6">{selectionError}</p>
            <button
              aria-label="Cerrar error"
              className="flex h-8 w-8 items-center justify-center rounded-full text-[var(--ui-color-danger)] transition hover:bg-[var(--ui-color-danger-soft)] hover:text-[var(--ui-color-danger)]"
              onClick={() => setSelectionError(null)}
              type="button"
            >
              <XIcon className="h-4 w-4" />
            </button>
          </div>
        ) : null}

          {!isSelectionLoading &&
          !selectionLoadError &&
          (controlState === CONTROL_STATE_CLASS_SELECTION ||
            controlState === CONTROL_STATE_PAYMENT_CAPTURE) ? (
            sortedClasses.length > 0 ? (
              <div className="grid gap-2.5">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="text-xs font-medium text-slate-500">{selectionKeyboardHint}</p>
                </div>
                <div className="grid gap-2.5 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
                  {sortedClasses.map((productClass, index) => {
                    const itemProps = getClassItemProps(index);

                    return (
                      <CatalogSelectionCard
                        buttonRef={itemProps.ref}
                        code={productClass.code}
                        isActive={classActiveIndex === index}
                        isDisabled={isSelectionDisabled}
                        key={productClass.id}
                        name={productClass.name}
                        onCardFocus={itemProps.onFocus}
                        onCardKeyDown={itemProps.onKeyDown}
                        onSelect={() => selectClass(productClass)}
                        priceText={
                          productClass.capture_mode_default === CLASS_CAPTURE_MODE
                            ? productClass.class_capture_unit_price
                            : null
                        }
                        shortcutLabel={getSelectionShortcutLabel(index)}
                        tabIndex={itemProps.tabIndex}
                        variant="pos"
                      />
                    );
                  })}
                </div>
              </div>
            ) : (
              <div className="rounded-xl border border-dashed border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-4 py-8 text-center text-sm text-slate-600">
                No hay clases para la busqueda actual.
              </div>
            )
          ) : null}

          {!isSelectionLoading &&
          !selectionLoadError &&
          controlState === CONTROL_STATE_PRODUCT_SELECTION ? (
            sortedProducts.length > 0 ? (
              <div className="grid gap-2.5">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
                    <span className="font-medium text-slate-700">
                      {pendingSelection?.productClass.name}
                    </span>
                  </div>
                  <p className="text-xs font-medium text-slate-500">{selectionKeyboardHint}</p>
                </div>
                <div className="grid gap-2.5 sm:grid-cols-2 xl:grid-cols-3">
                  {sortedProducts.map((product, index) => {
                    const itemProps = getProductItemProps(index);

                    return (
                      <CatalogSelectionCard
                        buttonRef={itemProps.ref}
                        code={product.code}
                        isActive={productActiveIndex === index}
                        key={product.id}
                        name={product.name}
                        onCardFocus={itemProps.onFocus}
                        onCardKeyDown={itemProps.onKeyDown}
                        onSelect={() => selectProduct(product)}
                        priceText={product.unit_price}
                        shortcutLabel={getSelectionShortcutLabel(index)}
                        tabIndex={itemProps.tabIndex}
                        variant="pos"
                      />
                    );
                  })}
                </div>
              </div>
            ) : (
              <div className="rounded-xl border border-dashed border-[var(--pos-shell-border)] bg-[var(--pos-shell-muted)] px-4 py-8 text-center text-sm text-slate-600">
                No hay productos para esta busqueda.
              </div>
            )
          ) : null}

          {controlState === CONTROL_STATE_QUANTITY_CAPTURE && pendingSelection ? (
            <div className="w-full max-w-5xl justify-self-center rounded-xl border border-[var(--pos-shell-border)] bg-white p-3 shadow-sm">
              <div className="grid gap-3 lg:grid-cols-[12rem_minmax(0,1fr)]">
                <CatalogVisual
                  className="min-h-[11.5rem]"
                  code={
                    pendingSelection.captureMode === PRODUCT_DIRECT_MODE
                      ? pendingSelection.product?.code ?? pendingSelection.productClass.code
                      : pendingSelection.productClass.code
                  }
                  name={
                    pendingSelection.captureMode === PRODUCT_DIRECT_MODE
                      ? pendingSelection.product?.name ?? pendingSelection.productClass.name
                      : pendingSelection.productClass.name
                  }
                />

                <div className="grid gap-2.5">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="text-base font-semibold text-slate-950">
                          {pendingSelection.captureMode === PRODUCT_DIRECT_MODE
                            ? pendingSelection.product?.name
                            : pendingSelection.productClass.name}
                        </p>
                        {isQuantityPending ? (
                          <span className="pos-chip" data-tone="warning">
                            Pendiente
                          </span>
                        ) : null}
                      </div>
                      <p className="mt-1 text-sm text-slate-600">
                        {pendingSelection.captureMode === PRODUCT_DIRECT_MODE
                          ? pendingSelection.productClass.name
                          : "Confirma la cantidad y agrega la linea al ticket."}
                      </p>
                    </div>
                  </div>

                  <div className="grid gap-2">
                    <input
                      aria-label="Cantidad"
                      className={cn(
                        "h-16 rounded-xl px-4 text-[2.25rem] font-semibold tracking-tight shadow-sm",
                        posInputClass,
                      )}
                      inputMode="decimal"
                      onChange={(event) => setQuantityText(event.target.value)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter" || event.key === "NumpadEnter") {
                          event.preventDefault();
                          handleAddLine();
                        }

                        if (event.key === "Escape") {
                          event.preventDefault();
                          goBack();
                        }

                        if (event.key === "Delete") {
                          event.preventDefault();
                          clearQuantity();
                          setSelectionError(null);
                        }
                      }}
                      placeholder="0"
                      ref={quantityInputRef}
                      value={pendingSelection.quantityText}
                    />
                    <div className="flex flex-wrap items-center gap-2">
                      <div className="flex items-center gap-2">
                        <Button
                          className={cn("h-10 px-3", posOutlineButtonClass)}
                          onClick={decrementPendingQuantity}
                          type="button"
                        >
                          -1
                        </Button>
                        <Button
                          className={cn("h-10 px-3", posOutlineButtonClass)}
                          onClick={incrementPendingQuantity}
                          type="button"
                        >
                          +1
                        </Button>
                      </div>

                      <div className="flex flex-wrap items-center gap-2">
                        {quantityPresets.map((preset) => (
                          <Button
                            className={cn("h-10 min-w-12 px-3", posOutlineButtonClass)}
                            key={preset}
                            onClick={() => setQuantityText(preset)}
                            type="button"
                          >
                            {preset}
                          </Button>
                        ))}
                      </div>
                    </div>
                    <p className="text-xs font-medium text-slate-500">
                      Enter: agregar · Esc: volver · Alt+1/2/3/6: rapido
                    </p>
                    <div className="flex flex-wrap items-center justify-end gap-3">
                      <Button
                        className={cn("h-10 px-4", posPrimaryButtonClass)}
                        disabled={!isQuantityReady}
                        onClick={handleAddLine}
                        type="button"
                      >
                        {quantityActionLabel}
                      </Button>
                    </div>
                    {selectionError ? (
                      <div className="flex items-start justify-between gap-3 rounded-lg border border-[var(--ui-color-danger-soft)] bg-[var(--ui-color-danger-soft)] px-3 py-2 text-sm text-[var(--ui-color-danger)]">
                        <p className="leading-6">{selectionError}</p>
                        <button
                          aria-label="Cerrar error"
                          className="flex h-8 w-8 items-center justify-center rounded-full text-[var(--ui-color-danger)] transition hover:bg-[var(--ui-color-danger-soft)] hover:text-[var(--ui-color-danger)]"
                          onClick={() => setSelectionError(null)}
                          type="button"
                        >
                          <XIcon className="h-4 w-4" />
                        </button>
                      </div>
                    ) : null}
                  </div>
                </div>
              </div>
            </div>
          ) : null}
      </CentralWorkspaceSheet>

      {cartLines.length > 0 ? (
        <section className="rounded-xl border border-[var(--pos-shell-border)] bg-[var(--pos-shell-surface)] px-4 py-3 shadow-sm lg:hidden">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-sm font-medium text-slate-900">Ticket actual</p>
              <p className="text-sm text-slate-600">{cartLines.length} lineas listas para cobrar.</p>
            </div>
            <span className="pos-chip" data-tone="primary">
              Cobro
            </span>
          </div>
        </section>
      ) : null}
    </div>
  );
}


