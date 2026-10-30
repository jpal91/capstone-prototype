import { getReceivedCopyXml } from "@/app/lib/data";
import { isKnownLender } from "@/app/lib/lenders";

export const GET = async (
  _req: Request,
  ctx: RouteContext<"/lenders/[clientId]/copies/[grantId]/xml">,
) => {
  const { clientId, grantId } = await ctx.params;

  if (!isKnownLender(clientId) || !/^\d+$/.test(grantId)) {
    return new Response(null, { status: 404 });
  }

  const app = await getReceivedCopyXml(clientId, Number(grantId));

  if (!app) {
    return new Response(null, { status: 404 });
  }

  const { xml, sha256 } = app;

  return new Response(new Uint8Array(xml), {
    headers: {
      "Content-Type": "application/xml",
      "X-Content-SHA256": sha256,
      "Cache-Control": "private, no-store",
    },
  });
};
