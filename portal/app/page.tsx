import Link from "next/link";

import DemoNotice from "@/app/components/DemoNotice";

export default function Home() {
  return (
    <main className="w-full max-w-5xl flex flex-col min-h-screen justify-center items-center mx-auto gap-10">
      <div className="text-8xl lg:text-[9rem] font-extrabold dark:bg-linear-to-r from-blue-800 to-blue-400 dark:bg-clip-text dark:text-transparent">
        OneApp
      </div>
      <p className="max-w-xl text-center text-lg opacity-80">
        Fill in one mortgage pre-application, then choose which lenders may
        download it, for how long, and revoke access at any time.
      </p>
      <div className="flex justify-center gap-8 w-full">
        <Link href="/borrower" className="btn btn-outline lg:btn-lg">
          Borrower Dashboard
        </Link>
        {/* A separate app (mock-lender), standing in for the lenders' own
            systems (FR-10). Its compose port; a plain <a>, since it's
            another origin. */}
        <a href="http://localhost:3001" className="btn btn-outline lg:btn-lg">
          Lender Dashboard
        </a>
      </div>
      <DemoNotice />
    </main>
  );
}
