// instrumentation-node.ts (next to it, in the project root)
import { migrate } from "drizzle-orm/postgres-js/migrator";

import { db } from "@/app/lib/db";

// Applies any SQL in drizzle/ that this database hasn't run yet (drizzle
// records applied migrations in its own table). Relative to the working
// directory: mock-lender/ under `pnpm dev`, and next to server.js in the image.
await migrate(db, { migrationsFolder: "./drizzle" });
