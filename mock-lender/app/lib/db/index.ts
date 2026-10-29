import "server-only";
import postgres from "postgres";
import { drizzle } from "drizzle-orm/postgres-js";

const BASE_URL =
  process.env.DATABASE_URL ?? "postgres://lender:lender@127.0.0.1:5432/lender";
const globalForDb = globalThis as unknown as {
  client: postgres.Sql | undefined;
};

const client = globalForDb.client ?? postgres(BASE_URL);

if (process.env.NODE_ENV !== "production") globalForDb.client = client;

export const db = drizzle({ client });
