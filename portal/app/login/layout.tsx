import type { Metadata } from "next";

import DemoNotice from "@/app/components/DemoNotice";

export const metadata: Metadata = {
  title: "Login",
};

export default function Layout({ children }: LayoutProps<"/login">) {
  return (
    <main className="w-screen h-screen flex flex-col justify-center items-center gap-6">
      {children}
      <DemoNotice showAccounts />
    </main>
  );
}
