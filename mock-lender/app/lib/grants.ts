import "server-only";
import { coreFor } from "@/app/lib/core/client";
import { db } from "@/app/lib/db";
import { coreGrantTable, receivedCopyTable } from "@/app/lib/db/schema";
import { and, eq, isNull, notInArray, sql } from "drizzle-orm";
import { createHash } from "node:crypto";

export type SyncGrantsResponse =
  | { status: "success"; listed: number; added: number; ended: number }
  | { status: "error"; message: string };

export type FetchApplicationResponse =
  | { status: "success"; sha256: string }
  | { status: "ended"; message: string }
  | { status: "error"; message: string }
  | { status: "unknown_grant"; message: string };

export const syncGrants = async (
  clientId: string,
): Promise<SyncGrantsResponse> => {
  const core = coreFor(clientId);

  if (!core) return { status: "error", message: "Unknown lender" };

  let result;
  try {
    result = await core.GET("/lender/grants");
  } catch {
    console.error("sync grants failed: core unreachable");
    return {
      status: "error",
      message: "Core could not be reached",
    };
  }

  const { data, response } = result;

  if (response.status === 401) {
    console.error(`${clientId} credentials are not valid`);
    return {
      status: "error",
      message: "Lender credentials are not valid",
    };
  } else if (!response.ok) {
    console.error("sync grants failed with status ", response.status);
    return {
      status: "error",
      message: "Sync grants failed, please try again",
    };
  }

  if (!data) return { status: "success", listed: 0, added: 0, ended: 0 };

  const txRes = await db.transaction(async (tx) => {
    const lenderListedIds = new Set(
      (
        await tx
          .select({ grantId: coreGrantTable.grantId })
          .from(coreGrantTable)
          .where(eq(coreGrantTable.clientId, clientId))
      ).map((g) => g.grantId),
    );
    let addedIds = 0;

    for (const grant of data) {
      const res = await tx
        .insert(coreGrantTable)
        .values({
          grantId: grant.grantId,
          clientId: clientId,
          expiresAt: new Date(grant.expiresAt),
          listedSha256: grant.sha256,
        })
        .onConflictDoUpdate({
          target: [coreGrantTable.clientId, coreGrantTable.grantId],
          set: {
            lastListedAt: new Date(),
            expiresAt: new Date(grant.expiresAt),
          },
        })
        .returning({ hash: coreGrantTable.listedSha256 });

      if (grant.sha256 !== res[0].hash) {
        console.error(
          `hash mismatch for grantId ${grant.grantId}. expected ${res[0].hash}, received ${grant.sha256}`,
        );
      }

      if (!lenderListedIds.has(grant.grantId)) {
        addedIds++;
      }
    }

    const coreListedIds = data.map((grant) => grant.grantId);

    const endedRes = await tx
      .update(coreGrantTable)
      .set({
        accessEndedAt: new Date(),
      })
      .where(
        and(
          eq(coreGrantTable.clientId, clientId),
          notInArray(coreGrantTable.grantId, coreListedIds),
          isNull(coreGrantTable.accessEndedAt),
        ),
      )
      .returning({ _id: coreGrantTable.clientId });

    return { listed: data.length, added: addedIds, ended: endedRes.length };
  });

  return { status: "success", ...txRes };
};

export const fetchApplication = async (
  clientId: string,
  grantId: number,
): Promise<FetchApplicationResponse> => {
  const thisGrant = and(
    eq(coreGrantTable.clientId, clientId),
    eq(coreGrantTable.grantId, grantId),
  );

  const grant = await db.select().from(coreGrantTable).where(thisGrant);

  if (!grant.length) {
    return {
      status: "unknown_grant",
      message: "Unknown grant, sync first",
    };
  }

  const core = coreFor(clientId);

  if (!core) return { status: "error", message: "Unknown lender" };

  let result;
  try {
    result = await core.GET("/lender/grants/{grant_id}/application", {
      params: {
        path: {
          grant_id: grantId,
        },
      },
      parseAs: "arrayBuffer",
    });
  } catch {
    console.error("fetch application failed: core unreachable");
    await db
      .update(coreGrantTable)
      .set({
        lastFetchStatus: "error",
        lastFetchAttemptAt: new Date(),
      })
      .where(thisGrant);

    return {
      status: "error",
      message: "Core could not be reached",
    };
  }

  const { data, response } = result;

  if (response.status === 404) {
    console.info("access to application has ended");

    await db
      .update(coreGrantTable)
      .set({
        accessEndedAt: sql`coalesce(${coreGrantTable.accessEndedAt}, now())`,
        lastFetchStatus: "access_ended",
        lastFetchAttemptAt: new Date(),
      })
      .where(thisGrant);

    return {
      status: "ended",
      message: "Access has ended for this application",
    };
  } else if (!response.ok) {
    console.error(
      "could not access application with response status ",
      response.status,
    );

    await db
      .update(coreGrantTable)
      .set({
        lastFetchStatus: "error",
        lastFetchAttemptAt: new Date(),
      })
      .where(thisGrant);

    return {
      status: "error",
      message: "Could not access application, please try again",
    };
  }

  const xml = Buffer.from(data ?? new ArrayBuffer());
  const hash = createHash("sha256").update(xml).digest("hex");
  const headerHash = response.headers.get("X-Content-SHA256") ?? "";
  const { listedSha256 } = grant[0];

  if (hash !== headerHash || hash !== listedSha256) {
    console.error(
      "hash mismatch between received xml and header hash or listed hash",
    );

    await db
      .update(coreGrantTable)
      .set({
        lastFetchStatus: "hash_mismatch",
        lastFetchAttemptAt: new Date(),
      })
      .where(thisGrant);

    return {
      status: "error",
      message:
        "Hash of received data did not match known hash for this application",
    };
  }

  await db.transaction(async (tx) => {
    await tx
      .update(coreGrantTable)
      .set({
        lastFetchStatus: "ok",
        lastFetchAttemptAt: new Date(),
      })
      .where(thisGrant);

    await tx
      .insert(receivedCopyTable)
      .values({
        clientId,
        grantId,
        sha256: hash,
        xml,
      })
      .onConflictDoNothing();
  });

  return { status: "success", sha256: hash };
};
