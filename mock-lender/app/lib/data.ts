import "server-only";

import { db } from "@/app/lib/db";
import { coreGrantTable, receivedCopyTable } from "@/app/lib/db/schema";
import { and, desc, eq, getColumns, sql } from "drizzle-orm";

export const getCoreGrants = async (clientId: string) => {
  const grants = await db
    .select()
    .from(coreGrantTable)
    .where(eq(coreGrantTable.clientId, clientId))
    .orderBy(
      sql`${coreGrantTable.accessEndedAt} is null desc`,
      desc(coreGrantTable.grantId),
    );

  return grants;
};

export const getReceivedCopies = async (clientId: string) => {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { xml, ...rest } = getColumns(receivedCopyTable);

  const copies = await db
    .select({ ...rest })
    .from(receivedCopyTable)
    .where(eq(receivedCopyTable.clientId, clientId))
    .orderBy(desc(receivedCopyTable.fetchedAt));

  return copies;
};

export const getReceivedCopyXml = async (clientId: string, grantId: number) => {
  const copy = await db
    .select({ xml: receivedCopyTable.xml, sha256: receivedCopyTable.sha256 })
    .from(receivedCopyTable)
    .where(
      and(
        eq(receivedCopyTable.clientId, clientId),
        eq(receivedCopyTable.grantId, grantId),
      ),
    )
    .limit(1);

  return copy.length > 0 ? copy[0] : null;
};
