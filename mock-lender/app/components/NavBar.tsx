import Link from "next/link";

// No login, so no logout: anyone who can open this app can act as any demo
// lender (see DemoNotice).
const NavBar = () => {
  return (
    <div className="navbar bg-base-100 shadow-sm">
      <div className="flex-1">
        <Link href="/" className="btn btn-ghost text-xl">
          Mock Lender
        </Link>
      </div>
    </div>
  );
};

export default NavBar;
