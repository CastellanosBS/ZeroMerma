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
): void {
  printWindow.document.open();
  printWindow.document.write(documentHtml);
  printWindow.document.close();

  // Keep adapter errors in the caller's exception boundary. The browser waits for
  // document loading itself; a delayed timer would report success before failure.
  printWindow.focus();
  printWindow.print();
}
