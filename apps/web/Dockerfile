FROM node:22-alpine AS build

WORKDIR /app

RUN npm install --global pnpm@9.15.9

COPY pnpm-workspace.yaml pnpm-lock.yaml ./
COPY apps/web/package.json apps/web/package.json
COPY packages/api-types/package.json packages/api-types/package.json

RUN pnpm install --frozen-lockfile

COPY apps/web apps/web
COPY packages/api-types packages/api-types

RUN pnpm --filter @stock-research/web build

FROM nginx:alpine

COPY --from=build /app/apps/web/dist /usr/share/nginx/html
COPY infrastructure/nginx/web.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
