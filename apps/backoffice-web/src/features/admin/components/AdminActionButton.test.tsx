import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { authorizationUser } from "../../../test-support/authorization";
import { BackofficeAuthorizationContext } from "../../auth/authorization-context";
import { AdminActionButton } from "./AdminActionButton";

describe("administrative action presentation", () => {
  it("keeps a branch read-only when the actor manages another branch", () => {
    const user = authorizationUser([
      { capability: "inventory.view", scope_type: "GLOBAL", branch_ids: [] },
      { capability: "inventory.adjust", scope_type: "BRANCH_SET", branch_ids: ["north"] },
    ]);
    const button = (branch: string, disabled = false) =>
      renderToStaticMarkup(
        <BackofficeAuthorizationContext.Provider value={user}>
          <AdminActionButton capability="inventory.adjust" branchIds={[branch]} disabled={disabled}>
            Adjust
          </AdminActionButton>
        </BackofficeAuthorizationContext.Provider>,
      );
    expect(button("south")).toContain('disabled=""');
    expect(button("north")).not.toContain('disabled=""');
    expect(button("north", true)).toContain('disabled=""');
  });

  it("never turns viewing a report into permission to export it", () => {
    const markup = renderToStaticMarkup(
      <BackofficeAuthorizationContext.Provider
        value={authorizationUser([
          { capability: "reports.view", scope_type: "GLOBAL", branch_ids: [] },
        ])}
      >
        <AdminActionButton capability="reports.export">Export</AdminActionButton>
      </BackofficeAuthorizationContext.Provider>,
    );
    expect(markup).toContain('disabled=""');
  });
});
