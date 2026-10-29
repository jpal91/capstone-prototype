"use client";

import { useActionState, useState } from "react";

import { grantAccess, type GrantFormState } from "@/app/actions/grants";
import type { components } from "@/app/lib/core/schema";

type Lender = components["schemas"]["LenderResponse"];

const EXPIRY_DAYS = [7, 30, 90];

type ShareFormProps = {
  versionId: number;
  versionNumber: number;
  // null when the lenders couldn't be loaded.
  lenders: Lender[] | null;
  // Lenders that already have an active grant for this version.
  activeLenderIds: number[];
};

const ShareForm = ({
  versionId,
  versionNumber,
  lenders,
  activeLenderIds,
}: ShareFormProps) => {
  const [state, formAction, pending] = useActionState<GrantFormState, FormData>(
    grantAccess,
    { status: "idle" },
  );
  // Controlled only so the consent text can name the lender.
  const [lenderId, setLenderId] = useState("");
  const [days, setDays] = useState("30");

  if (lenders === null) {
    return (
      <p className="text-sm text-error">Lenders couldn&apos;t be loaded.</p>
    );
  }

  const lenderName = lenders.find((l) => String(l.id) === lenderId)?.name;
  const errors = state.status === "error" ? (state.fieldErrors ?? {}) : {};

  return (
    <details className="collapse collapse-arrow border border-base-300">
      <summary className="collapse-title text-sm font-semibold">
        Share with a lender
      </summary>
      <form
        action={formAction}
        className="collapse-content flex flex-col gap-3"
      >
        <input type="hidden" name="versionId" value={versionId} />

        <div className="grid gap-3 sm:grid-cols-2">
          <label className="flex flex-col gap-1">
            <span className="text-sm font-medium">Lender</span>
            <select
              name="lenderId"
              value={lenderId}
              onChange={(e) => setLenderId(e.target.value)}
              className={`select select-sm w-full ${errors.lenderId ? "select-error" : ""}`}
              required
            >
              <option value="" disabled>
                Choose a lender
              </option>
              {lenders.map((l) => (
                <option
                  key={l.id}
                  value={l.id}
                  disabled={activeLenderIds.includes(l.id)}
                >
                  {l.name}
                  {activeLenderIds.includes(l.id) ? " (already shared)" : ""}
                </option>
              ))}
            </select>
            {errors.lenderId && (
              <span className="text-xs text-error">{errors.lenderId}</span>
            )}
          </label>

          <label className="flex flex-col gap-1">
            <span className="text-sm font-medium">Access for</span>
            <select
              name="expiresInDays"
              value={days}
              onChange={(e) => setDays(e.target.value)}
              className={`select select-sm w-full ${errors.expiresInDays ? "select-error" : ""}`}
            >
              {EXPIRY_DAYS.map((d) => (
                <option key={d} value={d}>
                  {d} days
                </option>
              ))}
            </select>
            {errors.expiresInDays && (
              <span className="text-xs text-error">{errors.expiresInDays}</span>
            )}
          </label>
        </div>

        {/* What the borrower is agreeing to, in plain words (FR-05, L-01). */}
        <p className="text-xs opacity-70">
          {lenderName ?? "The lender"} will be able to download version{" "}
          {versionNumber} of your pre-application, everything in it, for {days}{" "}
          days. You can revoke access at any time, but a copy the lender has
          already downloaded can&apos;t be recalled.
        </p>

        <div className="flex flex-wrap items-center justify-end gap-3">
          <div role="status" className="mr-auto text-sm">
            {state.status === "error" && (
              <span className="text-error">{state.message}</span>
            )}
            {state.status === "created" && (
              <span className="text-success">
                Shared with {state.grant.lenderName}.
              </span>
            )}
          </div>
          <button
            type="submit"
            className="btn btn-primary btn-sm"
            disabled={pending || !lenderId}
          >
            {pending && <span className="loading loading-spinner loading-xs" />}
            Share version {versionNumber}
          </button>
        </div>
      </form>
    </details>
  );
};

export default ShareForm;
