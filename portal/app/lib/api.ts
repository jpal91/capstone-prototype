
const BASE_URL = process.env.API_BASE_URL || "http://127.0.0.1:8000"

type ApiFetchResponse<T> = { ok: false, error?: Record<string, any>, status: number } | { ok: true, msg: T, status: number }

export const apiFetch = async <T = any>(
  path: string,
  init: RequestInit
): Promise<ApiFetchResponse<T>> => {
  let url: URL

  if (path.startsWith("http")) {
    url = new URL(path)
  } else if (!path.startsWith("/")) {
    url = new URL("/" + path, BASE_URL)
  } else {
    url = new URL(path, BASE_URL)
  }

  try {
    const res = await fetch(url, init)
    const body = await res.json()

    if (!res.ok) {
      console.error("failed with status ", res.status, " Error:\n", body)

      return {
        ok: false,
        error: body,
        status: res.status
      }
    }

    return {
      ok: true,
      msg: body,
      status: res.status
    }
  } catch (e) {
    console.error("Fetch failed with error -", e)
    return {
      ok: false,
      status: 0
    }
  }
}
