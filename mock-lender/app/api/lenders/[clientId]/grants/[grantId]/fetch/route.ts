import { fetchApplication } from "@/app/lib/grants";
import { isKnownLender } from "@/app/lib/lenders";

export const POST = async (
  _req: Request,
  ctx: RouteContext<"/api/lenders/[clientId]/grants/[grantId]/fetch">,
) => {
  const { clientId, grantId } = await ctx.params;

  if (!isKnownLender(clientId) || !/^\d+$/.test(grantId)) {
    return Response.json(
      { status: "error", message: "Not found" },
      { status: 404 },
    );
  }

  const res = await fetchApplication(clientId, Number(grantId));

  if (res.status !== "success") {
    const status =
      res.status === "ended" ? 409 : res.status === "unknown_grant" ? 404 : 502;
    return Response.json(res, { status });
  }

  return Response.json(res);
};
