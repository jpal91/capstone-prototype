import { syncGrants } from "@/app/lib/grants";
import { isKnownLender } from "@/app/lib/lenders";

export const POST = async (
  _req: Request,
  ctx: RouteContext<"/api/lenders/[clientId]/sync">,
) => {
  const { clientId } = await ctx.params;

  if (!isKnownLender(clientId)) {
    return Response.json(
      { status: "error", message: "Lender not found" },
      { status: 404 },
    );
  }

  const res = await syncGrants(clientId);

  return Response.json(res, { status: res.status === "success" ? 200 : 502 });
};
