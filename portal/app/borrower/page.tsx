import { redirect } from "next/navigation"
import { requireSession } from "@/app/lib/session"

const DashboardPage = async () => {
  const session = await requireSession()

  if (!session) {
    redirect("/login")
  }

  return <div></div>
}

export default DashboardPage
