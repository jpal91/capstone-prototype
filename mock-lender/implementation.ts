export async function register() {
  // register() also runs for the Edge runtime, where postgres.js can't load.
  if (process.env.NEXT_RUNTIME !== "nodejs") return;

  const path = await import("node:path");
  const { migrate } = await import("drizzle-orm/postgres-js/migrator");
  const { db } = await import("@/app/lib/db");

  // Applies any SQL in drizzle/ that this database hasn't run yet (drizzle
  // records applied migrations in its own table).
  await migrate(db, {
    migrationsFolder: path.join(process.cwd(), "drizzle"),
  });
}
