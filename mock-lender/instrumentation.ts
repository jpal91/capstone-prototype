export async function register() {
  // register() also runs for the Edge runtime, where postgres.js can't load.
  if (process.env.NEXT_RUNTIME == "nodejs") {
    await import("./instrumentation-node");
  }
}
