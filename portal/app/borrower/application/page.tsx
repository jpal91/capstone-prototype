import { redirect } from "next/navigation";

import DraftForm from "@/app/components/draft/DraftForm";
import { requireSession } from "@/app/lib/session";
import { getDraft } from "@/app/lib/utils";

const ApplicationPage = async () => {
  const session = await requireSession();

  if (!session) {
    redirect("/login");
  }

  const draftRes = await getDraft();

  return (
    <div className="mx-auto mt-10 flex w-full max-w-4xl flex-col gap-8 p-8">
      <div className="flex flex-col gap-2">
        <h1 className="text-4xl font-bold">Your pre-application</h1>
        <p className="opacity-70">
          Every field is optional while you work; saving keeps a draft only you
          can see. This pre-application doesn&apos;t ask for your Social
          Security number or demographic information: you give those directly to
          the lender you choose.
        </p>
      </div>

      {draftRes === null ? (
        <div role="alert" className="alert alert-error">
          Your draft couldn&apos;t be loaded. Try again.
        </div>
      ) : (
        <DraftForm draft={draftRes.draft} />
      )}
    </div>
  );
};

export default ApplicationPage;
