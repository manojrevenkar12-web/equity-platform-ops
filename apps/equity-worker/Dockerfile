# The API and the worker share one image; the Deployment picks the command (deploy/k8s/base).
FROM node:22-slim AS build
WORKDIR /app
RUN corepack enable
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY tsconfig.json ./
COPY src/ src/
RUN pnpm build && pnpm prune --prod

FROM node:22-slim
ENV NODE_ENV=production
WORKDIR /app
COPY --from=build /app/node_modules node_modules
COPY --from=build /app/dist dist
COPY package.json ./
USER node
EXPOSE 3000
CMD ["node", "dist/server.js"]
