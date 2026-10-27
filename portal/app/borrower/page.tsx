import { redirect } from "next/navigation"
import { requireSession } from "@/app/lib/session"
import { getDraft, getGrants, getVersions } from "@/app/lib/utils"

import VersionCard from "@/app/components/VersionCard"
import Link from "next/link"

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
      <div className="w-full flex justify-between items-center border-2 rounded-xl bg-base-200 p-10">
        <div className="text-2xl font-bold">
          {draftRes?.lastModified ? "Resume Draft" : "Start a New Draft"}
        </div>
        <Link href="/" className="btn lg:btn-lg">
          {draftRes?.lastModified ? "Resume" : "Start"}
        </Link>
      </div>
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
