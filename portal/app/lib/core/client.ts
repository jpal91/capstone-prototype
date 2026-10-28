import "server-only";
import createClient, { type Middleware } from "openapi-fetch";
import { redirect } from "next/navigation";

import { getToken } from "@/app/lib/session";
import type { paths } from "./schema";

// Set in compose. Read when the server starts, not at build time.
const baseUrl = process.env.CORE_URL ?? "http://127.0.0.1:8000";

// Without the session middleware: login, and logout, which must clear the
// cookie even when core has already expired the token.
export const publicCore = createClient<paths>({ baseUrl });

// redirect() throws, so a call through `core` that hits either redirect ends
// there. Don't wrap these calls in a bare try/catch: call unstable_rethrow(e)
// first in the catch.
const auth: Middleware = {
  async onRequest({ request }) {
    const token = await getToken();
    if (!token) redirect("/login");
    request.headers.set("Authorization", `Bearer ${token}`);
    return request;
  },
  onResponse({ response }) {
    // core no longer accepts the token (expired, or logged out elsewhere).
    if (response.status === 401) redirect("/login");
  },
};

// Every borrower route.
export const core = createClient<paths>({ baseUrl });
core.use(auth);
