import {
  snakeCase,
  integer,
  text,
  timestamp,
  primaryKey,
  serial,
  bytea,
  foreignKey,
  unique,
} from "drizzle-orm/pg-core";

export const coreGrantTable = snakeCase.table(
  "core_grant",
  {
    clientId: text().notNull(),
    grantId: integer().notNull(),
    listedSha256: text().notNull(),
    firstSeenAt: timestamp({ withTimezone: true }).defaultNow().notNull(),
    lastListedAt: timestamp({ withTimezone: true }).defaultNow().notNull(),
    expiresAt: timestamp({ withTimezone: true }).notNull(),
    accessEndedAt: timestamp({ withTimezone: true }),
    lastFetchStatus: text({
      enum: ["ok", "access_ended", "hash_mismatch", "error"],
    }),
    lastFetchAttemptAt: timestamp({ withTimezone: true }),
  },
  (table) => [primaryKey({ columns: [table.clientId, table.grantId] })],
);

export const receivedCopyTable = snakeCase.table(
  "received_copy",
  {
    id: serial().primaryKey(),
    clientId: text().notNull(),
    grantId: integer().notNull(),
    sha256: text().notNull(),
    xml: bytea().notNull(),
    fetchedAt: timestamp({ withTimezone: true }).defaultNow().notNull(),
  },
  (table) => [
    foreignKey({
      columns: [table.clientId, table.grantId],
      foreignColumns: [coreGrantTable.clientId, coreGrantTable.grantId],
    }),
    unique().on(table.clientId, table.grantId),
  ],
);

export type CoreGrantRowSelect = typeof coreGrantTable.$inferSelect;
export type CoreGrantRowInsert = typeof coreGrantTable.$inferInsert;
export type ReceivedCopyRowSelect = typeof receivedCopyTable.$inferSelect;
export type ReceivedCopyRowInsert = typeof receivedCopyTable.$inferInsert;
