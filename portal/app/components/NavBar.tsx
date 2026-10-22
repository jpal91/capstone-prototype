"use client"
import { logout } from "@/app/lib/session"
import { redirect } from "next/navigation"

const NavBar = () => {
  return (
    <div className="navbar bg-base-100 shadow-sm">
      <div className="flex-1">
        <a className="btn btn-ghost text-xl">OneApp</a>
      </div>
      <div className="flex-none">
        <button className="btn"
          onClick={() => {
            logout()
            redirect("/")
          }}
        >
          Logout
        </button>
      </div>
    </div>
  )
}

export default NavBar
