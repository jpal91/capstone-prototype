"use server"
import { cookies } from 'next/headers'

export const requireSession = async () => {
  const cookieStore = await cookies()

  if (cookieStore.get("session")) {
    return true
  } else {
    return false
  }
}

export const getToken = async () => {
  const cookieStore = await cookies()
  const session = cookieStore.get("session")

  if (!session) return

  return session.value
}

export async function createSession(token: string) {
  const expiresAt = new Date(Date.now() + 24 * 60 * 60 * 1000)
  const cookieStore = await cookies()

  cookieStore.set('session', token, {
    httpOnly: true,
    secure: true,
    expires: expiresAt,
    sameSite: 'lax',
    path: '/',
  })
}

export const logout = async () => {
  const cookieStore = await cookies()
  const session = cookieStore.get("session")

  if (!session) {
    // redirect("/")
    return
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
  } catch {}

  // redirect("/")
  return
}
