import Link from "next/link";

export default function Home() {
  return (
    <main className="w-full max-w-5xl flex flex-col min-h-screen justify-center items-center mx-auto gap-10">
      <div className="text-8xl lg:text-[9rem] font-extrabold dark:bg-linear-to-r from-blue-800 to-blue-400 dark:bg-clip-text dark:text-transparent">
        OneApp
      </div>
      <div className="flex justify-center gap-8 w-full">
        <Link href="/borrower" className="btn btn-outline lg:btn-lg">
          Borrower Dashboard
        </Link>
        <Link href="/" className="btn btn-outline lg:btn-lg">
          Lender Dashboard
        </Link>
      </div>
    </main>
  );
}
