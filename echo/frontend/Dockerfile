FROM node:22-alpine AS builder

RUN npm install -g --force pnpm

WORKDIR /code

COPY package.json pnpm-lock.yaml ./

RUN echo "fetch-timeout=60000" >> .npmrc
# https://github.com/pnpm/pnpm/issues/5803#issuecomment-1974820613
RUN pnpm config set store-dir /home/node/.local/share/pnpm/store
RUN pnpm install --frozen-lockfile

COPY . .

ARG VITE_BUILD_VERSION
ARG VITE_API_BASE_URL
ARG VITE_ADMIN_BASE_URL
ARG VITE_PARTICIPANT_BASE_URL
ARG VITE_USE_PARTICIPANT_ROUTER=0
ARG VITE_DIRECTUS_PUBLIC_URL

ENV VITE_BUILD_VERSION=$VITE_BUILD_VERSION
ENV VITE_API_URL=$VITE_API_BASE_URL
ENV VITE_ADMIN_BASE_URL=$VITE_ADMIN_BASE_URL
ENV VITE_PARTICIPANT_BASE_URL=$VITE_PARTICIPANT_BASE_URL
ENV VITE_DIRECTUS_PUBLIC_URL=$VITE_DIRECTUS_PUBLIC_URL
ENV VITE_USE_PARTICIPANT_ROUTER=$VITE_USE_PARTICIPANT_ROUTER

RUN pnpm run build

FROM node:22-alpine

WORKDIR /app

RUN npm install -g --force serve

COPY --from=builder /code/dist /app

CMD ["serve", "-p", "5173", "--single"]