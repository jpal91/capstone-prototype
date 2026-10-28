import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Login",
};

export default function Layout({ children }: LayoutProps<"/login">) {
  return (
    <main className="w-screen h-screen flex justify-center items-center">
      {children}
    </main>
  );
}
