export function openBrowserPrintWindow(options?: {
  height?: number;
  width?: number;
}): Window | null {
  const height = options?.height ?? 760;
  const width = options?.width ?? 480;

  return window.open("", "_blank", `width=${width},height=${height}`);
}

export function writePrintableDocument(
  printWindow: Window,
  documentHtml: string,
  options?: {
    printDelayMs?: number;
  },
): void {
  printWindow.document.open();
  printWindow.document.write(documentHtml);
  printWindow.document.close();

  const printDelayMs = options?.printDelayMs ?? 120;
  window.setTimeout(() => {
    printWindow.focus();
    printWindow.print();
  }, printDelayMs);
}
