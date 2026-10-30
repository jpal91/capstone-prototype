# Build context: prototype/ (the pnpm workspace root, for pnpm-lock.yaml; see
# compose.yml). Only mock-lender/ and the workspace files are copied in, so
# this image contains no MISMO schema material.

FROM node:26-trixie-slim AS build
ENV NEXT_TELEMETRY_DISABLED=1
# npm only to bootstrap pnpm; keep the version in step with packageManager in
# mock-lender/package.json.
RUN npm install -g pnpm@12.6.0
WORKDIR /app

# Dependencies first, so this layer is cached until the lockfile changes.
COPY pnpm-workspace.yaml pnpm-lock.yaml ./
COPY mock-lender/package.json mock-lender/
RUN --mount=type=cache,target=/pnpm/store \
    pnpm install --frozen-lockfile --filter mock-lender --store-dir /pnpm/store

COPY mock-lender/ mock-lender/
RUN pnpm --filter mock-lender build

FROM node:26-trixie-slim
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=3001
WORKDIR /app

# standalone/ mirrors the workspace (server.js under mock-lender/); static
# assets aren't included in it and are copied next to server.js. So are the
# migrations: instrumentation-node.ts applies ./drizzle at startup, and
# server.js changes into its own directory first. Files stay owned by root,
# so the app user can't modify them.
COPY --from=build /app/mock-lender/.next/standalone ./
COPY --from=build /app/mock-lender/.next/static mock-lender/.next/static
COPY --from=build /app/mock-lender/drizzle mock-lender/drizzle

USER node
EXPOSE 3001
CMD ["node", "mock-lender/server.js"]
