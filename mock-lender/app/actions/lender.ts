"use server";
import * as z from "zod";
import { refresh } from "next/cache";

import {
  syncGrants,
  type SyncGrantsResponse,
  type FetchApplicationResponse,
  fetchApplication,
} from "@/app/lib/grants";

export type SyncGrantFormState = SyncGrantsResponse | { status: "idle" };
export type FetchApplicationFormState =
  FetchApplicationResponse | { status: "idle" };

const SyncSchema = z.object({ clientId: z.string().min(1) });
const FetchApplicationSchema = z.object({
  clientId: z.string().min(1),
  grantId: z.coerce.number().int().positive(),
});

export const syncGrantsAction = async (
  _state: SyncGrantFormState,
  form: FormData,
): Promise<SyncGrantFormState> => {
  const parsed = SyncSchema.safeParse({ clientId: form.get("clientId") });

  if (!parsed.success) return { status: "error", message: "Missing lender" };

  const res = await syncGrants(parsed.data.clientId);

  if (res.status === "success") refresh();

  return res;
};

export const fetchApplicationAction = async (
  _state: FetchApplicationFormState,
  form: FormData,
): Promise<FetchApplicationFormState> => {
  const parsed = FetchApplicationSchema.safeParse({
    clientId: form.get("clientId"),
    grantId: form.get("grantId"),
  });

  if (!parsed.success)
    return { status: "error", message: "Missing Grant Id or lender" };

  const { clientId, grantId } = parsed.data;

  const res = await fetchApplication(clientId, grantId);

  refresh();

  return res;
};
