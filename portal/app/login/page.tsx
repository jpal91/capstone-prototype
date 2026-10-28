"use client";
import { useActionState } from "react";

import { loginUser } from "@/app/actions/auth";

const LoginPage = () => {
  const [state, action, pending] = useActionState(loginUser, undefined);

  return (
    <form action={action}>
      <fieldset className="fieldset bg-base-200 border-base-300 rounded-box w-sm lg:w-sm border p-4">
        <legend className="fieldset-legend">Login</legend>

        <label className="label">Username</label>
        <input
          type="text"
          name="username"
          className="input  w-full"
          placeholder="Username"
          autoComplete="username"
          required
        />
        <div
          className="validator-hint"
          hidden={!Boolean(state?.errors?.username)}
        >
          {state?.errors?.username?.join("\n")}
        </div>

        <label className="label">Password</label>
        <input
          type="password"
          name="password"
          className="input  w-full"
          placeholder="Password"
          autoComplete="current-password"
          required
        />
        <div
          className="validator-hint"
          hidden={!Boolean(state?.errors?.password)}
        >
          {state?.errors?.password?.join("\n")}
        </div>

        <button disabled={pending} className="btn btn-neutral mt-4">
          Login
        </button>
        <div className="text-xs my-1" hidden={!Boolean(state?.message)}>
          {state?.message}
        </div>
      </fieldset>
    </form>
  );
};

export default LoginPage;
