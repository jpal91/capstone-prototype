"use server";
import * as z from "zod";
import { unstable_rethrow } from "next/navigation";
import { refresh } from "next/cache";

import { core } from "@/app/lib/core/client";
import { coreFieldErrors } from "./utils";

import type { components } from "@/app/lib/core/schema";

export type GrantFormState =
  | { status: "idle" }
  | { status: "created"; grant: components["schemas"]["GrantResponse"] }
  | { status: "revoked"; grant: components["schemas"]["GrantResponse"] }
  | { status: "error"; message: string; fieldErrors?: Record<string, string> };

const GrantCreateFormSchema = z.object({
  lenderId: z.coerce.number().positive(),
  versionId: z.coerce.number().positive(),
  expiresInDays: z.coerce.number().int().min(1).max(365),
});

export const grantAccess = async (
  _state: GrantFormState,
  form: FormData,
): Promise<GrantFormState> => {
  const validatedFields = GrantCreateFormSchema.safeParse({
    lenderId: form.get("lenderId"),
    versionId: form.get("versionId"),
    expiresAt: form.get("expiresAt"),
  });

  if (!validatedFields.success) {
    const errors = Object.fromEntries(
      validatedFields.error.issues.map((i) => [i.path.join("."), i.message]),
    );

    return {
      status: "error",
      message: "Grant create request contained validation errors",
      fieldErrors: errors,
    };
  }

  const { lenderId, versionId, expiresInDays } = validatedFields.data;
  const expiresAt = new Date(
    Date.now() + expiresInDays * 86_400_000,
  ).toISOString();

  let result;
  try {
    result = await core.POST("/grants", {
      body: {
        lenderId,
        versionId,
        expiresAt,
      },
    });
  } catch (e) {
    unstable_rethrow(e);
    console.error("create grant request failed: core unreachable");
    return {
      status: "error",
      message: "Error when creating, please try again",
    };
  }

  const { data, error, response } = result;

  if (response.status === 422 && error) {
    return {
      status: "error",
      message: "Grant create request contained validation errors",
      fieldErrors: coreFieldErrors(error.detail),
    };
  } else if (response.status === 404) {
    return {
      status: "error",
      message: "That version or lender is no longer available",
    };
  }

  if (error) {
    console.error("grant create failed with status ", response.status);
    return {
      status: "error",
      message: "Create grant failed. Please try again",
    };
  } else {
    refresh();

    return {
      status: "created",
      grant: data,
    };
  }
};

export const revokeGrant = async (
  _state: GrantFormState,
  form: FormData,
): Promise<GrantFormState> => {
  const idStr = form.get("id");

  if (!idStr || !/^\d+$/.test(idStr as string)) {
    return {
      status: "error",
      message: "Grant ID must be a valid integer",
    };
  }

  let result;
  try {
    result = await core.POST("/grants/{grant_id}/revoke", {
      params: {
        path: {
          grant_id: Number(idStr),
        },
      },
    });
  } catch (e) {
    unstable_rethrow(e);
    console.error("revoke grant request failed: core unreachable");
    return {
      status: "error",
      message: "Error when revoking grant, please try again",
    };
  }

  const { data, error, response } = result;

  if (response.status === 404) {
    console.error("grant id to revoke is invalid");
    return {
      status: "error",
      message: "That grant no longer exists",
    };
  }

  if (error) {
    console.error("revoke grant failed with status ", response.status);
    return {
      status: "error",
      message: "Revoke grant failed, please try again",
    };
  } else {
    refresh();

    return {
      status: "revoked",
      grant: data,
    };
  }
};
