import type { ComponentType, SVGProps } from "react";

import {
  BagIcon,
  CheckCircleIcon,
  ClipboardIcon,
  InboxIcon,
  MoneyIcon,
  PencilSquareIcon,
  PrinterIcon,
  RotateCcwIcon,
  StoreIcon,
  TrashIcon,
  TruckIcon,
} from "../../components/pos-icons";

export type PosModuleKey =
  | "pos"
  | "passToCounter"
  | "sendToBranch"
  | "receiveTransfer"
  | "orders"
  | "tickets"
  | "returns"
  | "corrections"
  | "waste"
  | "payments"
  | "discounts"
  | "shiftClose";

export interface PosModuleDefinition {
  description: string;
  icon: ComponentType<SVGProps<SVGSVGElement>>;
  key: PosModuleKey;
  label: string;
  navigationShortcut: string;
  path: string;
  shortLabel: string;
}

export const posModules: PosModuleDefinition[] = [
  {
    key: "pos",
    label: "POS",
    navigationShortcut: "Ctrl+Alt+P",
    shortLabel: "POS",
    icon: BagIcon,
    path: "/pos",
    description: "Consola principal de venta con caja activa.",
  },
  {
    key: "passToCounter",
    label: "Pasar a mostrador",
    navigationShortcut: "Ctrl+Alt+M",
    shortLabel: "PM",
    icon: StoreIcon,
    path: "/pasar-a-mostrador",
    description: "Movimiento operativo del fondo al mostrador.",
  },
  {
    key: "sendToBranch",
    label: "Enviar a sucursal",
    navigationShortcut: "Ctrl+Alt+S",
    shortLabel: "ES",
    icon: TruckIcon,
    path: "/enviar-a-sucursal",
    description: "Salida fisica de producto hacia otra sucursal.",
  },
  {
    key: "receiveTransfer",
    label: "Recibir envio",
    navigationShortcut: "Ctrl+Alt+R",
    shortLabel: "RE",
    icon: InboxIcon,
    path: "/recibir-envio",
    description: "Recepcion de envios pendientes para la sucursal.",
  },
  {
    key: "orders",
    label: "Pedidos",
    navigationShortcut: "Ctrl+Alt+O",
    shortLabel: "PE",
    icon: ClipboardIcon,
    path: "/pedidos",
    description: "Captura, consulta y entrega de pedidos.",
  },
  {
    key: "tickets",
    label: "Tickets",
    navigationShortcut: "Ctrl+Alt+T",
    shortLabel: "TI",
    icon: PrinterIcon,
    path: "/tickets",
    description: "Consulta y reimpresion de tickets.",
  },
  {
    key: "returns",
    label: "Devoluciones",
    navigationShortcut: "Ctrl+Alt+D",
    shortLabel: "DE",
    icon: RotateCcwIcon,
    path: "/devoluciones",
    description: "Registro de devoluciones con trazabilidad.",
  },
  {
    key: "corrections",
    label: "Ajustes",
    navigationShortcut: "Ctrl+Alt+C",
    shortLabel: "AJ",
    icon: PencilSquareIcon,
    path: "/correcciones",
    description: "Ajustes auditados sobre documentos operativos ya confirmados.",
  },
  {
    key: "waste",
    label: "Registrar merma",
    navigationShortcut: "Ctrl+Alt+W",
    shortLabel: "ME",
    icon: TrashIcon,
    path: "/registrar-merma",
    description: "Registro de merma para trazabilidad operativa.",
  },
  {
    key: "payments",
    label: "Pagos",
    navigationShortcut: "Ctrl+Alt+G",
    shortLabel: "PA",
    icon: MoneyIcon,
    path: "/pagos",
    description: "Registro de egresos operativos del turno.",
  },
  {
    key: "shiftClose",
    label: "Cerrar turno",
    navigationShortcut: "Ctrl+Alt+L",
    shortLabel: "CT",
    icon: CheckCircleIcon,
    path: "/cerrar-turno",
    description: "Cierre de turno y conciliacion de caja.",
  },
];

const moduleMap = new Map(posModules.map((module) => [module.key, module]));

export function getPosModuleByKey(key: PosModuleKey): PosModuleDefinition {
  const module = moduleMap.get(key);

  if (!module) {
    throw new Error(`POS module ${key} is not registered.`);
  }

  return module;
}

export function resolveActivePosModule(pathname: string): PosModuleDefinition {
  if (pathname === "/" || pathname === "/cash-session/open" || pathname.startsWith("/pos")) {
    return getPosModuleByKey("pos");
  }

  const matchedModule = posModules.find((module) => module.path === pathname);
  return matchedModule ?? getPosModuleByKey("pos");
}
