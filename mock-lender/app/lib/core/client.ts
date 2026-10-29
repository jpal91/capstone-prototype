import "server-only";
import createClient from "openapi-fetch";
import { getLender } from "@/app/lib/lenders";

import type { paths } from "./schema";

// Set in compose. Read when the server starts, not at build time.
const baseUrl = process.env.CORE_URL ?? "http://127.0.0.1:8000";

export const coreFor = (clientId: string) => {
  const lender = getLender(clientId);

  if (!lender) return null;

  const auth = Buffer.from(`${lender.clientId}:${lender.secret}`).toString(
    "base64",
  );

  return createClient<paths>({
    baseUrl,
    headers: {
      Authorization: `Basic ${auth}`,
    },
  });
};
