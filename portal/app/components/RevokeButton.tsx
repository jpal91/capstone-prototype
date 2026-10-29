"use client";

import { useActionState, type MouseEvent } from "react";

import { revokeGrant, type GrantFormState } from "@/app/actions/grants";

const RevokeButton = ({
  grantId,
  lenderName,
}: {
  grantId: number;
  lenderName: string;
}) => {
  const [state, formAction, pending] = useActionState<GrantFormState, FormData>(
    revokeGrant,
    { status: "idle" },
  );

  // Revoking can't be undone (a new grant would be needed), so confirm first.
  const confirmRevoke = (e: MouseEvent<HTMLButtonElement>) => {
    if (
      !window.confirm(
        `Revoke ${lenderName}'s access? They won't be able to download this version again.`,
      )
    ) {
      e.preventDefault();
    }
  };

  return (
    <form action={formAction} className="flex items-center gap-2">
      <input type="hidden" name="id" value={grantId} />
      {state.status === "error" && (
        <span className="text-xs text-error">{state.message}</span>
      )}
      <button
        type="submit"
        onClick={confirmRevoke}
        className="btn btn-outline btn-error btn-xs"
        disabled={pending}
      >
        {pending && <span className="loading loading-spinner loading-xs" />}
        Revoke
      </button>
    </form>
  );
};

export default RevokeButton;
