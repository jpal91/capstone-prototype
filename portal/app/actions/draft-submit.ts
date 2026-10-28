"use server"
import * as z from 'zod'
import { unstable_rethrow } from "next/navigation"

import { core } from "@/app/lib/core/client"
import { MAX_ROWS } from "@/app/lib/draft"
import { ownStatusValues, occupancyValues, assetTypeValues, loanProgramValues, loanPurposeValues, liabilityTypeValues, components } from "@/app/lib/core/schema"


// "assets.0.amount" -> { assets: [{ amount }] }. Keys come from an untrusted
// POST, so skip anything that could reach Object.prototype.
const UNSAFE = new Set(["__proto__", "prototype", "constructor"])

const unflatten = (form: FormData) => {
  const root: Record<string, any> = {}

  for (const [key, value] of form) {
    if (typeof value !== "string" || key.startsWith("$")) continue

    const parts = key.split(".")
    if (parts.some((p) => UNSAFE.has(p))) continue

    let node: any = root
    parts.forEach((part, i) => {
      if (i === parts.length - 1) {
        node[part] = value === "" ? null : value
      } else {
        node = node[part] ??= ( /^\d+$/.test(parts[i + 1]) ? [] : {} )
      }
    })
  }

  return root
}

const filterArrayItems = (arr: Array<any>) => {
  return arr.map(item => (
    item && typeof item === "object" && Object.values(item).some(Boolean) ? item : null
  )).filter(Boolean)
}

const zipCodeCheck = z.stringFormat("zipCode", /^\d{5}(-\d{4})?$/, { error: "Enter a 5- or 9-digit zip code" }).nullish()
const decimalCheck = z.stringFormat("decimal", /^\d+(\.\d{1,2})?$/, { error: "Enter a currency-like number. Ex. 12.23" }).nullish()

const AssetFormSchema = z.object({
  "institutionName": z.string().nullish(),
  "assetType": z.enum(assetTypeValues).nullish(),
  "amount": decimalCheck
})
const LiabilityFormSchema = z.object({
  "institutionName": z.string().nullish(),
  "liabilityType": z.enum(liabilityTypeValues).nullish(),
  "monthsRemaining": z.coerce.number().nullish(),
  "monthlyAmount": decimalCheck,
  "balance": decimalCheck
})

const DraftSaveFormSchema = z.object({
  borrower: z.object({
    firstName: z.string().nullish(),
    lastName: z.string().nullish(),
    dateOfBirth: z.iso.date().nullish(),
    phoneNumber: z.string().nullish(),
    email: z.email().nullish()
  }).optional(),
  address: z.object({
    streetAddress: z.string().nullish(),
    city: z.string().nullish(),
    state: z.string().trim().toUpperCase().regex(/^[A-Z]{2}$/).nullish(),
    zipCode: zipCodeCheck,
    ownStatus: z.enum(ownStatusValues).nullish(),
    monthsAtAddress: z.coerce.number().int().nonnegative().nullish()
  }).optional(),
  subjectProperty: z.object({
    streetAddress: z.string().nullish(),
    city: z.string().nullish(),
    state: z.string().trim().toUpperCase().regex(/^[A-Z]{2}$/).nullish(),
    zipCode: zipCodeCheck,
    monthlyTaxes: decimalCheck,
    monthlyHoi: decimalCheck,
    propertyValue: decimalCheck,
    occupancy: z.enum(occupancyValues).nullish()
  }).optional(),
  income: z.object({
    employerName: z.string().nullish(),
    monthlyIncome: decimalCheck,
    startDate: z.iso.date().nullish(),
    position: z.string().nullish()
  }).optional(),
  assets: z.preprocess(a => Array.isArray(a) ? filterArrayItems(a) : a, z.array(AssetFormSchema).max(MAX_ROWS).optional()),
  liabilities: z.preprocess(l => Array.isArray(l) ? filterArrayItems(l) : l, z.array(LiabilityFormSchema).max(MAX_ROWS).optional()),
  loan: z.object({
    loanTermMonths: z.coerce.number().int().nonnegative().nullish(),
    loanProgram: z.enum(loanProgramValues).nullish(),
    loanAmount: decimalCheck,
    loanPurpose: z.enum(loanPurposeValues).nullish()
  }).optional()
}) satisfies z.ZodType<components["schemas"]["UrlaDraft-Input"]>

// Same keys as the form's input names. FastAPI puts request-body errors under
// "body": ["body", "assets", 0, "amount"] -> "assets.0.amount".
const coreFieldErrors = (detail: components["schemas"]["ValidationError"][] = []) =>
  Object.fromEntries(detail.map((d) => [
    (d.loc[0] === "body" ? d.loc.slice(1) : d.loc).join("."),
    d.msg
  ]))

export type SubmitDraftState =
  | { status: "idle" }
  | { status: "saved", savedAt: string }
  | { status: "error", message: string, fieldErrors?: Record<string, string> };

export const submitDraft = async (_state: SubmitDraftState, form: FormData): Promise<SubmitDraftState> => {
  const objData = unflatten(form)
  const validatedFields = DraftSaveFormSchema.safeParse(objData)

  if (!validatedFields.success) {
    const errors = Object.fromEntries(validatedFields.error.issues.map(i => [i.path.join("."), i.message]))
    return {
      status: "error",
      message: "Application contained validation errors",
      fieldErrors: errors
    }
  }

  const { data: draft } = validatedFields

  let result
  try {
    result = await core.PUT("/draft", {
      body: draft
    })
  } catch (e) {
    // The auth middleware's redirect() throws too; let it through.
    unstable_rethrow(e)
    console.error("save draft failed: core unreachable")
    return {
      status: "error",
      message: "Error when saving draft, please try again"
    }
  }

  const { error, response } = result

  // core's own validation caught something zod let through.
  if (response.status === 422 && error) {
    return {
      status: "error",
      message: "Application contained validation errors",
      fieldErrors: coreFieldErrors(error.detail)
    }
  }

  if (error) {
    console.error("save draft failed with status ", response.status)
    return {
      status: "error",
      message: "Error when saving draft, please try again"
    }
  } else {
    return { status: "saved", savedAt: (new Date()).toISOString() }
  }
}
