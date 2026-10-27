import { redirect } from "next/navigation"
import { requireSession } from "@/app/lib/session"
import { getDraft, getGrants, getVersions } from "@/app/lib/utils"

import DraftCard from "@/app/components/DraftCard"
import VersionCard from "@/app/components/VersionCard"

const DashboardPage = async () => {
  const session = await requireSession()

  if (!session) {
    redirect("/login")
  }

  const [versions, draftRes, grants] = await Promise.all([getVersions(), getDraft(), getGrants()])

  // core lists versions oldest first.
  const newestFirst = versions?.toReversed()


  return (
    <div
      className="mx-auto w-full max-w-7xl flex flex-col p-8 mt-10 gap-20"
    >
      <DraftCard
        draft={draftRes?.draft ?? null}
        lastModified={draftRes?.lastModified ?? null}
        latestFinalizedAt={newestFirst?.[0]?.createdAt}
      />
      <section className="w-full flex flex-col">
        <h2 className="text-5xl font-bold mb-12">Finalized versions</h2>
        {newestFirst === undefined ? (
          <div role="alert" className="alert alert-error">Your versions couldn&apos;t be loaded. Try again.</div>
        ) : newestFirst.length === 0 ? (
          <p className="opacity-70">No finalized versions yet. Finalize your pre-application to create one you can share.</p>
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            {newestFirst.map((v, i) => (
              <VersionCard
                key={v.id}
                version={v}
                isLatest={i === 0}
                isOutdated={v.sha256 !== newestFirst[0].sha256}
                grants={grants?.filter((g) => g.versionId === v.id) ?? null}
              />
            ))}
          </div>
        )}
      </section>
    </div>
  )
}

export default DashboardPage
