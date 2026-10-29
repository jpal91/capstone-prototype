# Build context: prototype/ (the pnpm workspace root, for pnpm-lock.yaml; see
# compose.yml). Only portal/ and the workspace files are copied in, so this
# image contains no MISMO schema material.

FROM node:26-trixie-slim AS build
ENV NEXT_TELEMETRY_DISABLED=1
# npm only to bootstrap pnpm; keep the version in step with packageManager in
# portal/package.json.
RUN npm install -g pnpm@12.6.0
WORKDIR /app

# Dependencies first, so this layer is cached until the lockfile changes.
COPY pnpm-workspace.yaml pnpm-lock.yaml ./
COPY portal/package.json portal/
RUN --mount=type=cache,target=/pnpm/store \
    pnpm install --frozen-lockfile --filter portal --store-dir /pnpm/store

COPY portal/ portal/
RUN pnpm --filter portal build

FROM node:26-trixie-slim
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=3000
WORKDIR /app

# standalone/ mirrors the workspace (server.js under portal/); static assets
# and public/ aren't included in it and are copied next to server.js. Files
# stay owned by root, so the app user can't modify them.
COPY --from=build /app/portal/.next/standalone ./
COPY --from=build /app/portal/.next/static portal/.next/static
COPY --from=build /app/portal/public portal/public

USER node
EXPOSE 3000
CMD ["node", "portal/server.js"]
