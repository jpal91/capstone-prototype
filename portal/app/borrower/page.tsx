import { redirect } from "next/navigation"
import { requireSession } from "@/app/lib/session"
import { getDraft, getVersions } from "@/app/lib/utils"

import VersionCard from "@/app/components/VersionCard"
import Link from "next/link"

const DashboardPage = async () => {
  const session = await requireSession()

  if (!session) {
    redirect("/login")
  }

  const [versions, draftRes] = await Promise.all([getVersions(), getDraft()])


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
      <div className="w-full flex flex-col">
        <div className="text-5xl font-bold mb-12">Versions</div>
        <div className="flex gap-4 flex-wrap">
          {versions ? versions.map((v) => (
            <VersionCard
              key={v.id}
              sha256={v.sha256}
              createdAt={v.createdAt}
            />
          )) : <div>TODO</div>}
        </div>
      </div>
    </div>
  )
}

export default DashboardPage
