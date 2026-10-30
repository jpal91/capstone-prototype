import type { Metadata } from "next";
import Link from "next/link";

import { listLenders } from "@/app/lib/lenders";
import DemoNotice from "@/app/components/DemoNotice";

export const metadata: Metadata = { title: "Lenders" };

const LendersPage = () => {
  const lenders = listLenders();

  return (
    <div className="mx-auto w-full max-w-7xl flex flex-col items-center p-8 mt-10 gap-12">
      <h1 className="text-5xl font-bold self-start">Lenders</h1>
      <div className="grid w-full gap-4 md:grid-cols-2">
        {lenders.map((l) => (
          <Link
            key={l.clientId}
            href={`/lenders/${l.clientId}`}
            className="card card-border bg-base-100 hover:bg-base-200"
          >
            <div className="card-body">
              <h2 className="card-title">{l.name}</h2>
              <p className="text-sm opacity-70">
                Client ID <span className="font-mono">{l.clientId}</span>
              </p>
            </div>
          </Link>
        ))}
      </div>
      <DemoNotice />
    </div>
  );
};

export default LendersPage;
