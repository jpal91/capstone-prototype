import Link from "next/link"

import type { components } from "@/app/lib/core/schema"
import { formatDateTime } from "./format"

type Draft = components["schemas"]["UrlaDraft-Output"]

type DraftCardProps = {
  // null when the draft couldn't be loaded.
  draft: Draft | null
  // From the Last-Modified header; null until the first save.
  lastModified: string | null
  // When the newest version was finalized; undefined if there's none (or it
  // couldn't be loaded).
  latestFinalizedAt: string | undefined
}

const currency = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
})

const Summary = ({ draft }: { draft: Draft }) => {
  const name = [draft.borrower?.firstName, draft.borrower?.lastName].filter(Boolean).join(" ")
  const { loanPurpose, loanAmount } = draft.loan ?? {}
  const place = [draft.subjectProperty?.city, draft.subjectProperty?.state].filter(Boolean).join(", ")

  return (
    <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-1 text-sm">
      <dt className="opacity-70">Borrower</dt>
      <dd>{name || "—"}</dd>
      <dt className="opacity-70">Loan</dt>
      <dd>
        {[loanPurpose, loanAmount && currency.format(Number(loanAmount))].filter(Boolean).join(" · ") || "—"}
      </dd>
      <dt className="opacity-70">Property</dt>
      <dd>{place || "—"}</dd>
    </dl>
  )
}

const DraftCard = ({ draft, lastModified, latestFinalizedAt }: DraftCardProps) => {
  const started = lastModified !== null
  // Last-Modified only has whole seconds, so a save in the same second as the
  // latest finalize isn't flagged. Finalizing doesn't touch the draft.
  const unfinalized =
    started &&
    (latestFinalizedAt === undefined || new Date(lastModified) > new Date(latestFinalizedAt))

  return (
    <div className="card card-border bg-base-100">
      <div className="card-body gap-4">
        <div className="flex items-center justify-between gap-2">
          <h2 className="card-title text-2xl">Your pre-application</h2>
          {unfinalized && <span className="badge badge-warning">Changes not finalized</span>}
        </div>

        {draft === null ? (
          <p className="text-sm text-error">Your draft couldn&apos;t be loaded. Try again.</p>
        ) : started ? (
          <>
            <Summary draft={draft} />
            <p className="text-xs opacity-70">Last saved {formatDateTime(lastModified)}</p>
          </>
        ) : (
          <p className="text-sm opacity-70">
            Fill it in once, then finalize it to create a version you can share with lenders.
          </p>
        )}

        {draft !== null && (
          <div className="card-actions justify-end">
            <Link href="/borrower/application" className="btn btn-primary">
              {started ? "Continue editing" : "Start"}
            </Link>
          </div>
        )}
      </div>
    </div>
  )
}

export default DraftCard
