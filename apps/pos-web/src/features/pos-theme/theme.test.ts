import { describe, expect, it } from "vitest";

import type { PosBootstrapResponse } from "../../lib/api-contracts";
import {
  getPosBranchTheme,
  getPosButtonVariantClass,
  getPosStatusBadgeClass,
  posDangerButtonClass,
  posNeutralButtonClass,
  posSecondaryButtonClass,
} from "./theme";

const bootstrap: PosBootstrapResponse = {
  active_cash_session: null,
  branch: {
    code: "MAIN",
    id: "branch-main",
    is_active: true,
    name: "Main Branch",
    timezone: "America/Hermosillo",
  },
  local_timestamp: "2026-04-09T10:00:00Z",
  user: {
    email: "cashier@zeromerma.local",
    full_name: "Main Branch Cashier",
    id: "user-1",
    is_active: true,
  },
  workstation: {
    code: "POS-01",
    id: "workstation-1",
    is_active: true,
    name: "Front Register 01",
  },
};

describe("pos theme", () => {
  it("maps MAIN branch to EL_MEJOR_PAN", () => {
    expect(getPosBranchTheme(bootstrap).brandKey).toBe("EL_MEJOR_PAN");
  });

  it("exposes explicit POS button variants beyond the base shared button", () => {
    expect(getPosButtonVariantClass("secondary")).toBe(posSecondaryButtonClass);
    expect(getPosButtonVariantClass("neutral")).toBe(posNeutralButtonClass);
    expect(getPosButtonVariantClass("danger")).toBe(posDangerButtonClass);
  });

  it("builds explicit POS status badge classes", () => {
    expect(getPosStatusBadgeClass("ready")).toContain("pos-status-badge--ready");
    expect(getPosStatusBadgeClass("draft")).toContain("pos-status-badge--draft");
  });
});
