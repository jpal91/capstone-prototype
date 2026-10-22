"use server"
import * as z from 'zod'
import { redirect } from "next/navigation"

import { createSession, deleteSession, getToken } from "@/app/lib/session"
import { publicCore } from "@/app/lib/core/client"

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
    const { data, error, response } = await publicCore.POST("/auth/login", {
      body: { username, password }
    })

    if (error) {
      console.error("login failed with status", response.status)

      return {
        message: response.status === 401 ? "Invalid username or password" : "Could not log in, try again"
      }
    }

    await createSession(data.token)
  } catch (e) {
    console.error("login request failed:", e)

    return {
      message: "Could not log in, try again"
    }
  }


  redirect("/borrower")
}

export const logoutUser = async () => {
  const token = await getToken()

  if (token) {
    // A 401 means core has already ended the session; the cookie goes either way.
    try {
      await publicCore.POST("/auth/logout", {
        headers: { Authorization: `Bearer ${token}` }
      })
    } catch (e) {
      console.error("logout request failed:", e)
    }
  }

  await deleteSession()
  redirect("/login")
}
