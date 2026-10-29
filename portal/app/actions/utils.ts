import type { components } from "@/app/lib/core/schema";

// Same keys as the form's input names. FastAPI puts request-body errors under
// "body": ["body", "assets", 0, "amount"] -> "assets.0.amount".
export const coreFieldErrors = (
  detail: components["schemas"]["ValidationError"][] = [],
) =>
  Object.fromEntries(
    detail.map((d) => [
      (d.loc[0] === "body" ? d.loc.slice(1) : d.loc).join("."),
      d.msg.replace(/^Value error, /, ""),
    ]),
  );
