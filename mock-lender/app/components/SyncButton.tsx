"use client";

import { useActionState } from "react";

import {
  syncGrantsAction,
  type SyncGrantFormState,
} from "@/app/actions/lender";

// Asks core which grants this lender currently has (GET /lender/grants),
// standing in for the notification that isn't built (FR-09).
const SyncButton = ({ clientId }: { clientId: string }) => {
  const [state, formAction, pending] = useActionState<
    SyncGrantFormState,
    FormData
  >(syncGrantsAction, { status: "idle" });

  return (
    <form action={formAction} className="flex flex-wrap items-center gap-3">
      <input type="hidden" name="clientId" value={clientId} />
      <button
        type="submit"
        className="btn btn-primary btn-sm"
        disabled={pending}
      >
        {pending && <span className="loading loading-spinner loading-xs" />}
        Check for applications
      </button>
      <div role="status" className="text-sm">
        {state.status === "error" && (
          <span className="text-error">{state.message}</span>
        )}
        {state.status === "success" && (
          <span className="opacity-70">
            {state.listed} listed · {state.added} new · {state.ended} ended
          </span>
        )}
      </div>
    </form>
  );
};

export default SyncButton;
