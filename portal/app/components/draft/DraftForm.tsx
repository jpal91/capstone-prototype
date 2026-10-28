"use client";

import Link from "next/link";
import {
  startTransition,
  useActionState,
  useEffect,
  useRef,
  useState,
  type FormEvent,
} from "react";

import {
  saveOrFinalizeDraft,
  type SubmitDraftState,
} from "@/app/actions/draft-submit";
import type { components } from "@/app/lib/core/schema";
import { formatDateTime } from "../format";
import { ErrorsContext } from "./fields";
import {
  AssetsSection,
  BorrowerSection,
  CurrentAddressSection,
  IncomeSection,
  LiabilitiesSection,
  LoanSection,
  PropertySection,
} from "./sections";

type Draft = components["schemas"]["UrlaDraft-Output"];
type Intent = "save" | "finalize";

const EMPTY: Record<string, string> = {};

const DraftForm = ({ draft }: { draft: Draft }) => {
  const [state, formAction, pending] = useActionState<
    SubmitDraftState,
    FormData
  >(saveOrFinalizeDraft, { status: "idle" });
  // Which button started the pending submission, for its spinner.
  const [intent, setIntent] = useState<Intent>("save");
  const formRef = useRef<HTMLFormElement>(null);

  // React resets a form after every <form action> submission, which would
  // throw away what the user typed when a save fails. Calling the action
  // ourselves skips that reset; `action` stays as the no-JS fallback.
  const onSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    // The submitter's name/value ("intent") is only included when passed in.
    const submitter = (e.nativeEvent as SubmitEvent).submitter;
    const formData = new FormData(e.currentTarget, submitter);
    setIntent(formData.get("intent") === "finalize" ? "finalize" : "save");
    startTransition(() => formAction(formData));
  };

  // The form is long: after a failed submit, bring the first error into view.
  useEffect(() => {
    if (state.status !== "error") return;
    const first = formRef.current?.querySelector<HTMLElement>(
      '[aria-invalid="true"], [role="alert"]',
    );
    first?.scrollIntoView({ block: "center" });
    if (first?.matches("input, select")) first.focus({ preventScroll: true });
  }, [state]);

  const errors =
    state.status === "error" ? (state.fieldErrors ?? EMPTY) : EMPTY;
  // Rules on the whole draft (e.g. a refinance needs the property address)
  // have an empty loc.
  const draftError = errors[""];

  return (
    <ErrorsContext value={errors}>
      <form
        ref={formRef}
        action={formAction}
        onSubmit={onSubmit}
        className="flex flex-col gap-8"
        noValidate
      >
        <BorrowerSection value={draft.borrower} />
        <CurrentAddressSection value={draft.address} />
        <IncomeSection value={draft.income} />
        <AssetsSection value={draft.assets} />
        <LiabilitiesSection value={draft.liabilities} />
        <LoanSection value={draft.loan} />
        <PropertySection value={draft.subjectProperty} />

        <div className="sticky bottom-0 -mx-2 flex flex-wrap items-center justify-end gap-4 border-t border-base-300 bg-base-100 px-2 py-4">
          <div role="status" className="mr-auto text-sm">
            {state.status === "error" && (
              <div className="text-error">
                {state.message}
                {draftError && <div>{draftError}</div>}
              </div>
            )}
            {state.status === "saved" && (
              <span className="text-success">
                Saved {formatDateTime(state.savedAt)}
              </span>
            )}
            {state.status === "finalized" && (
              <span className="text-success">
                Version {state.version.number} created.{" "}
                <Link href="/borrower" className="link">
                  Share it from the dashboard
                </Link>
              </span>
            )}
          </div>
          <Link href="/borrower" className="btn btn-ghost">
            Back to dashboard
          </Link>
          {/* Save comes first: pressing Enter in a field submits with the first button. */}
          <button
            type="submit"
            name="intent"
            value="save"
            className="btn"
            disabled={pending}
          >
            {pending && intent === "save" && (
              <span className="loading loading-spinner loading-sm" />
            )}
            Save draft
          </button>
          <button
            type="submit"
            name="intent"
            value="finalize"
            className="btn btn-primary"
            disabled={pending}
          >
            {pending && intent === "finalize" && (
              <span className="loading loading-spinner loading-sm" />
            )}
            Save and finalize
          </button>
        </div>
      </form>
    </ErrorsContext>
  );
};

export default DraftForm;
