import Link from "next/link";

import { logoutUser } from "@/app/actions/auth";

const NavBar = () => {
  return (
    <div className="navbar bg-base-100 shadow-sm">
      <div className="flex-1">
        <Link href="/borrower" className="btn btn-ghost text-xl">
          OneApp
        </Link>
      </div>
      <form className="flex-none" action={logoutUser}>
        <button className="btn">Logout</button>
      </form>
    </div>
  );
};

export default NavBar;
