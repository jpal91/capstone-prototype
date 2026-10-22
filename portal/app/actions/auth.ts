"use server"
import 'server-only'
import * as z from 'zod'
import { redirect } from "next/navigation"

import { createSession } from "@/app/lib/session"

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
    const res = await fetch("http://127.0.0.1:8000/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username,
        password
      })
    })

    if (!res.ok) {
      const msg = await res.json()
      console.error(msg)

      return {
        message: "Invalid username or password"
      }
    }

    const { token } = await res.json()
    await createSession(token)
  } catch {
    return {
      message: "Could not login, try again"
    }
  }


  redirect("/dashboard")
}
