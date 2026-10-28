import NavBar from "@/app/components/NavBar";

const DashboardLayout = ({ children }: LayoutProps<"/borrower">) => {
  return (
    <>
      <NavBar />
      <main>{children}</main>
    </>
  );
};

export default DashboardLayout;
