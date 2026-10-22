"use server"
// import { logout } from "@/app/lib/session"
import { cookies } from "next/headers"
import { redirect } from "next/navigation"

const LogoutPage = async () => {
  const cookieStore = await cookies()
  const session = cookieStore.get("session")

  if (!session) {
    redirect("/")
  }

  const token = session.value
  cookieStore.delete("session")

  try {
    fetch("http://127.0.0.1:8000/auth/logout", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${token}`
      }
    })
  } catch { }

  redirect("/")

  return <></>
}

export default LogoutPage
