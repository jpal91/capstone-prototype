import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { listLenders } from "@/app/lib/lenders";
import { getCoreGrants, getReceivedCopies } from "@/app/lib/data";
import CopyCard from "@/app/components/CopyCard";
import GrantsTable from "@/app/components/GrantsTable";

const findLender = (clientId: string) =>
  listLenders().find((l) => l.clientId === clientId);

export const generateMetadata = async ({
  params,
}: PageProps<"/lenders/[clientId]">): Promise<Metadata> => {
  const { clientId } = await params;

  return { title: findLender(clientId)?.name ?? "Unknown lender" };
};

const LenderPage = async ({ params }: PageProps<"/lenders/[clientId]">) => {
  const { clientId } = await params;
  const lender = findLender(clientId);

  if (!lender) notFound();

  const [grants, copies] = await Promise.all([
    getCoreGrants(clientId),
    getReceivedCopies(clientId),
  ]);

  const endedGrantIds = new Set(
    grants.filter((g) => g.accessEndedAt).map((g) => g.grantId),
  );

  return (
    <div className="mx-auto w-full max-w-7xl flex flex-col p-8 mt-10 gap-20">
      <section className="w-full flex flex-col">
        <h1 className="text-5xl font-bold mb-2">{lender.name}</h1>
        <p className="opacity-70 mb-12">
          Client ID <span className="font-mono">{lender.clientId}</span>
        </p>
        <h2 className="text-3xl font-bold mb-6">Shared applications</h2>
        <GrantsTable grants={grants} />
      </section>

      <section className="w-full flex flex-col">
        <h2 className="text-3xl font-bold mb-2">Received copies</h2>
        <p className="opacity-70 mb-6">
          Stored in this lender&apos;s own database. Ending access stops new
          fetches; it doesn&apos;t remove these.
        </p>
        {copies.length === 0 ? (
          <p className="opacity-70">No applications fetched yet.</p>
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            {copies.map((c) => (
              <CopyCard
                key={c.id}
                copy={c}
                accessEnded={endedGrantIds.has(c.grantId)}
              />
            ))}
          </div>
        )}
      </section>
    </div>
  );
};

export default LenderPage;
