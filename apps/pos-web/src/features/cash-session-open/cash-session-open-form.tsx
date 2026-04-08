import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "../../components/ui/button";
import type { PosBootstrapResponse } from "../../lib/api-contracts";
import { formatLocalDateTime } from "../../lib/formatters";

const openCashSessionSchema = z.object({
  openingAmount: z
    .string()
    .trim()
    .min(1, "Enter the opening amount.")
    .regex(/^\d+(\.\d{1,2})?$/, "Use digits with up to two decimals."),
});

type OpenCashSessionFormValues = z.infer<typeof openCashSessionSchema>;

export function CashSessionOpenForm({
  bootstrap,
  errorMessage,
  isSubmitDisabled,
  onSubmit,
}: {
  bootstrap: PosBootstrapResponse;
  errorMessage?: string;
  isSubmitDisabled: boolean;
  onSubmit: (values: OpenCashSessionFormValues) => Promise<void>;
}) {
  const {
    formState: { errors, isSubmitting },
    handleSubmit,
    register,
  } = useForm<OpenCashSessionFormValues>({
    defaultValues: {
      openingAmount: "",
    },
    resolver: zodResolver(openCashSessionSchema),
  });

  return (
    <section className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
      <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <p className="text-sm font-medium uppercase tracking-wide text-green-800">
          Cash session opening
        </p>
        <h1 className="mt-2 text-3xl font-semibold text-slate-950">Open the register</h1>
        <p className="mt-4 text-sm leading-6 text-slate-700">
          Confirm the workstation context and record the opening amount before operating.
        </p>

        <dl className="mt-8 grid gap-4 sm:grid-cols-2">
          <div>
            <dt className="text-sm font-medium text-slate-600">Branch</dt>
            <dd className="mt-1 text-lg font-semibold text-slate-950">{bootstrap.branch.name}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-slate-600">Workstation</dt>
            <dd className="mt-1 text-lg font-semibold text-slate-950">
              {bootstrap.workstation.name}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-slate-600">Operator</dt>
            <dd className="mt-1 text-lg font-semibold text-slate-950">{bootstrap.user.full_name}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-slate-600">Local date and time</dt>
            <dd className="mt-1 text-lg font-semibold text-slate-950">
              {formatLocalDateTime(bootstrap.local_timestamp, bootstrap.branch.timezone)}
            </dd>
          </div>
        </dl>
      </div>

      <aside className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <form
          className="grid gap-4"
          onSubmit={handleSubmit(async (values) => {
            await onSubmit(values);
          })}
        >
          <div className="grid gap-2">
            <label className="text-sm font-medium text-slate-800" htmlFor="opening-amount">
              Opening amount
            </label>
            <input
              {...register("openingAmount")}
              className="h-12 rounded-md border border-slate-300 px-3 text-base text-slate-950 outline-none transition focus:border-green-700 focus:ring-2 focus:ring-green-700/20"
              id="opening-amount"
              inputMode="decimal"
              placeholder="0.00"
            />
            {errors.openingAmount ? (
              <span className="text-sm text-rose-700">{errors.openingAmount.message}</span>
            ) : (
              <span className="text-sm text-slate-600">
                Record the counted amount before the first sale.
              </span>
            )}
          </div>

          {errorMessage ? (
            <div className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800">
              {errorMessage}
            </div>
          ) : null}

          <Button
            className="h-12 w-full"
            disabled={isSubmitting || isSubmitDisabled}
            type="submit"
          >
            {isSubmitting || isSubmitDisabled ? "Opening cash session..." : "Open cash session"}
          </Button>
        </form>
      </aside>
    </section>
  );
}
