import { getReceivedCopies } from "@/app/lib/data";
import { isKnownLender } from "@/app/lib/lenders";

export const GET = async (
  _req: Request,
  ctx: RouteContext<"/api/lenders/[clientId]/copies">,
) => {
  const { clientId } = await ctx.params;

  if (!isKnownLender(clientId)) {
    return Response.json(
      { status: "error", message: "Lender not found" },
      { status: 404 },
    );
  }

  const res = await getReceivedCopies(clientId);

  return Response.json(res);
};
