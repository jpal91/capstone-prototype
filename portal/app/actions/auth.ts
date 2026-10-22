"use server"
import * as z from 'zod'
import { redirect } from "next/navigation"

import { createSession, logout } from "@/app/lib/session"
import { apiFetch } from "@/app/lib/api"

const LoginFormSchema = z.object({
  username: z.string(),
  password: z.string()
})

export type FormState =
  | {
      errors?: {
        username?: string[]
        password?: string[]
      }
      message?: string
    }
  | undefined


export const loginUser = async (_state: FormState, form: FormData) => {
  const validatedFields = LoginFormSchema.safeParse({
    username: form.get("username"),
    password: form.get("password")
  })

  if (!validatedFields.success) {
    return {
      errors: z.flattenError(validatedFields.error).fieldErrors
    }
  }

  const { username, password } = validatedFields.data


  try {
    const res = await apiFetch<{ token: string }>("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username,
        password
      })
    })

    if (!res.ok) {
      return {
        message: res.status === 401 ? "Invalid username or password" : "Could not log in, try again"
      }
    }

    const { token } = res.msg
    await createSession(token)
  } catch {
    return {
      message: "Could not login, try again"
    }
  }


  redirect("/dashboard")
}

export const logoutUser = async () => {
  await logout()
  redirect("/")
}
