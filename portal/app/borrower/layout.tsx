import NavBar from "@/app/components/NavBar"

const DashboardLayout = ({ children }: LayoutProps<'/dashboard'>) => {
  return (
    <>
      <NavBar />
      <main>{children}</main>
    </>
  )
}

export default DashboardLayout
