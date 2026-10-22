import { cookies } from 'next/headers'

export const requireSession = async () => {
  const cookieStore = await cookies()

  if (cookieStore.get("session")) {
    return true
  } else {
    return false
  }
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
