"use client"

import Link from "next/link"
import { startTransition, useActionState, type FormEvent } from "react"

import { submitDraft, type SubmitDraftState } from "@/app/actions/draft-submit"
import type { components } from "@/app/lib/core/schema"
import { formatDateTime } from "../format"
import { ErrorsContext } from "./fields"
import {
  AssetsSection,
  BorrowerSection,
  CurrentAddressSection,
  IncomeSection,
  LiabilitiesSection,
  LoanSection,
  PropertySection,
} from "./sections"

type Draft = components["schemas"]["UrlaDraft-Output"]

const EMPTY: Record<string, string> = {}

const DraftForm = ({ draft }: { draft: Draft }) => {
  const [state, formAction, pending] = useActionState<SubmitDraftState, FormData>(
    submitDraft,
    { status: "idle" }
  )

  // React resets a form after every <form action> submission, which would
  // throw away what the user typed when a save fails. Calling the action
  // ourselves skips that reset; `action` stays as the no-JS fallback.
  const onSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)
    startTransition(() => formAction(formData))
  }

  const errors = state.status === "error" ? state.fieldErrors ?? EMPTY : EMPTY

  return (
    <ErrorsContext value={errors}>
      <form action={formAction} onSubmit={onSubmit} className="flex flex-col gap-8" noValidate>
        <BorrowerSection value={draft.borrower} />
        <CurrentAddressSection value={draft.address} />
        <IncomeSection value={draft.income} />
        <AssetsSection value={draft.assets} />
        <LiabilitiesSection value={draft.liabilities} />
        <LoanSection value={draft.loan} />
        <PropertySection value={draft.subjectProperty} />

        <div className="sticky bottom-0 -mx-2 flex flex-wrap items-center justify-end gap-4 border-t border-base-300 bg-base-100 px-2 py-4">
          <div role="status" className="mr-auto text-sm">
            {state.status === "error" && <span className="text-error">{state.message}</span>}
            {state.status === "saved" && <span className="text-success">Saved {formatDateTime(state.savedAt)}</span>}
          </div>
          <Link href="/borrower" className="btn btn-ghost">Back to dashboard</Link>
          <button type="submit" className="btn btn-primary" disabled={pending}>
            {pending && <span className="loading loading-spinner loading-sm" />}
            Save draft
          </button>
        </div>
      </form>
    </ErrorsContext>
  )
}

export default DraftForm
