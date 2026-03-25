import { RequireAuth } from "@/modules/auth/RequireAuth";
import { CashSessionOpenScreen } from "@/modules/pos/cash-session/CashSessionOpenScreen";

export default function PosCashSessionOpenPage() {
    return (
        <RequireAuth>
            <CashSessionOpenScreen />
        </RequireAuth>
    );
}
