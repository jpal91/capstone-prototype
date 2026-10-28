import { core } from "@/app/lib/core/client";

export const GET = async (
  _req: Request,
  ctx: RouteContext<"/borrower/versions/[id]/xml">,
) => {
  const { id } = await ctx.params;

  // Only plain digits; anything else can't be one of the borrower's versions.
  if (!/^\d+$/.test(id)) {
    return new Response(null, { status: 404 });
  }

  // "stream" passes core's bytes through untouched (the hash is over them);
  // the default would JSON.parse the XML.
  const { data, response } = await core.GET("/versions/{version_id}/xml", {
    params: { path: { version_id: Number(id) } },
    parseAs: "stream",
  });

  if (!response.ok || !data) {
    if (response.status !== 404) {
      console.error("fetch version xml failed with status ", response.status);
    }
    return new Response(null, { status: response.status === 404 ? 404 : 502 });
  }

  return new Response(data, {
    headers: {
      "Content-Type": "application/xml",
      "X-Content-SHA256": response.headers.get("X-Content-SHA256") ?? "",
      "Cache-Control": "private, no-store",
    },
  });
};
