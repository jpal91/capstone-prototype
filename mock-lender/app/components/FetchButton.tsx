"use client";

import { useActionState } from "react";

import {
  fetchApplicationAction,
  type FetchApplicationFormState,
} from "@/app/actions/lender";

// Offered on ended grants too: core answers with the same 404 as for any
// other denial, and records the real reason in its audit log.
const FetchButton = ({
  clientId,
  grantId,
}: {
  clientId: string;
  grantId: number;
}) => {
  const [state, formAction, pending] = useActionState<
    FetchApplicationFormState,
    FormData
  >(fetchApplicationAction, { status: "idle" });

  return (
    <form action={formAction} className="flex flex-col items-start gap-1">
      <input type="hidden" name="clientId" value={clientId} />
      <input type="hidden" name="grantId" value={grantId} />
      <button
        type="submit"
        className="btn btn-outline btn-xs"
        disabled={pending}
      >
        {pending && <span className="loading loading-spinner loading-xs" />}
        Fetch
      </button>
      <div role="status" className="text-xs">
        {state.status === "success" && (
          <span className="text-success">Fetched, hash verified</span>
        )}
        {state.status === "ended" && (
          <span className="opacity-70">{state.message}</span>
        )}
        {(state.status === "error" || state.status === "unknown_grant") && (
          <span className="text-error">{state.message}</span>
        )}
      </div>
    </form>
  );
};

export default FetchButton;
